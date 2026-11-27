"""§459 one versioned candidate path; modes never confer release authority."""
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
import re

from .engine import BaselinePreviewRequest375, BaselineEnginePreview375, evaluate_baseline_preview
from .replay import require_utc

ENGINE_CONTRACT = "mst.shared-candidate.v1"


class EngineMode(str, Enum):
    RESEARCH = "RESEARCH"
    VALIDATION = "VALIDATION"
    PRODUCTION = "PRODUCTION"


def _typed(value):
    """Private canonical typed encoding, not an attestation or public receipt."""
    if type(value) in (str, int, bool, type(None)):
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("MST_459_NONFINITE_PROFILE")
        return ["decimal", str(value)]
    if type(value) is datetime:
        require_utc(value)
        return ["utc", value.isoformat()]
    if isinstance(value, Enum):
        return ["enum", type(value).__module__, type(value).__qualname__, _typed(value.value)]
    if type(value) is tuple:
        return ["tuple", [_typed(v) for v in value]]
    if is_dataclass(value) and not isinstance(value, type):
        cls = type(value)
        if not cls.__dataclass_params__.frozen or not cls.__module__.startswith("swing_trading."):
            raise ValueError("MST_459_FROZEN_PLAN_REQUIRED")
        return ["record", cls.__module__, cls.__qualname__,
                [[f.name, _typed(getattr(value, f.name))] for f in fields(value)]]
    raise ValueError("MST_459_UNSUPPORTED_PROFILE_VALUE")


def configuration_digest(requests):
    if type(requests) is not tuple or len(requests) > 32:
        raise ValueError("MST_459_EXPLICIT_REQUESTS")
    if any(type(r) is not BaselinePreviewRequest375 for r in requests):
        raise ValueError("MST_459_EXACT_REQUEST")
    payload = json.dumps([ENGINE_CONTRACT, _typed(requests)], ensure_ascii=True,
                         separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CandidateProfile459:
    profile_id: str
    version: str
    code_git_sha: str
    configuration_sha256: str
    requests: tuple[BaselinePreviewRequest375, ...]

    def __post_init__(self):
        for value in (self.profile_id, self.version):
            if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value):
                raise ValueError("MST_459_EXPLICIT_PROFILE_ID")
        if type(self.code_git_sha) is not str or not re.fullmatch(r"[a-f0-9]{40}", self.code_git_sha):
            raise ValueError("MST_459_EXPLICIT_CODE_REFERENCE")
        if self.configuration_sha256 != configuration_digest(self.requests):
            raise ValueError("MST_459_PROFILE_DIGEST_MISMATCH")


@dataclass(frozen=True)
class ModeEvaluation459:
    mode: EngineMode
    private_profile: CandidateProfile459
    private_preview: BaselineEnginePreview375

    def safe_summary(self):
        summary = self.private_preview.safe_phase_summary()
        summary.update(schema="mst.private.unified_mode.v1", mode=self.mode.value,
                       engine_contract=ENGINE_CONTRACT, validation_qualified=False,
                       production_qualified=False, publication_allowed=False,
                       code_identity_attested=False)
        return summary


def evaluate_candidate(inputs, *, mode, profile):
    """Research and Validation call exactly the same detector; Production denied.

    A caller-supplied code SHA identifies a claim, not the running build.
    Validation is candidate replay capability, not OOS or release certification.
    """
    if type(mode) is not EngineMode or type(profile) is not CandidateProfile459:
        raise ValueError("MST_459_EXPLICIT_MODE_PROFILE")
    if mode is EngineMode.PRODUCTION:
        raise ValueError("MST_459_PRODUCTION_NOT_QUALIFIED")
    if profile.configuration_sha256 != configuration_digest(profile.requests):
        raise ValueError("MST_459_PROFILE_DIGEST_MISMATCH")
    preview = evaluate_baseline_preview(inputs, requests=profile.requests)
    return ModeEvaluation459(mode, profile, preview)
