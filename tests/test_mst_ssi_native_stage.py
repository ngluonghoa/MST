"""Strict SSI Cloud Cache-stage tests: 100% fabricated HTTP/Drive/OHLCV.

No user account, market-data rights, live quote or real OAuth is used here.
"""
from __future__ import annotations

import hashlib
import json
import unittest

from scripts import mst_mfx_style_appowned_pipeline as cloud
from scripts import mst_ssi_native_stage as stage
from scripts import mst_mfx_ssi_readonly as ssi


def env(tf="M5", **extra):
    data = {
        "GITHUB_REPOSITORY":cloud.REPO,
        "GITHUB_REPOSITORY_ID":cloud.REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID":cloud.OWNER_ID,
        "GITHUB_REF":"refs/heads/main",
        "GITHUB_EVENT_NAME":"workflow_dispatch",
        "GITHUB_WORKFLOW_REF":cloud.WORKFLOW,
        "MST_MFX_APP_OWNED_READONLY_ACCEPTED":"true",
        "MST_GDRIVE_OAUTH_CLIENT_ID":"FAKE_CLIENT",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET":"FAKE_SECRET",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN":"FAKE_REFRESH",
        "MST_OAUTH_BOOTSTRAP_ACCEPTED":"false",
        "MST_MFX_SOURCE_MODE":cloud.MODE_SSI_STAGE,
        "MST_SOURCE_TF":tf,
        "MST_SSI_READONLY_OWNER_ACCEPTED":"true",
        "MST_SSI_SOURCE_RIGHTS_CONFIRMED":"true",
        "MST_SSI_STORAGE_RIGHTS_CONFIRMED":"true",
        "MST_MFX_SOURCE_QUARANTINE_WRITE_ACCEPTED":"true",
        "MST_SSI_API_KEY":"FAKE_READONLY_KEY",
        "MST_SSI_API_SECRET":"FAKE_READONLY_SECRET",
        "MST_SSI_SYMBOL":"FPT",
        "MST_SSI_FROM_DATE":"2026-11-11",
        "MST_SSI_TO_DATE":"2026-11-13" if tf=="D1" else "2026-11-12",
        "GITHUB_RUN_ID":"43270010001",
        "GITHUB_RUN_ATTEMPT":"1",
    }
    data.update(extra)
    return data


def bar(label, v=200, symbol="FPT"):
    return {"symbol":symbol, "tradingDate":label,
            "open":"100.2","high":"101.0","low":"99.8",
            "close":"100.5","volume":str(v)}


def stamps(tf):
    if tf=="D1":
        return "2026-11-11","2026-11-12","2026-11-13"
    delta={"M5":5,"M15":15,"M30":30,"H1":60}[tf]
    def clock(minutes):
        h=9+minutes//60
        mm=minutes%60
        return f"2026-11-12 {h:02d}:{mm:02d}:00"
    return clock(0),clock(delta),clock(delta*2)


def source_rows(tf="M5", old=False):
    first,second,third=stamps(tf)
    return ([bar(first,200),bar(second,250)] if old
            else [bar(second,255),bar(third,300)])


def archive(tf="M5", symbol="FPT"):
    old=source_rows(tf,old=True)
    # D1 second day 12 and first day 11, while intraday both are day 12.
    return {
        "schema":"mst.cloud.ssi_native_unpublished_candidate.v0.1",
        "project":"MST","source":"SSI_FASTCONNECT_V3_MARKET_DATA",
        "symbol":symbol,"source_native_tf":tf,
        "resolution": {"M5":"5m","M15":"15m","M30":"30m","H1":"1h","D1":"1d"}[tf],
        "from_date":"2026-11-11","to_date":"2026-11-13",
        "issuer_first_known_verified":False,
        "official_venue_closed_verified":False,
        "price_unit_adjusted_basis_verified":False,
        "independent_publish_cas_verified":False,
        "eligible_for_signals":False,"raw_native":old,
    }


class Response:
    def __init__(self, body=None, status=200, raw=None):
        self._body={} if body is None else body
        self.status_code=status
        self.content=json.dumps(self._body).encode() if raw is None else raw
    def json(self):
        return self._body


class Drive:
    LIST="https://www.googleapis.com/drive/v3/files"
    UPLOAD="https://www.googleapis.com/upload/drive/v3/files"
    ROOT="FAKE_APP_ROOT_1234567890"
    CHUNKS="FAKE_CHUNKS_1234567890"
    OLD="FAKE_PRIOR_SSI_1234567890"
    NEW="FAKE_NEW_SSI_1234567890"

    def __init__(self, prior=None):
        self.old_body=None
        self.old_info=None
        if prior:
            self.old_body=json.dumps(prior,sort_keys=True,separators=(",",":"),
                                     allow_nan=False).encode()
            tf=prior["source_native_tf"]
            self.old_info=self._info(self.OLD,
                "MST_UNPUBLISHED_SSI_NATIVE_"+tf+"_43269999999_1.json",
                self.old_body, {
                    "mst_unpublished":"true",
                    "source_sha256":hashlib.sha256(self.old_body).hexdigest(),
                    "source_symbol":prior["symbol"],
                    "source_native_tf":tf,
                    "source_run_id":"43269999999",
                    "schema":"ssi_native_candidate_v1"})
        self.new_info=None
        self.new_body=None
        self.post_count=0
        self.prior_media_count=0
        self.new_media_count=0
        self.census_override=None
        self.mutate_old_version=False
        self.mutate_old_media=False
        self.calls=[]

    def _info(self, fid, name, body, props):
        return {"id":fid,"name":name,"mimeType":"application/json",
                "parents":[self.CHUNKS],"trashed":False,
                "shared":False,"ownedByMe":True,"isAppAuthorized":True,
                "version":"1","size":str(len(body)),
                "md5Checksum":hashlib.md5(body).hexdigest(),
                "appProperties":props}

    def _short(self, info):
        return {k:info[k] for k in
                ("id","name","mimeType","parents","trashed","appProperties")}

    def get(self, url, *, params, timeout, **kwargs):
        self.calls.append(("GET",url,params))
        if url==self.LIST:
            q=params["q"]
            if "name contains 'MST_UNPUBLISHED_SSI_'" in q:
                if self.census_override is not None:
                    return Response(self.census_override)
                return Response({"files":[self._short(x) for x in
                    (self.old_info,self.new_info) if x]})
            name=q.split("name = '",1)[1].split("'",1)[0]
            if name==cloud.DRIVE_ROOT:
                return Response({"files":[{
                    "id":self.ROOT,"name":name,"mimeType":cloud.MIME_FOLDER,
                    "parents":["FAKE_DRIVE_ROOT"],"trashed":False}]})
            if name=="CHUNKS":
                return Response({"files":[{
                    "id":self.CHUNKS,"name":name,"mimeType":cloud.MIME_FOLDER,
                    "parents":[self.ROOT],"trashed":False}]})
            return Response({"files":[
                {k:x[k] for k in ("id","name","mimeType","parents","trashed")}
                for x in (self.old_info,self.new_info) if x and x["name"]==name
            ]})
        if url==cloud.DRIVE_URL+self.OLD and self.old_info:
            if params.get("alt")=="media":
                self.prior_media_count+=1
                return Response(raw=(b"TAMPER" if self.mutate_old_media else self.old_body))
            if self.mutate_old_version and self.prior_media_count>0:
                return Response(dict(self.old_info,version="5"))
            return Response(self.old_info)
        if url==cloud.DRIVE_URL+self.NEW and self.new_info:
            if params.get("alt")=="media":
                self.new_media_count+=1
                return Response(raw=self.new_body)
            return Response(self.new_info)
        return Response(status=404)

    def post(self, url, *, params, data, headers, timeout):
        self.post_count+=1
        assert url==self.UPLOAD
        assert params["uploadType"]=="multipart"
        boundary=headers["Content-Type"].split("boundary=",1)[1].encode()
        chunks=data.split(b"--"+boundary)
        props=json.loads(chunks[1].split(b"\r\n\r\n",1)[1].strip())
        body=chunks[2].split(b"\r\n\r\n",1)[1].removesuffix(b"\r\n")
        self.new_info=self._info(self.NEW,props["name"],body,props["appProperties"])
        self.new_body=body
        return Response({"id":self.NEW},201)


class SsiSourceStaging(unittest.TestCase):
    def stage(self, drive, tf="M5", **changes):
        return stage.stage_ssi_native_source(drive,env(tf,**changes),source_rows(tf))

    def test_native_modes_first_capture_on_five_distinct_tfs(self):
        for tf in ("M5","M15","M30","H1","D1"):
            with self.subTest(tf=tf):
                d=Drive()
                result=self.stage(d,tf)
                self.assertTrue(result["unpublished_private_source_document_stored"])
                self.assertEqual(result["source_native_tf"],tf)
                self.assertEqual(d.post_count,1)
                self.assertEqual(d.new_media_count,2)
                self.assertFalse(result["source_delta_linked_to_prior_private_native_tf"])
                self.assertFalse(result["signals_and_trading_eligible"])
                body=json.loads(d.new_body)
                self.assertEqual(body["source_native_tf"],tf)
                self.assertFalse(body["official_venue_closed_verified"])
                self.assertFalse(body["eligible_for_signals"])
                self.assertNotIn("FAKE_SECRET",str(result))

    def test_all_five_tfs_link_corrupted_overlapping_candle_and_exited_rows(self):
        for tf in ("M5","M15","M30","H1","D1"):
            with self.subTest(tf=tf):
                d=Drive(archive(tf))
                result=self.stage(d,tf)
                self.assertTrue(result["source_delta_linked_to_prior_private_native_tf"])
                self.assertEqual(result["source_delta_added_rows"],1)
                self.assertEqual(result["source_delta_revised_rows"],1)
                self.assertEqual(result["source_delta_window_exited_not_deleted"],1)
                self.assertEqual(d.prior_media_count,2)
                self.assertEqual(d.new_media_count,2)
                data=json.loads(d.new_body)
                delta=data["prior_source_incremental_delta"]["delta"]
                self.assertEqual(delta["revised"][0]["before"]["volume"],"250")
                self.assertEqual(delta["revised"][0]["after"]["volume"],"255")
                self.assertEqual(delta["added"][0]["volume"],"300")
                self.assertEqual(delta["window_exited_not_deleted"][0]["volume"],"200")
                self.assertFalse(delta["eligible_for_signals"])
                self.assertEqual(len(delta["plan_sha256"]),64)

    def test_verified_all_native_tfs_noop_reuses_prior_and_never_reuploads(self):
        for tf in ("M5","M15","M30","H1","D1"):
            for only_exits in (False,True):
                with self.subTest(tf=tf,only_exits=only_exits):
                    d=Drive(archive(tf))
                    original=source_rows(tf,old=True)
                    new=original[1:] if only_exits else original
                    receipt=stage.stage_ssi_native_source(d,env(tf),new)
                    self.assertTrue(receipt["source_noop_reused_verified_prior"])
                    self.assertFalse(receipt["unpublished_private_source_document_stored"])
                    self.assertTrue(receipt["previous_candidate_kept_unmodified"])
                    self.assertEqual(receipt["source_delta_window_exited_not_deleted"],
                                     int(only_exits))
                    self.assertEqual(receipt["source_delta_added_rows"],0)
                    self.assertEqual(receipt["source_delta_revised_rows"],0)
                    self.assertEqual(receipt["stored_object_count"],0)
                    self.assertEqual(d.prior_media_count,2)
                    self.assertEqual(d.new_media_count,0)
                    self.assertEqual(d.post_count,0)
                    self.assertFalse(receipt["signals_and_trading_eligible"])

    def test_rights_manual_main_storage_separate_and_reruns_denied(self):
        for update in (
            {"MST_SSI_SOURCE_RIGHTS_CONFIRMED":"false"},
            {"MST_SSI_STORAGE_RIGHTS_CONFIRMED":"false"},
            {"MST_MFX_SOURCE_QUARANTINE_WRITE_ACCEPTED":"false"},
            {"MST_SSI_READONLY_OWNER_ACCEPTED":"false"},
            {"GITHUB_REF":"refs/heads/draft"},
            {"GITHUB_RUN_ATTEMPT":"2"},
            {"MST_SOURCE_TF":"H4"},
            {"MST_MFX_SOURCE_MODE":cloud.MODE_SSI_NATIVE},
        ):
            with self.subTest(update=update):
                d=Drive()
                with self.assertRaises((ssi.SsiSourceDenied,cloud.CloudGateDenied)):
                    stage.stage_ssi_native_source(d,env(**update),source_rows())
                self.assertEqual(d.post_count,0)

    def test_wrong_symbol_wrong_tf_are_separate_source_histories(self):
        for change in ("symbol","tf"):
            d=Drive(archive("M5"))
            if change=="symbol":
                d.old_info["appProperties"]["source_symbol"]="DCM"
            else:
                d.old_info["name"]=d.old_info["name"].replace("_M5_","_M15_")
                d.old_info["appProperties"]["source_native_tf"]="M15"
            result=self.stage(d)
            self.assertFalse(result["source_delta_linked_to_prior_private_native_tf"])
            self.assertEqual(d.prior_media_count,0)
            self.assertEqual(d.post_count,1)

    def test_missing_prior_no_overlaps_never_reclassify_as_new_valid_capture(self):
        d=Drive(archive())
        new=[bar("2026-11-12 11:00:00"),bar("2026-11-12 11:05:00")]
        with self.assertRaisesRegex(cloud.CloudGateDenied,"NO_OVERLAP"):
            stage.stage_ssi_native_source(d,env(),new)
        self.assertEqual(d.post_count,0)

    def test_prior_invalid_metadata_sharing_hash_media_version_fail_preupload(self):
        for kind in ("shared","owner","hash","media","version","mime","label"):
            d=Drive(archive())
            if kind=="shared":d.old_info["shared"]=True
            if kind=="owner":d.old_info["ownedByMe"]=False
            if kind=="hash":d.old_info["appProperties"]["source_sha256"]="0"*64
            if kind=="media":d.mutate_old_media=True
            if kind=="version":d.mutate_old_version=True
            if kind=="mime":d.old_info["mimeType"]="text/plain"
            if kind=="label":d.old_info["appProperties"]["source_native_tf"]="H1"
            with self.subTest(kind=kind),self.assertRaises(cloud.CloudGateDenied):
                self.stage(d)
            self.assertEqual(d.post_count,0)

    def test_unlabeled_duplicate_self_future_and_broken_census_fail_preupload(self):
        for kind in ("unlabeled","duplicated","self","future","bad_token","unknown","incomplete"):
            d=Drive(archive())
            if kind=="unlabeled":del d.old_info["appProperties"]["source_symbol"]
            if kind=="duplicated":
                d.census_override={"files":[d._short(d.old_info)]*2}
            if kind in ("self","future"):
                run="43270010001" if kind=="self" else "43270010002"
                d.old_info["name"]=d.old_info["name"].replace("43269999999",run)
                d.old_info["appProperties"]["source_run_id"]=run
            if kind=="bad_token":
                d.census_override={"files":[d._short(d.old_info)],
                                   "nextPageToken":"token"}
            if kind=="unknown":
                d.old_info["name"]="MST_UNPUBLISHED_SSI_UNKNOWN_43269999999_1.json"
            if kind=="incomplete":
                d.census_override={"files":[d._short(d.old_info)],
                                   "incompleteSearch":True}
            with self.subTest(kind=kind),self.assertRaises(cloud.CloudGateDenied):
                self.stage(d)
            self.assertEqual(d.post_count,0)

    def test_duplicate_current_attempt_without_retry_avoids_double_upload(self):
        d=Drive()
        self.stage(d)
        self.assertEqual(d.post_count,1)
        with self.assertRaises(cloud.CloudGateDenied):
            self.stage(d)
        self.assertEqual(d.post_count,1)

    def test_source_validation_fails_before_any_write(self):
        for bad in (
            [bar("2026-11-12 09:00:00"),bar("2026-11-12 09:00:00")],
            [dict(bar("2026-11-12 09:00:00"),unknown_token="TOP_SECRET")],
            [bar("2026-11-12")],
            [dict(bar("2026-11-12 09:00:00"),volume="1.5")],
        ):
            d=Drive()
            with self.subTest(bad=bad),self.assertRaises(cloud.CloudGateDenied):
                stage.stage_ssi_native_source(d,env(),bad)
            self.assertEqual(d.post_count,0)


class ReadOnlyNotLeakingSource(unittest.TestCase):
    def test_native_fetch_includes_bounded_source_while_public_receipt_does_not(self):
        class FakeSsiApi:
            def post(self, *args, **kwargs):
                return Response({"tokenType":"Bearer",
                                 "accessToken":"FAKE_MARKETDATA_JWT_"+("x"*30)})
            def get(self, *args, **kwargs):
                return Response({"pageIndex":1,"pageSize":100,"pageCount":1,
                                 "data":[bar("2026-11-12")]})
        api=FakeSsiApi()
        settings=env("D1",MST_MFX_SOURCE_MODE=cloud.MODE_SSI)
        report,rows=ssi._fetch_ssi_native_once(api,settings)
        self.assertEqual(len(rows),1)
        self.assertEqual(set(rows[0]),set(stage.NATIVE_KEYS))
        self.assertNotIn("value",rows[0])
        self.assertNotIn("accessToken",str(report))
        self.assertNotIn("tradingDate",str(report))
        summary=ssi.read_ssi_native_once(FakeSsiApi(),settings)
        self.assertNotIn("tradingDate",str(summary))
        self.assertFalse(summary["private_data_stored_to_drive"])


if __name__=="__main__":
    unittest.main()
