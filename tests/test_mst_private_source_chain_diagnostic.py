"""§195: synthetic only, bounded unpublished private candidate graph diagnostics."""
from __future__ import annotations

from copy import deepcopy
from hashlib import md5,sha256
import json
import unittest

from scripts.mst_private_source_chain_diagnostic import (
    LineageDenied,verify_private_source_chain,
)
from scripts import mst_mfx_style_appowned_pipeline as cloud
from scripts import mst_ssi_native_stage as ssi_stage
from test_mst_mfx_style_appowned_pipeline import (
    FakeQuarantineDrive,DnseNative,stage_owner_env,
)
from test_mst_ssi_native_stage import (
    Drive as SsiDrive,env as ssi_env,source_rows,
)

RUNS=("43270010001","43270010002","43270010003")
PROVIDER_NAME={
    "DNSE":"DNSE_OFFICIAL_OPENAPI",
    "SSI":"SSI_FASTCONNECT_V3_MARKET_DATA",
}


def seal(record):
    """Recompute a fabricated mutable Drive envelope; not proof of authority."""
    archive=record["archive"]
    body=json.dumps(archive,sort_keys=True,separators=(",",":"),
                    allow_nan=False).encode()
    record["body"]=body
    info=record["metadata"]
    info["size"]=str(len(body))
    info["md5Checksum"]=md5(body).hexdigest()
    info["appProperties"]["source_sha256"]=sha256(body).hexdigest()
    return record


def synthetic(provider,run,*,tf="D1",symbol="FPT",different=False):
    if provider=="DNSE":
        d=FakeQuarantineDrive()
        payload=DnseNative().payload()
        if different:
            payload["v"][1]+=7
        cloud.stage_unpublished_dnse_source(
            d,stage_owner_env(GITHUB_RUN_ID=run),payload,
        )
        info,body=deepcopy(d.file_info),d.media
    else:
        d=SsiDrive()
        rows=source_rows(tf)
        if different:
            rows=deepcopy(rows)
            rows[-1]["volume"]="345"
        ssi_stage.stage_ssi_native_source(
            d,ssi_env(tf,GITHUB_RUN_ID=run),rows,
        )
        info,body=deepcopy(d.new_info),d.new_body
    # Fake Drive classes use a constant created ID for each invocation;
    # give each independently staged observation a unique fake file ID.
    ident="FAKE_CANDIDATE_"+provider+"_"+run
    info["id"]=ident
    return {
        "file_id":ident,"metadata":info,"body":body,
        "archive":json.loads(body),
    }


def link(child,parent):
    child["archive"]["prior_source_incremental_delta"]={
        "schema":"mst.private.synthetic_delta.v0",
        "prior_private_file_id":parent["file_id"],
        "prior_source_sha256":sha256(parent["body"]).hexdigest(),
        "delta":{"eligible_for_signals":False},
        "eligible_for_signals":False,
    }
    return seal(child)


def record(obj):
    return {k:deepcopy(obj[k]) for k in ("file_id","metadata","body")}


def pin(obj,provider,tf="D1",symbol="FPT"):
    return {
        "provider":provider,"symbol":symbol,"native_tf":tf,
        "file_id":obj["file_id"],
        "run_id":obj["metadata"]["appProperties"]["source_run_id"],
        "source_sha256":sha256(obj["body"]).hexdigest(),
    }


def chain(provider="DNSE",tf="D1"):
    a=synthetic(provider,RUNS[0],tf=tf)
    b=synthetic(provider,RUNS[1],tf=tf,different=True)
    link(b,a)
    c=synthetic(provider,RUNS[2],tf=tf)
    link(c,b)
    return a,b,c


def check(parts,root,head,provider="DNSE",tf="D1",**kw):
    return verify_private_source_chain(
        [record(x) for x in parts],
        parent=parts[0]["metadata"]["parents"][0] if parts else "FAKE_CHUNKS_1234567890",
        floor_pin=pin(root,provider,tf),
        expected_head_pin=pin(head,provider,tf),
        complete_census_supplied=True,
        **kw,
    )


class SourceChainDiagnosticTests(unittest.TestCase):
    def test_three_generation_source_chain_stays_unpublished(self):
        for provider,tf in (("DNSE","D1"),("SSI","D1"),("SSI","M5")):
            with self.subTest(provider=provider,tf=tf):
                a,b,c=chain(provider,tf)
                result=check([c,a,b],a,c,provider,tf)
                self.assertEqual(result["candidate_count"],3)
                self.assertEqual(result["linked_edges_verified"],2)
                self.assertTrue(result["all_supplied_records_accounted_for"])
                for key in ("external_pin_signature_verified",
                            "independent_monotone_highwater_verified",
                            "drive_census_independently_verified",
                            "signed_atomic_publish_cas_verified",
                            "source_finality_verified","signal_eligible",
                            "cache_published"):
                    self.assertFalse(result[key],key)

    def test_standalone_explicit_floor_equals_head_is_diagnostic_only(self):
        a=synthetic("DNSE",RUNS[0])
        proof=check([a],a,a)
        self.assertEqual(proof["linked_edges_verified"],0)
        self.assertFalse(proof["cache_published"])

    def test_missing_middle_candidate_denied(self):
        a,b,c=chain()
        with self.assertRaisesRegex(LineageDenied,"BROKEN_OR_REVERSED_EDGE"):
            check([a,c],a,c)

    def test_missing_root_or_known_head_denied(self):
        a,b,c=chain()
        with self.assertRaisesRegex(LineageDenied,"FLOOR_PIN_MISMATCH"):
            check([b,c],a,c)
        with self.assertRaisesRegex(LineageDenied,"HEAD_PIN_MISMATCH"):
            check([a,b],a,c)

    def test_fork_at_anchored_root_denied(self):
        a,b,c=chain()
        c["archive"]["prior_source_incremental_delta"]["prior_private_file_id"]=a["file_id"]
        c["archive"]["prior_source_incremental_delta"]["prior_source_sha256"]=sha256(a["body"]).hexdigest()
        seal(c)
        with self.assertRaisesRegex(LineageDenied,"FORK_NOT_A_LINEAR_HISTORY"):
            check([a,b,c],a,c)

    def test_fresh_unlinked_capture_cannot_claim_continuous_lineage(self):
        a,b,c=chain()
        b["archive"].pop("prior_source_incremental_delta")
        seal(b)
        link(c,b)
        with self.assertRaisesRegex(LineageDenied,"PREDECESSOR_REQUIRED"):
            check([a,b,c],a,c)

    def test_out_of_order_run_or_self_link_denied(self):
        a,b,c=chain()
        b["archive"]["prior_source_incremental_delta"]["prior_private_file_id"]=b["file_id"]
        b["archive"]["prior_source_incremental_delta"]["prior_source_sha256"]=sha256(b["body"]).hexdigest()
        seal(b)
        with self.assertRaisesRegex(LineageDenied,"BROKEN_OR_REVERSED_EDGE"):
            check([a,b,c],a,c)

    def test_duplicate_file_id_or_duplicate_run_denied(self):
        a,b,c=chain()
        with self.assertRaisesRegex(LineageDenied,"DUPLICATE_FILE_OR_RUN"):
            check([a,b,b],a,b)
        c["metadata"]["appProperties"]["source_run_id"]=b["metadata"]["appProperties"]["source_run_id"]
        c["metadata"]["name"]=b["metadata"]["name"]
        # This is already a forbidden candidate identity mismatch.
        with self.assertRaises(LineageDenied):
            check([a,b,c],a,c)

    def test_anchored_head_sha_replaced_denied_after_rehash(self):
        a,b,c=chain()
        expected_head=pin(c,"DNSE")
        c["archive"]["raw_native"]["v"][-1]+=1
        # native digest is now stale: independently still denied.
        seal(c)
        with self.assertRaises(LineageDenied):
            verify_private_source_chain(
                [record(x) for x in (a,b,c)],
                parent=a["metadata"]["parents"][0],
                floor_pin=pin(a,"DNSE"),
                expected_head_pin=expected_head,
                complete_census_supplied=True,
            )

    def test_root_was_rewritten_with_fully_consistent_body_sha_denied(self):
        a,b,c=chain()
        original_pin=pin(a,"DNSE")
        a["archive"]["local_receive_utc"]="2026-11-15T00:00:00+00:00"
        seal(a)
        with self.assertRaisesRegex(LineageDenied,"(FLOOR_PIN_MISMATCH|BROKEN_OR_REVERSED_EDGE)"):
            verify_private_source_chain(
                [record(x) for x in (a,b,c)],
                parent=a["metadata"]["parents"][0],
                floor_pin=original_pin,
                expected_head_pin=pin(c,"DNSE"),
                complete_census_supplied=True,
            )

    def test_protection_requires_census_and_pins(self):
        a,b,c=chain()
        f,h=pin(a,"DNSE"),pin(c,"DNSE")
        for raw in ([],[record(a)]*129,{"fake":"dict"}):
            with self.subTest(kind=type(raw).__name__),self.assertRaises(LineageDenied):
                verify_private_source_chain(
                    raw,parent=a["metadata"]["parents"][0],
                    floor_pin=f,expected_head_pin=h,
                    complete_census_supplied=True,
                )
        with self.assertRaisesRegex(LineageDenied,"SCOPE_OR_CENSUS_UNVERIFIED"):
            verify_private_source_chain(
                [record(x) for x in (a,b,c)],
                parent=a["metadata"]["parents"][0],
                floor_pin=f,expected_head_pin=h,
                complete_census_supplied=False,
            )
        bad=dict(h,source_sha256="f"*64)
        with self.assertRaisesRegex(LineageDenied,"HEAD_PIN_MISMATCH"):
            verify_private_source_chain(
                [record(x) for x in (a,b,c)],
                parent=a["metadata"]["parents"][0],
                floor_pin=f,expected_head_pin=bad,
                complete_census_supplied=True,
            )

    def test_wrong_provider_tf_symbol_or_private_acl_denied(self):
        a,b,c=chain()
        for key,value in (("provider","SSI"),("native_tf","M5"),("symbol","DCM")):
            with self.subTest(field=key):
                bad=pin(c,"DNSE")
                bad[key]=value
                with self.assertRaises(LineageDenied):
                    verify_private_source_chain(
                        [record(x) for x in (a,b,c)],
                        parent=a["metadata"]["parents"][0],
                        floor_pin=pin(a,"DNSE"),expected_head_pin=bad,
                        complete_census_supplied=True,
                    )
        a["metadata"]["shared"]=True
        with self.assertRaisesRegex(LineageDenied,"PRIVATE_RECORD_INTEGRITY_INVALID"):
            check([a,b,c],a,c)

    def test_stale_head_pin_rejected_with_complete_census(self):
        a,b,c=chain()
        with self.assertRaisesRegex(LineageDenied,"GAP_OR_UNANCHORED_BRANCH"):
            check([a,b,c],a,b)

    def test_new_valid_but_foreign_sibling_candidate_rejected(self):
        a,b,c=chain()
        alien=synthetic("SSI","43270010004")
        with self.assertRaises(LineageDenied):
            check([a,b,c,alien],a,c)


if __name__=="__main__":
    unittest.main()
