"""MFX-style MST Cloud preflight tests; ALL data and OAuth responses fabricated."""
import json
import unittest

from scripts import mst_mfx_style_appowned_pipeline as m


def owner_env(**updates):
    env = {
        "GITHUB_REPOSITORY":m.REPO,
        "GITHUB_REPOSITORY_ID":m.REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID":m.OWNER_ID,
        "GITHUB_REF":"refs/heads/main",
        "GITHUB_EVENT_NAME":"workflow_dispatch",
        "GITHUB_WORKFLOW_REF":m.WORKFLOW,
        "MST_MFX_APP_OWNED_READONLY_ACCEPTED":"true",
        "MST_GDRIVE_OAUTH_CLIENT_ID":"FAKE_CLIENT",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET":"FAKE_SECRET",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN":"FAKE_REFRESH",
        "MST_OAUTH_BOOTSTRAP_ACCEPTED":"false",
    }
    env.update(updates)
    return env


class FakeResponse:
    def __init__(self, data, status=200):
        self._data=data
        self.status_code=status
        self.content=json.dumps(data).encode("utf-8")
    def json(self):
        return self._data


class FakeDrive:
    def __init__(self):
        self.calls=[]
        self.root="FAKE_APP_ROOT_1234567890"
        names=(m.DRIVE_ROOT,*m.DRIVE_CHILDREN)
        self.files={
          f"FAKE_APP_{n}_1234567890":{
            "id":f"FAKE_APP_{n}_1234567890",
            "name":n,"mimeType":m.MIME_FOLDER,
            "parents":[self.root if n!=m.DRIVE_ROOT else "FAKE_MY_DRIVE_ROOT"],
            "trashed":False,"shared":False,
            "ownedByMe":True,"isAppAuthorized":True,
          } for n in names
        }
        self.files[f"FAKE_APP_{m.DRIVE_ROOT}_1234567890"]["id"]=self.root
        root_item=self.files.pop(f"FAKE_APP_{m.DRIVE_ROOT}_1234567890")
        self.files[self.root]=root_item
        self.overrides={}
        self.duplicate=False
    def get(self,url,*,params,timeout):
        self.calls.append(("GET",url,params))
        if url == m.DRIVE_URL[:-1]:
            query=params["q"]
            n=query.split("name = '",1)[1].split("'",1)[0]
            files=[dict(v) for v in self.files.values() if v["name"]==n]
            if self.duplicate and n==m.DRIVE_ROOT:
                files.append(dict(files[0],id="FAKE_DUP_123456"))
            return FakeResponse({"files":files})
        key=url[len(m.DRIVE_URL):]
        if key not in self.files:return FakeResponse({},404)
        return FakeResponse(dict(self.files[key],**self.overrides.get(key,{})))


class Gates(unittest.TestCase):
    def test_cloud_manual_main_owner_accepted_drive(self):
        mode,secret=m.guard(owner_env())
        self.assertEqual(mode,m.MODE_DRIVE)
        self.assertNotIn("FAKE_SECRET",repr(secret))

    def test_not_started_without_owner_gate(self):
        with self.assertRaises(m.CloudGateDenied):
            m.guard(owner_env(MST_MFX_APP_OWNED_READONLY_ACCEPTED="false"))

    def test_no_cron_no_branch_no_crossproject(self):
        for change in ({"GITHUB_EVENT_NAME":"schedule"},
                       {"GITHUB_REF":"refs/heads/test"},
                       {"GITHUB_REPOSITORY":"ngluonghoa/MFX"}):
            with self.subTest(change=change), self.assertRaises(m.CloudGateDenied):
                m.guard(owner_env(**change))

    def test_no_legacy_sa_or_bootstrap_write(self):
        with self.assertRaises(m.CloudGateDenied):
            m.guard(owner_env(MST_GDRIVE_SERVICE_ACCOUNT_JSON="FAKE"))
        with self.assertRaises(m.CloudGateDenied):
            m.guard(owner_env(MST_OAUTH_BOOTSTRAP_ACCEPTED="true"))

    def test_dnse_requires_rights_and_dedicated_credentials(self):
        kwargs={"MST_MFX_SOURCE_MODE":m.MODE_DNSE,
                "MST_DNSE_SYMBOL":"FPT",
                "MST_DNSE_FROM_UNIX":"1794000000",
                "MST_DNSE_TO_UNIX":"1794500000"}
        with self.assertRaises(m.CloudGateDenied):
            m.guard(owner_env(**kwargs))
        kwargs.update({"MST_DNSE_READONLY_OWNER_ACCEPTED":"true",
                       "MST_DNSE_SOURCE_RIGHTS_CONFIRMED":"true",
                       "MST_DNSE_API_KEY":"FAKE_KEY",
                       "MST_DNSE_API_SECRET":"FAKE_SECRET"})
        self.assertEqual(m.guard(owner_env(**kwargs))[0],m.MODE_DNSE)
        kwargs["MST_DNSE_SYMBOL"]="EURUSD"
        with self.assertRaises(m.CloudGateDenied):
            m.guard(owner_env(**kwargs))


class PrivateDrive(unittest.TestCase):
    def test_exact_private_owned_folder_set(self):
        s=FakeDrive()
        result=m.inspect_app_owned_drive(s)
        self.assertEqual(result["app_owned_folder_count"],5)
        self.assertTrue(result["exact_app_owned_private_scope_verified"])
        self.assertEqual(result["drive_writes"],0)
        self.assertTrue(all(call[0]=="GET" for call in s.calls))

    def test_missing_root_rejects(self):
        s=FakeDrive()
        s.files.pop(s.root)
        with self.assertRaises(m.CloudGateDenied):
            m.inspect_app_owned_drive(s)

    def test_public_or_unowned_or_not_app_authorized_rejects(self):
        for key,value in (("shared",True),("ownedByMe",False),
                          ("isAppAuthorized",False),("trashed",True)):
            s=FakeDrive()
            fid=next(i for i,f in s.files.items() if f["name"]=="CHUNKS")
            s.overrides[fid]={key:value}
            with self.subTest(key=key),self.assertRaises(m.CloudGateDenied):
                m.inspect_app_owned_drive(s)


class DnseNative(unittest.TestCase):
    def payload(self):
        return {"t":[1794000000,1794086400],
                "o":[100,101],"h":[102,103],"l":[99,100],
                "c":[101,102],"v":[200,250],"nextTime":0}

    def test_marketdata_request_signing_never_leaks_secret(self):
        url,h=m.build_dnse_request("FPT",1794000000,1794500000,
            "FAKE_KEY","FAKE_SECRET",
            date_header="Fri, 13 Nov 2026 00:00:00 +0000",nonce="a"*32)
        self.assertTrue(url.startswith("https://openapi.dnse.com.vn/price/ohlc?"))
        self.assertIn("Signature keyId=",h["X-Signature"])
        self.assertNotIn("FAKE_SECRET",url+json.dumps(h))
        self.assertEqual(h["version"],m.DNSE_VERSION)

    def test_ohlcv_native_valid_observation_only(self):
        o=m.validate_dnse_native(self.payload(),1794000000,1794500000)
        self.assertEqual(o["observed_native_d1_rows"],2)
        self.assertFalse(o["trade_signal_eligible"])
        self.assertFalse(o["market_data_written_to_drive"])
        self.assertFalse(o["native_source_close_issuer_attested"])

    def test_truncated_or_incomplete_rejected(self):
        payload=self.payload()
        payload["v"].pop()
        with self.assertRaises(m.CloudGateDenied):
            m.validate_dnse_native(payload,1794000000,1794500000)
        payload=self.payload()
        payload["nextTime"]=1794500001
        with self.assertRaises(m.CloudGateDenied):
            m.validate_dnse_native(payload,1794000000,1794500000)

    def test_ohlc_invariant_rejected(self):
        payload=self.payload()
        payload["l"][0]=105
        with self.assertRaises(m.CloudGateDenied):
            m.validate_dnse_native(payload,1794000000,1794500000)

    def test_price_or_duplicate_timestamp_rejected(self):
        payload=self.payload()
        payload["t"][1]=payload["t"][0]
        with self.assertRaises(m.CloudGateDenied):
            m.validate_dnse_native(payload,1794000000,1794500000)
        payload=self.payload()
        payload["o"][0]=float("nan")
        with self.assertRaises(m.CloudGateDenied):
            m.validate_dnse_native(payload,1794000000,1794500000)



def stage_owner_env(**updates):
    return owner_env(**{
        "MST_MFX_SOURCE_MODE":m.MODE_STAGE,
        "MST_DNSE_READONLY_OWNER_ACCEPTED":"true",
        "MST_DNSE_SOURCE_RIGHTS_CONFIRMED":"true",
        "MST_DNSE_STORAGE_RIGHTS_CONFIRMED":"true",
        "MST_MFX_SOURCE_QUARANTINE_WRITE_ACCEPTED":"true",
        "MST_DNSE_API_KEY":"FAKE_MARKETDATA_ID",
        "MST_DNSE_API_SECRET":"FAKE_MARKETDATA_SECRET",
        "MST_DNSE_SYMBOL":"FPT",
        "MST_DNSE_FROM_UNIX":"1794000000",
        "MST_DNSE_TO_UNIX":"1794500000",
        "GITHUB_RUN_ID":"43270010001",
        "GITHUB_RUN_ATTEMPT":"1",
        **updates,
    })


class FakeQuarantineDrive(FakeDrive):
    FILE_ID="FAKE_UNPUBLISHED_DOC_1234567890"
    def __init__(self):
        super().__init__()
        self.media=None
        self.file_info=None
        self.post_calls=0
        self.media_reads=0
        self.mutate_media=False
        self.name_lookup_count=0

    def get(self,url,*,params,timeout,**kwargs):
        if url=="https://www.googleapis.com/drive/v3/files":
            q=params.get("q","")
            if "MST_UNPUBLISHED_DNSE_D1_" in q:
                self.name_lookup_count+=1
                files=[]
                if self.file_info:
                    files=[{k:self.file_info[k] for k in
                            ("id","name","mimeType","parents","trashed")}]
                return FakeResponse({"files":files})
        if url==m.DRIVE_URL+self.FILE_ID:
            if params.get("alt")=="media":
                self.media_reads+=1
                o=FakeResponse({"ignored":"private_source_body"})
                o.content=(b"TAMPERED" if self.mutate_media else self.media)
                return o
            return FakeResponse(self.file_info)
        return super().get(url,params=params,timeout=timeout)

    def post(self,url,*,params,data,headers,timeout):
        self.post_calls+=1
        assert url=="https://www.googleapis.com/upload/drive/v3/files"
        assert params["uploadType"]=="multipart"
        boundary=headers["Content-Type"].split("boundary=",1)[1]
        first=b"--"+boundary.encode()
        assert data.startswith(first+b"\r\nContent-Type:")
        parts=data.split(first)
        metadata=json.loads(parts[1].split(b"\r\n\r\n",1)[1].strip())
        body=parts[2].split(b"\r\n\r\n",1)[1].removesuffix(b"\r\n")
        self.media=body
        import hashlib
        self.file_info={
            "id":self.FILE_ID,"name":metadata["name"],"mimeType":"application/json",
            "parents":metadata["parents"],"trashed":False,
            "shared":False,"ownedByMe":True,"isAppAuthorized":True,
            "version":"1","size":str(len(body)),
            "md5Checksum":hashlib.md5(body).hexdigest(),
            "appProperties":metadata["appProperties"],
        }
        return FakeResponse({"id":self.FILE_ID},201)


class UnpublishedSourceStage(unittest.TestCase):
    def test_stage_requires_independent_owner_storage_license_gate(self):
        payload=DnseNative().payload()
        d=FakeQuarantineDrive()
        bad=stage_owner_env(MST_MFX_SOURCE_QUARANTINE_WRITE_ACCEPTED="false")
        with self.assertRaises(m.CloudGateDenied):
            m.stage_unpublished_dnse_source(d,bad,payload)
        self.assertEqual(d.post_calls,0)

    def test_stage_rejects_workflow_rerun(self):
        payload=DnseNative().payload()
        d=FakeQuarantineDrive()
        with self.assertRaises(m.CloudGateDenied):
            m.stage_unpublished_dnse_source(d,stage_owner_env(GITHUB_RUN_ATTEMPT="2"),payload)
        self.assertEqual(d.post_calls,0)

    def test_stage_uses_exact_app_chunk_and_two_real_media_reads(self):
        payload=DnseNative().payload()
        d=FakeQuarantineDrive()
        r=m.stage_unpublished_dnse_source(d,stage_owner_env(),payload)
        self.assertTrue(r["unpublished_private_source_document_stored"])
        self.assertTrue(r["readback_sha256_verified"])
        self.assertTrue(r["not_a_cache_publish_commit"])
        self.assertFalse(r["signals_and_trading_eligible"])
        self.assertEqual(d.post_calls,1)
        self.assertEqual(d.media_reads,2)
        self.assertEqual(d.name_lookup_count,2)
        saved=json.loads(d.media)
        self.assertEqual(saved["raw_native"]["v"],[200,250])
        self.assertFalse(saved["eligible_for_signals"])
        self.assertFalse(saved["independent_publish_cas_verified"])
        # Same run cannot silently upload another source on retry.
        with self.assertRaisesRegex(m.CloudGateDenied,"PREEXISTING_ATTEMPT"):
            m.stage_unpublished_dnse_source(d,stage_owner_env(),payload)
        self.assertEqual(d.post_calls,1)

    def test_mismatch_on_media_readback_cannot_claim_staged_success(self):
        d=FakeQuarantineDrive()
        d.mutate_media=True
        with self.assertRaisesRegex(m.CloudGateDenied,"MEDIA_READBACK_MISMATCH"):
            m.stage_unpublished_dnse_source(d,stage_owner_env(),DnseNative().payload())
        self.assertEqual(d.post_calls,1)

if __name__=="__main__":
    unittest.main()
