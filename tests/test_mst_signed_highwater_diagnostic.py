"""MST §245 ephemeral Ed25519 signatures; no owner key, private repo or I/O."""
from __future__ import annotations

from copy import deepcopy
from base64 import b64encode
from hashlib import sha256
from pathlib import Path
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from scripts import mst_signed_highwater_diagnostic as h

KEY_ID = "MST_FAKE_OWNER_KEY_EPOCH1"
SERIES = "FPT_D1_SSI_FAKE"
PRIVATE = Ed25519PrivateKey.generate()
PUBLIC = PRIVATE.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def pin(n=1, *, source_sha=None, **kw):
    p = {
        "provider": "SSI", "symbol": "FPT", "native_tf": "D1",
        "file_id": f"FakeOwnerSourceChunk{n:04d}",
        "run_id": str(4460000000+n),
        "source_sha256": source_sha or sha256(f"FICTIONAL OHLCV {n}".encode()).hexdigest(),
    }
    p.update(kw)
    return p


def sign(body, *, key=PRIVATE, key_id=KEY_ID):
    sig = key.sign(h._canonical(body, max_bytes=2048))
    return {
        "schema": h.CHECKPOINT_SCHEMA,
        "key_id": key_id,
        "body": body,
        "signature_b64": b64encode(sig).decode(),
    }


def genesis(**kw):
    body = {
        "schema": h.BODY_SCHEMA, "repository": "ngluonghoa/MST",
        "series_id": SERIES, "sequence": 1,
        "previous_checkpoint_sha256": None, "previous_head_pin": None,
        "head_pin": pin(1), "source_finality_attested": False,
        "publisher_cas_executed": False,
        "source_licensed_for_storage_attested": False,
        "signals_eligible": False,
    }
    body.update(kw)
    return sign(body)


def successor(prev, n, **changes):
    body = {
        **prev["body"],
        "sequence": n,
        "previous_checkpoint_sha256": h.checkpoint_digest(prev),
        "previous_head_pin": deepcopy(prev["body"]["head_pin"]),
        "head_pin": pin(n),
    }
    body.update(changes)
    return sign(body)


def check(ckpts, *, pub=PUBLIC, tip=None, key_id=KEY_ID):
    return h.verify_signed_highwater_candidates(
        ckpts, trusted_key_id=key_id,
        trusted_ed25519_public_key=pub,
        expected_tip_checkpoint_sha256=(tip if tip is not None else
                                        h.checkpoint_digest(ckpts[-1]) if
                                        type(ckpts) is list and ckpts else "0"*64),
    )


class SignedHighwaterReadonly245(unittest.TestCase):
    def test_one_signed_candidate_is_not_trusted_owner_or_cas(self):
        a = genesis()
        result = check([a])
        self.assertEqual(result["checkpoint_count"], 1)
        self.assertEqual(result["linked_edges"], 0)
        self.assertEqual(result["source_provider"], "SSI")
        self.assertEqual(result["native_tf"], "D1")
        self.assertTrue(result["signed_for_supplied_ed25519_key"])
        for flag in (
            "independent_owner_signer_authenticated",
            "external_tip_pin_independently_authenticated",
            "actual_git_ref_verified",
            "highwater_immutability_monotonicity_proven",
            "atomic_cas_executed",
            "source_rights_or_bar_finality_attested",
            "cache_head_published", "signals_or_trades_eligible",
        ):
            self.assertIs(result[flag], False)
        report = json.dumps(result)
        for private in (
            a["body"]["head_pin"]["file_id"],
            a["body"]["head_pin"]["source_sha256"],
            a["body"]["head_pin"]["run_id"],
            a["signature_b64"], KEY_ID, SERIES,
        ):
            self.assertNotIn(private, report)

    def test_three_valid_signed_monotone_edges(self):
        a = genesis()
        b = successor(a, 2)
        c = successor(b, 3)
        result = check([a,b,c])
        self.assertEqual(result["checkpoint_count"], 3)
        self.assertEqual(result["linked_edges"], 2)
        self.assertEqual(h.checkpoint_digest(c), sha256(h._canonical(c,max_bytes=4096)).hexdigest())

    def test_canonical_equivalent_ordering_keeps_expected_tip(self):
        a = genesis()
        shuffled = {
            "signature_b64": a["signature_b64"],
            "body": dict(reversed(list(a["body"].items()))),
            "key_id": a["key_id"],
            "schema": a["schema"],
        }
        self.assertEqual(h.checkpoint_digest(shuffled),h.checkpoint_digest(a))
        self.assertEqual(check([shuffled])["checkpoint_count"],1)

    def test_tampered_signed_body_cannot_verify_with_original_signature(self):
        a = genesis()
        bad = deepcopy(a)
        bad["body"]["head_pin"]["source_sha256"] = "a"*64
        with self.assertRaisesRegex(h.HighwaterDenied,"ED25519_SIGNATURE_INVALID"):
            check([bad])

    def test_wrong_external_public_key_denied(self):
        different = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        with self.assertRaisesRegex(h.HighwaterDenied,"ED25519_SIGNATURE_INVALID"):
            check([genesis()],pub=different)

    def test_wrong_external_tip_pin_denied(self):
        with self.assertRaisesRegex(h.HighwaterDenied,"EXTERNAL_TIP_MISMATCH"):
            check([genesis()],tip="0"*64)

    def test_signed_hash_link_stale_tampered_previous_denied(self):
        a = genesis()
        b = successor(a, 2, previous_checkpoint_sha256="a"*64)
        with self.assertRaisesRegex(h.HighwaterDenied,"SIGNED_LINK_OR_REPLAY_DENIED"):
            check([a,b])

    def test_signed_previous_head_pin_drift_denied(self):
        a = genesis()
        b = successor(a, 2, previous_head_pin=pin(99))
        with self.assertRaisesRegex(h.HighwaterDenied,"SIGNED_LINK_OR_REPLAY_DENIED"):
            check([a,b])

    def test_signed_same_or_older_run_denied(self):
        a = genesis()
        for earlier in (pin(1, file_id="DifferentFakeFile0001"), pin(1)):
            b = successor(a, 2, head_pin=earlier)
            with self.subTest(p=earlier), self.assertRaisesRegex(
                h.HighwaterDenied, "SIGNED_LINK_OR_REPLAY_DENIED"
            ):
                check([a,b])

    def test_signed_same_chunk_digest_again_denied(self):
        a = genesis()
        b = successor(
            a, 2,
            head_pin=pin(2, source_sha=a["body"]["head_pin"]["source_sha256"]),
        )
        with self.assertRaisesRegex(h.HighwaterDenied,"SIGNED_LINK_OR_REPLAY_DENIED"):
            check([a,b])

    def test_signed_different_source_scope_denied(self):
        a = genesis()
        for variant in ({"provider":"DNSE"}, {"symbol":"HPG"},{"native_tf":"H1"}):
            b = successor(a, 2, head_pin=pin(2, **variant))
            with self.subTest(variant=variant),self.assertRaisesRegex(
                h.HighwaterDenied, "SIGNED_LINK_OR_REPLAY_DENIED"
            ):
                check([a,b])

    def test_signed_changed_series_rejected(self):
        a = genesis()
        b = successor(a, 2, series_id="HPG_D1_SSI_FAKE")
        with self.assertRaisesRegex(h.HighwaterDenied,"SIGNED_LINK_OR_REPLAY_DENIED"):
            check([a,b])

    def test_sequence_missing_checkpoint_denied(self):
        a = genesis()
        c = successor(a, 3)
        with self.assertRaisesRegex(h.HighwaterDenied,"CHECKPOINT_SEQUENCE_GAP"):
            check([a,c])

    def test_genesis_cannot_have_a_previous_checkpoint(self):
        for broken in (
            {"previous_checkpoint_sha256":"b"*64},
            {"previous_head_pin":pin(2)},
        ):
            with self.subTest(broken=broken),self.assertRaisesRegex(
                h.HighwaterDenied, "GENESIS_PREDECESSOR_DENIED"
            ):
                check([genesis(**broken)])

    def test_malformed_secret_key_id_and_public_key_inputs_denied(self):
        a = genesis()
        for key, pub, tip in (
            ("bad",PUBLIC,h.checkpoint_digest(a)),
            (KEY_ID,b"short",h.checkpoint_digest(a)),
            (KEY_ID,PUBLIC,"A"*64),
            (KEY_ID,PUBLIC,True),
        ):
            with self.subTest(key=key,pub=pub,tip=tip),self.assertRaisesRegex(
                h.HighwaterDenied,"EXTERNAL_TRUST_INPUT_INVALID"
            ):
                h.verify_signed_highwater_candidates(
                    [a],trusted_key_id=key,
                    trusted_ed25519_public_key=pub,
                    expected_tip_checkpoint_sha256=tip,
                )

    def test_not_a_trading_authority_even_if_attestation_flags_signed(self):
        for name in h.FALSE_FIELDS:
            with self.subTest(name=name),self.assertRaisesRegex(
                h.HighwaterDenied, "CHECKPOINT_BODY_DENIED"
            ):
                check([genesis(**{name:True})])

    def test_unrecognized_body_fields_denied(self):
        a = genesis()
        bad = deepcopy(a)
        bad["body"]["private_market_price"]="secret"
        with self.assertRaisesRegex(h.HighwaterDenied,"CHECKPOINT_BODY_DENIED"):
            check([bad])

    def test_invalid_native_provider_and_timeframe_denied(self):
        for p in (
            pin(1, provider="VCBS"),
            pin(1, native_tf="H4"),
            pin(1, symbol="AA"),
            pin(1, file_id="../malicious"),
            pin(1, run_id="00012345"),
            pin(1, source_sha256="not-hash"),
        ):
            with self.subTest(p=p),self.assertRaisesRegex(
                h.HighwaterDenied,"HEAD_PIN_INVALID"
            ):
                check([genesis(head_pin=p)])

    def test_signature_not_canonical_base64_denied(self):
        a = genesis()
        for sig in (a["signature_b64"][:-1]+"?", "x",
                    a["signature_b64"][:10]+"?"+a["signature_b64"][11:]):
            bad=deepcopy(a)
            bad["signature_b64"]=sig
            with self.subTest(sig=sig[:10]),self.assertRaises(h.HighwaterDenied):
                check([bad])

    def test_bool_sequence_and_extra_checkpoint_denied(self):
        with self.assertRaisesRegex(h.HighwaterDenied,"CHECKPOINT_BODY_DENIED"):
            check([genesis(sequence=True)])
        bad=deepcopy(genesis())
        bad["extra"]="bad"
        with self.assertRaisesRegex(h.HighwaterDenied,"CHECKPOINT_ENVELOPE_INVALID"):
            check([bad])

    def test_bounded_checkpoint_count_and_nonfinite_json(self):
        a=genesis()
        for bad in ([], [a]*129, "not list", [a, a]):
            with self.subTest(kind=type(bad).__name__),self.assertRaises(h.HighwaterDenied):
                check(bad)
        for data in ({"n":float("nan")}, {"n":float("inf")}):
            with self.assertRaisesRegex(h.HighwaterDenied,"CANONICAL_JSON_INVALID"):
                h._canonical(data,max_bytes=2048)

    def test_no_network_signing_or_private_credential_from_runtime_script(self):
        source = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_signed_highwater_diagnostic.py").read_text()
        for forbidden in (
            "Ed25519PrivateKey", "requests.post(", "urlopen(", "google.auth",
            "GITHUB_TOKEN", "MST_SSI_API_SECRET", "session.delete(",
            "subprocess", "os.environ",
        ):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
