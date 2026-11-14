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
        # Cross-check the exact signed target against DNSE's official SDK:
        # the query is not in the HMAC string even though it is on the URL.
        import base64
        import hashlib
        import hmac
        from urllib.parse import quote
        signing=("(request-target): get /price/ohlc\n"
                 "date: Fri, 13 Nov 2026 00:00:00 +0000\n"
                 "nonce: "+("a"*32)).encode()
        signature=quote(base64.b64encode(
            hmac.new(b"FAKE_SECRET",signing,hashlib.sha256).digest()
        ).decode(),safe="")
        self.assertIn('signature="'+signature+'"',h["X-Signature"])
        _,second=m.build_dnse_request(
            "HPG",1794200000,1794500000,"FAKE_KEY","FAKE_SECRET",
            date_header="Fri, 13 Nov 2026 00:00:00 +0000",nonce="a"*32)
        self.assertEqual(second["X-Signature"],h["X-Signature"])

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
            if "MST_UNPUBLISHED_DNSE_" in q:
                self.name_lookup_count+=1
                files=[]
                if self.file_info:
                    files=[{k:self.file_info[k] for k in
                            ("id","name","mimeType","parents","trashed","appProperties")}]
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
        self.assertEqual(d.name_lookup_count,3)  # default D1 full census + before/after
        saved=json.loads(d.media)
        self.assertEqual(saved["raw_native"]["v"],[200,250])
        self.assertFalse(saved["eligible_for_signals"])
        self.assertFalse(saved["independent_publish_cas_verified"])
        # Same run cannot silently upload another source on retry.
        with self.assertRaisesRegex(m.CloudGateDenied,
                                    "PREEXISTING_ATTEMPT|AUTO_D1_FUTURE_OR_SELF_SOURCE|INTRA_SELF_OR_FUTURE_RUN"):
            m.stage_unpublished_dnse_source(d,stage_owner_env(),payload)
        self.assertEqual(d.post_calls,1)

    def test_mismatch_on_media_readback_cannot_claim_staged_success(self):
        d=FakeQuarantineDrive()
        d.mutate_media=True
        with self.assertRaisesRegex(m.CloudGateDenied,"MEDIA_READBACK_MISMATCH"):
            m.stage_unpublished_dnse_source(d,stage_owner_env(),DnseNative().payload())
        self.assertEqual(d.post_calls,1)




class PriorDnseD1IncrementalStage(unittest.TestCase):
    """Exercise private predecessor proof + delta in actual stage via fakes."""
    PRIOR_ID = "FAKE_PRIOR_DNSE_1234567890"

    class Drive(FakeQuarantineDrive):
        def __init__(self, prior_archive):
            super().__init__()
            self.old_body = json.dumps(prior_archive,sort_keys=True,
                                       separators=(",",":"),allow_nan=False).encode()
            import hashlib
            self.old_info={
                "id":PriorDnseD1IncrementalStage.PRIOR_ID,
                "name":"MST_UNPUBLISHED_DNSE_D1_43269999999_1.json",
                "mimeType":"application/json",
                "parents":["FAKE_APP_CHUNKS_1234567890"],
                "trashed":False,"shared":False,
                "ownedByMe":True,"isAppAuthorized":True,
                "size":str(len(self.old_body)),
                "version":"4",
                "md5Checksum":hashlib.md5(self.old_body).hexdigest(),
                "appProperties":{
                    "mst_unpublished":"true",
                    "source_sha256":hashlib.sha256(self.old_body).hexdigest()},
            }
            self.old_media_reads=0
            self.old_tamper=False

        def get(self,url,*,params,timeout,**kwargs):
            if url==m.DRIVE_URL+PriorDnseD1IncrementalStage.PRIOR_ID:
                if params.get("alt")=="media":
                    self.old_media_reads+=1
                    response=FakeResponse({})
                    response.content=(b"BROKEN" if self.old_tamper else self.old_body)
                    return response
                return FakeResponse(self.old_info)
            if url=="https://www.googleapis.com/drive/v3/files":
                query=params.get("q","")
                if self.old_info["name"] in query:
                    return FakeResponse({"files":[{k:self.old_info[k] for k in
                        ("id","name","mimeType","parents","trashed")}]})
            return super().get(url,params=params,timeout=timeout,**kwargs)

    def prior(self):
        return {
            "schema":"mst.cloud.dnse_unpublished_source_candidate.v0.1",
            "project":"MST","source":"DNSE_OFFICIAL_OPENAPI",
            "symbol":"FPT","resolution":"1D","source_native_tf":"D1",
            "from_unix":1793999999,"to_unix":1794200000,
            "issuer_first_known_verified":False,
            "official_venue_closed_verified":False,
            "independent_publish_cas_verified":False,
            "eligible_for_signals":False,
            "raw_native":{
                "t":[1794000000,1794086400],
                "o":[100,101],"h":[102,103],"l":[99,100],
                "c":[101,102],"v":[200,250],"nextTime":0},
        }

    def new_payload(self):
        return {"t":[1794086400,1794172800],
                "o":[101,104],"h":[103,106],"l":[100,103],
                "c":[102,105],"v":[255,300],"nextTime":0}

    def run_stage(self, drive, **updates):
        env=stage_owner_env(MST_DNSE_PREVIOUS_SOURCE_FILE_ID=self.PRIOR_ID,
                            **updates)
        return m.stage_unpublished_dnse_source(drive,env,self.new_payload())

    def test_prior_reads_twice_and_delta_retains_source_revisions(self):
        d=self.Drive(self.prior())
        result=self.run_stage(d)
        self.assertTrue(result["unpublished_private_source_document_stored"])
        self.assertTrue(result["source_delta_linked_to_prior_private_d1"])
        self.assertEqual(result["source_delta_added_rows"],1)
        self.assertEqual(result["source_delta_revised_rows"],1)
        self.assertEqual(result["source_delta_window_exited_not_deleted"],1)
        self.assertEqual(d.old_media_reads,2)
        self.assertEqual(d.media_reads,2)
        self.assertEqual(d.post_calls,1)
        archive=json.loads(d.media)
        link=archive["prior_source_incremental_delta"]
        delta=link["delta"]
        self.assertEqual(delta["added"][0]["source_row"]["volume"],300)
        self.assertEqual(delta["revised"][0]["before"]["volume"],250)
        self.assertEqual(delta["revised"][0]["after"]["volume"],255)
        self.assertFalse(link["eligible_for_signals"])
        self.assertFalse(archive["eligible_for_signals"])
        self.assertFalse(result["signals_and_trading_eligible"])

    def test_without_previous_optional_id_keeps_original_behavior(self):
        d=self.Drive(self.prior())
        env=stage_owner_env()
        result=m.stage_unpublished_dnse_source(d,env,DnseNative().payload())
        self.assertTrue(result["unpublished_private_source_document_stored"])
        self.assertFalse(result["source_delta_linked_to_prior_private_d1"])
        self.assertNotIn("prior_source_incremental_delta",json.loads(d.media))
        self.assertEqual(d.old_media_reads,0)

    def test_wrong_identity_and_tampered_prior_fail_before_new_upload(self):
        wrong=self.prior()
        wrong["symbol"]="HPG"
        d=self.Drive(wrong)
        with self.assertRaisesRegex(m.CloudGateDenied,"IDENTITY_MISMATCH"):
            self.run_stage(d)
        self.assertEqual(d.post_calls,0)
        d=self.Drive(self.prior())
        d.old_tamper=True
        with self.assertRaises(m.CloudGateDenied):
            self.run_stage(d)
        self.assertEqual(d.post_calls,0)

    def test_prior_shared_or_wrong_parent_denied_before_upload(self):
        for key,value in (("shared",True),("ownedByMe",False),
                          ("parents",["BAD_PARENT_12345"]),
                          ("version","bad")):
            d=self.Drive(self.prior())
            d.old_info[key]=value
            with self.subTest(key=key),self.assertRaises(m.CloudGateDenied):
                self.run_stage(d)
            self.assertEqual(d.post_calls,0)

    def test_prior_no_overlap_or_incomplete_page_fail_closed(self):
        prior=self.prior()
        # A one-session historical window is valid but does not overlap
        # the next source window; do not accidentally create duplicate D1.
        for field in ("t","o","h","l","c","v"):
            prior["raw_native"][field]=prior["raw_native"][field][:1]
        d=self.Drive(prior)
        with self.assertRaisesRegex(m.CloudGateDenied,"NO_OVERLAP"):
            self.run_stage(d)
        self.assertEqual(d.post_calls,0)
        prior=self.prior()
        prior["raw_native"]["nextTime"]=1794200000
        d=self.Drive(prior)
        with self.assertRaisesRegex(m.CloudGateDenied,"DELTA_INVALID"):
            self.run_stage(d)
        self.assertEqual(d.post_calls,0)

    def test_verified_d1_noop_keeps_prior_and_does_not_upload_duplicate(self):
        prior=self.prior()
        for only_exits in (False,True):
            with self.subTest(only_exits=only_exits):
                d=self.Drive(prior)
                src=prior["raw_native"]
                new={
                    k:(v[1:] if only_exits else v[:])
                    for k,v in src.items() if k!="nextTime"
                }
                new["nextTime"]=0
                receipt=m.stage_unpublished_dnse_source(
                    d,
                    stage_owner_env(MST_DNSE_PREVIOUS_SOURCE_FILE_ID=self.PRIOR_ID),
                    new,
                )
                self.assertTrue(receipt["source_noop_reused_verified_prior"])
                self.assertFalse(receipt["unpublished_private_source_document_stored"])
                self.assertTrue(receipt["previous_candidate_kept_unmodified"])
                self.assertEqual(receipt["source_delta_added_rows"],0)
                self.assertEqual(receipt["source_delta_revised_rows"],0)
                self.assertEqual(
                    receipt["source_delta_window_exited_not_deleted"],
                    int(only_exits),
                )
                self.assertEqual(receipt["stored_object_count"],0)
                self.assertEqual(d.post_calls,0)
                self.assertEqual(d.old_media_reads,2)
                self.assertEqual(d.media_reads,0)
                self.assertFalse(receipt["signals_and_trading_eligible"])

    def test_prior_id_cannot_be_used_by_readonly_or_non_d1_modes(self):
        d=self.Drive(self.prior())
        for changes in (
            {"MST_MFX_SOURCE_MODE":m.MODE_DNSE},
            {"MST_SOURCE_TF":"M5"},
            {"MST_DNSE_PREVIOUS_SOURCE_FILE_ID":"../evil"},
            {"GITHUB_RUN_ATTEMPT":"2"},
        ):
            env=stage_owner_env(MST_DNSE_PREVIOUS_SOURCE_FILE_ID=self.PRIOR_ID)
            env.update(changes)
            with self.subTest(changes=changes),self.assertRaises(m.CloudGateDenied):
                m.stage_unpublished_dnse_source(d,env,self.new_payload())
            self.assertEqual(d.post_calls,0)


class AutoDnseD1PriorDiscovery(unittest.TestCase):
    """Cloud source-candidate selection, all request/media interactions faked."""

    class Drive(PriorDnseD1IncrementalStage.Drive):
        def __init__(self, archive):
            super().__init__(archive)
            self.old_info["appProperties"].update({
                "source_symbol":"FPT",
                "source_native_tf":"D1",
                "source_run_id":"43269999999",
            })
            self.enumerations=0
            self.override_records=None
            self.overwrite_listing=None

        def item(self):
            return {k:self.old_info[k] for k in
                    ("id","name","mimeType","parents","trashed","appProperties")}

        def get(self,url,*,params,timeout,**kwargs):
            if (url=="https://www.googleapis.com/drive/v3/files"
                    and "name contains 'MST_UNPUBLISHED_DNSE_'" in params.get("q","")):
                self.enumerations+=1
                if self.overwrite_listing is not None:
                    return FakeResponse(self.overwrite_listing)
                return FakeResponse({"files":(
                    self.override_records if self.override_records is not None
                    else [self.item()]
                )})
            return super().get(url,params=params,timeout=timeout,**kwargs)

    def prior(self):
        return PriorDnseD1IncrementalStage().prior()

    def payload(self):
        return PriorDnseD1IncrementalStage().new_payload()

    def run_auto(self, d, **updates):
        env=stage_owner_env(MST_DNSE_PREVIOUS_SOURCE_FILE_ID="auto")
        env.update(updates)
        return m.stage_unpublished_dnse_source(d,env,self.payload())


    def test_blank_d1_input_auto_links_existing_labeled_prior(self):
        d=self.Drive(self.prior())
        env=stage_owner_env()  # empty predecessor now becomes auto by default
        result=m.stage_unpublished_dnse_source(d,env,self.payload())
        self.assertTrue(result["source_delta_linked_to_prior_private_d1"])
        self.assertEqual(result["source_delta_revised_rows"],1)
        self.assertEqual(d.enumerations,1)
        self.assertEqual(d.old_media_reads,2)
        self.assertEqual(d.post_calls,1)

    def test_blank_d1_input_denies_legacy_before_new_upload(self):
        d=self.Drive(self.prior())
        del d.old_info["appProperties"]["source_symbol"]
        with self.assertRaisesRegex(m.CloudGateDenied,"LEGACY_OR_UNLABELED"):
            m.stage_unpublished_dnse_source(d,stage_owner_env(),self.payload())
        self.assertEqual(d.enumerations,1)
        self.assertEqual(d.post_calls,0)

    def test_auto_reads_verified_predecessor_then_stages_delta(self):
        d=self.Drive(self.prior())
        receipt=self.run_auto(d)
        self.assertEqual(d.enumerations,1)
        self.assertEqual(d.old_media_reads,2)
        self.assertEqual(d.media_reads,2)
        self.assertEqual(d.post_calls,1)
        self.assertTrue(receipt["source_delta_linked_to_prior_private_d1"])
        self.assertEqual(receipt["source_delta_added_rows"],1)
        self.assertEqual(receipt["source_delta_revised_rows"],1)
        archive=json.loads(d.media)
        self.assertEqual(archive["prior_source_incremental_delta"][
            "prior_private_file_id"],PriorDnseD1IncrementalStage.PRIOR_ID)
        self.assertEqual(archive["prior_source_incremental_delta"]["delta"][
            "revised"][0]["after"]["volume"],255)
        self.assertEqual(d.file_info["appProperties"]["source_symbol"],"FPT")
        self.assertEqual(d.file_info["appProperties"]["source_native_tf"],"D1")
        self.assertEqual(d.file_info["appProperties"]["source_run_id"],"43270010001")
        self.assertFalse(receipt["signals_and_trading_eligible"])

    def test_empty_complete_census_is_first_capture(self):
        d=self.Drive(self.prior())
        d.override_records=[]
        result=self.run_auto(d)
        self.assertTrue(result["unpublished_private_source_document_stored"])
        self.assertFalse(result["source_delta_linked_to_prior_private_d1"])
        self.assertEqual(d.enumerations,1)
        self.assertEqual(d.old_media_reads,0)
        self.assertEqual(d.post_calls,1)

    def test_other_symbol_not_used_as_predecessor(self):
        d=self.Drive(self.prior())
        d.old_info["appProperties"]["source_symbol"]="DCM"
        result=self.run_auto(d)
        self.assertFalse(result["source_delta_linked_to_prior_private_d1"])
        self.assertEqual(d.old_media_reads,0)
        self.assertEqual(d.post_calls,1)

    def test_legacy_unlabeled_d1_must_not_be_ignored(self):
        d=self.Drive(self.prior())
        del d.old_info["appProperties"]["source_symbol"]
        with self.assertRaisesRegex(m.CloudGateDenied,"LEGACY_OR_UNLABELED"):
            self.run_auto(d)
        self.assertEqual(d.post_calls,0)

    def test_highest_previous_run_chosen_from_unsorted_census(self):
        d=self.Drive(self.prior())
        older=d.item()
        older["id"]="FAKE_OLDER_DNSE_1234567890"
        older["name"]="MST_UNPUBLISHED_DNSE_D1_43268888888_1.json"
        older["appProperties"]=dict(older["appProperties"],
                                    source_run_id="43268888888")
        d.override_records=[older,d.item()]
        result=self.run_auto(d)
        self.assertTrue(result["source_delta_linked_to_prior_private_d1"])
        self.assertEqual(d.old_media_reads,2)
        self.assertEqual(d.post_calls,1)

    def test_tied_latest_run_is_ambiguous(self):
        d=self.Drive(self.prior())
        second=d.item()
        second["id"]="FAKE_NATIVE_DNSE_1234567890"
        second["name"]="MST_UNPUBLISHED_DNSE_NATIVE_D1_43269999999_1.json"
        d.override_records=[d.item(),second]
        with self.assertRaisesRegex(m.CloudGateDenied,"AMBIGUOUS"):
            self.run_auto(d)
        self.assertEqual(d.post_calls,0)

    def test_future_or_current_run_id_denied(self):
        for run in ("43270010001","43270010002"):
            d=self.Drive(self.prior())
            d.old_info["name"]="MST_UNPUBLISHED_DNSE_D1_"+run+"_1.json"
            d.old_info["appProperties"]["source_run_id"]=run
            with self.subTest(run=run),self.assertRaisesRegex(
                    m.CloudGateDenied,"FUTURE_OR_SELF"):
                self.run_auto(d)
            self.assertEqual(d.post_calls,0)

    def test_census_missing_page_or_bad_token_rejected(self):
        for token in ("page2","bad"*300):
            d=self.Drive(self.prior())
            d.overwrite_listing={"files":[d.item()],"nextPageToken":token}
            with self.subTest(token=token[:10]),self.assertRaises(
                    m.CloudGateDenied):
                self.run_auto(d)
            self.assertEqual(d.post_calls,0)
            self.assertLessEqual(d.enumerations,8)

    def test_duplicate_or_unknown_scope_denied(self):
        d=self.Drive(self.prior())
        d.override_records=[d.item(),d.item()]
        with self.assertRaisesRegex(m.CloudGateDenied,"DUPLICATE_CENSUS"):
            self.run_auto(d)
        self.assertEqual(d.post_calls,0)
        d=self.Drive(self.prior())
        bad=d.item()
        bad["name"]="MST_UNPUBLISHED_DNSE_UNEXPECTED_43269999999_1.json"
        d.override_records=[bad]
        with self.assertRaisesRegex(m.CloudGateDenied,"UNKNOWN_SOURCE_FILENAME"):
            self.run_auto(d)
        self.assertEqual(d.post_calls,0)

    def test_auto_guard_wrong_tf_or_owner_denied_before_census(self):
        for change in (
            {"MST_SOURCE_TF":"M5"},
            {"MST_MFX_SOURCE_MODE":m.MODE_DNSE_NATIVE},
            {"GITHUB_RUN_ATTEMPT":"2"},
            {"MST_DNSE_SOURCE_RIGHTS_CONFIRMED":"false"},
            {"GITHUB_REF":"refs/heads/dev"},
        ):
            d=self.Drive(self.prior())
            with self.subTest(change=change),self.assertRaises(m.CloudGateDenied):
                self.run_auto(d,**change)
            self.assertEqual(d.enumerations,0)
            self.assertEqual(d.post_calls,0)

class NativeQuarantineStage(unittest.TestCase):
    def native_env(self, tf="M5", **updates):
        env=stage_owner_env(
            MST_MFX_SOURCE_MODE=m.MODE_STAGE_NATIVE,
            MST_SOURCE_TF=tf,
            MST_DNSE_FROM_UNIX="1794000000",
            MST_DNSE_TO_UNIX="1794172800",
        )
        env.update(updates)
        return env

    def native_payload(self, second=300):
        return {"t":[1794000000,1794000000+second],
                "o":[100,101],"h":[102,103],"l":[99,100],
                "c":[101,102],"v":[200,250],"nextTime":0}

    def test_each_native_tf_has_own_quarantined_name_and_source_resolution(self):
        expected={"M5":("5",300),"M15":("15",900),"M30":("30",1800),
                  "H1":("1H",3600),"D1":("1D",86400)}
        for tf,(resolution,period) in expected.items():
            with self.subTest(tf=tf):
                d=FakeQuarantineDrive()
                env=self.native_env(tf)
                receipt=m.stage_unpublished_dnse_source(
                    d,env,self.native_payload(second=period))
                self.assertTrue(receipt["unpublished_private_source_document_stored"])
                self.assertEqual(receipt["source_native_tf"],tf)
                self.assertEqual(receipt["source_rows_observed"],2)
                self.assertFalse(receipt["signals_and_trading_eligible"])
                self.assertFalse(receipt["independent_atomic_cas_ready"])
                body=json.loads(d.media)
                self.assertEqual(body["source_native_tf"],tf)
                self.assertEqual(body["resolution"],resolution)
                self.assertEqual(
                    body["schema"],"mst.cloud.dnse_native_unpublished_candidate.v0.1")
                self.assertFalse(body["eligible_for_signals"])
                self.assertFalse(body["official_venue_closed_verified"])
                self.assertEqual(
                    d.file_info["name"],"MST_UNPUBLISHED_DNSE_NATIVE_"
                    +tf+"_43270010001_1.json")
                self.assertEqual(d.media_reads,2)
                self.assertEqual(d.name_lookup_count,3)  # full TF census + name before/after
                self.assertEqual(d.post_calls,1)
                with self.assertRaisesRegex(
                        m.CloudGateDenied,"PREEXISTING_ATTEMPT|AUTO_D1_FUTURE_OR_SELF_SOURCE|INTRA_SELF_OR_FUTURE_RUN"):
                    m.stage_unpublished_dnse_source(
                        d,env,self.native_payload(second=period))
                self.assertEqual(d.post_calls,1)

    def test_native_stage_denies_missing_rights_or_storage_or_approval(self):
        for gate in ("MST_DNSE_SOURCE_RIGHTS_CONFIRMED",
                     "MST_DNSE_STORAGE_RIGHTS_CONFIRMED",
                     "MST_MFX_SOURCE_QUARANTINE_WRITE_ACCEPTED"):
            d=FakeQuarantineDrive()
            with self.subTest(gate=gate),self.assertRaises(m.CloudGateDenied):
                m.stage_unpublished_dnse_source(
                    d,self.native_env(**{gate:"false"}),self.native_payload())
            self.assertEqual(d.post_calls,0)

    def test_native_stage_rejects_h4_long_window_and_rerun(self):
        invalid=[
            self.native_env("H4"),
            self.native_env("M5",MST_DNSE_TO_UNIX=str(1794000000+6*86400)),
            self.native_env("M5",GITHUB_RUN_ATTEMPT="2"),
            self.native_env("M5",GITHUB_REF="refs/heads/feature"),
        ]
        for env in invalid:
            d=FakeQuarantineDrive()
            with self.subTest(env=env.get("MST_SOURCE_TF")),self.assertRaises(
                    m.CloudGateDenied):
                m.stage_unpublished_dnse_source(d,env,self.native_payload())
            self.assertEqual(d.post_calls,0)

    def test_m5_source_bounds_and_readback_mismatch_fail_closed(self):
        d=FakeQuarantineDrive()
        d.mutate_media=True
        with self.assertRaisesRegex(
                m.CloudGateDenied,"MEDIA_READBACK_MISMATCH"):
            m.stage_unpublished_dnse_source(
                d,self.native_env(),self.native_payload())
        self.assertEqual(d.post_calls,1)
        d=FakeQuarantineDrive()
        with self.assertRaisesRegex(
                m.CloudGateDenied,"NATIVE_TIMESTAMP_MISMATCH"):
            m.stage_unpublished_dnse_source(
                d,self.native_env(
                    MST_DNSE_TO_UNIX="1794005000"),self.native_payload(second=9000))
        self.assertEqual(d.post_calls,0)

class DnseNativeTimeframeTests(unittest.TestCase):
    def test_native_intraday_count_is_never_labeled_daily(self):
        payload = DnseNative().payload()
        for tf in ("M5", "M15", "M30", "H1"):
            with self.subTest(tf=tf):
                summary = m.validate_dnse_native(
                    payload, 1794000000, 1794500000, timeframe=tf
                )
                self.assertEqual(summary["observed_native_rows"], 2)
                self.assertNotIn("observed_native_d1_rows", summary)
                self.assertFalse(summary["trade_signal_eligible"])
        daily = m.validate_dnse_native(
            payload, 1794000000, 1794500000, timeframe="D1"
        )
        self.assertEqual(daily["observed_native_d1_rows"], 2)
        self.assertEqual(daily["observed_native_rows"], 2)
        with self.assertRaisesRegex(m.CloudGateDenied, "NATIVE_TF_UNSUPPORTED"):
            m.validate_dnse_native(payload, 1794000000, 1794500000, timeframe="H4")

    def test_native_mapping_all_supported_and_unproven_h4_denied(self):
        from scripts.mst_mfx_native_timeframes import provider_resolution, NativeTfDenied
        expected={"M5":"5","M15":"15","M30":"30","H1":"1H","D1":"1D"}
        for tf,resolution in expected.items():
            self.assertEqual(provider_resolution("DNSE",tf),resolution)
        with self.assertRaisesRegex(NativeTfDenied,"NATIVE_H4"):
            provider_resolution("DNSE","H4")

    def test_request_signs_vendor_path_for_every_native_timeframe(self):
        outputs=[]
        for tf in ("M5","M15","M30","H1","D1"):
            url,headers=m.build_dnse_request(
                "FPT",1794000000,1794200000,"FAKE_KEY","FAKE_SECRET",
                date_header="Fri, 13 Nov 2026 00:00:00 +0000",
                nonce="a"*32,timeframe=tf)
            outputs.append(headers["X-Signature"])
            self.assertIn("resolution=",url)
        self.assertEqual(len(set(outputs)),1)
        with self.assertRaises(m.CloudGateDenied):
            m.build_dnse_request(
                "FPT",1794000000,1794500000,"FAKE_KEY","FAKE_SECRET",
                date_header="Fri, 13 Nov 2026 00:00:00 +0000",
                nonce="a"*32,timeframe="H4")

    def test_original_d1_mode_cannot_request_m5_under_owner_gate(self):
        env=owner_env(
            MST_MFX_SOURCE_MODE=m.MODE_DNSE,
            MST_SOURCE_TF="M5",
            MST_DNSE_READONLY_OWNER_ACCEPTED="true",
            MST_DNSE_SOURCE_RIGHTS_CONFIRMED="true",
            MST_DNSE_API_KEY="FAKE_KEY",MST_DNSE_API_SECRET="FAKE_SECRET",
            MST_DNSE_SYMBOL="FPT",
            MST_DNSE_FROM_UNIX="1794000000",MST_DNSE_TO_UNIX="1794500000",
        )
        with self.assertRaisesRegex(m.CloudGateDenied,"D1_MODE_CANNOT_PROMOTE"):
            m.guard(env)
        env["MST_MFX_SOURCE_MODE"]=m.MODE_DNSE_NATIVE
        # A native M5 test window is deliberately shorter than D1's 95 days.
        env["MST_DNSE_TO_UNIX"]="1794200000"
        self.assertEqual(m.guard(env)[0],m.MODE_DNSE_NATIVE)
        env["MST_SOURCE_TF"]="H4"
        with self.assertRaises(m.CloudGateDenied):
            m.guard(env)

    def test_quarantine_staging_cannot_use_intra_tf_behind_d1_contract(self):
        with self.assertRaisesRegex(m.CloudGateDenied,"D1_MODE_CANNOT_PROMOTE"):
            m.guard(stage_owner_env(MST_SOURCE_TF="M5"))




class DnseSourceTransportRightsAndWireSafety(unittest.TestCase):
    """End-to-end source helper exercised only against fabricated HTTP."""

    class Session:
        def __init__(self, payload, status=200, raw_override=None):
            self.payload=payload
            self.status=status
            self.raw_override=raw_override
            self.calls=[]
        def get(self,url,*,headers,timeout,allow_redirects):
            self.calls.append((url,headers,timeout,allow_redirects))
            r=FakeResponse(self.payload,self.status)
            if self.raw_override is not None:
                r.content=self.raw_override
            return r

    @staticmethod
    def valid_env(**updates):
        env=stage_owner_env(
            MST_MFX_SOURCE_MODE=m.MODE_DNSE_NATIVE,
            MST_SOURCE_TF="M5",
            MST_DNSE_FROM_UNIX="1794000000",
            MST_DNSE_TO_UNIX="1794005000",
        )
        env.update(updates)
        return env

    @staticmethod
    def valid_payload():
        return {"t":[1794000000,1794000300],
                "o":[100.0,101.0],"h":[102.0,103.0],
                "l":[99.0,100.0],"c":[101.0,102.0],
                "v":[200,250],"nextTime":0}

    def test_direct_helper_rejects_unentitled_or_nonmain_before_http(self):
        invalid=[
            {"MST_DNSE_SOURCE_RIGHTS_CONFIRMED":"false"},
            {"MST_DNSE_READONLY_OWNER_ACCEPTED":"false"},
            {"MST_MFX_APP_OWNED_READONLY_ACCEPTED":"false"},
            {"GITHUB_REF":"refs/heads/feature"},
            {"GITHUB_EVENT_NAME":"schedule"},
            {"MST_MFX_SOURCE_MODE":m.MODE_DRIVE},
        ]
        for changes in invalid:
            session=self.Session(self.valid_payload())
            with self.subTest(changes=changes), self.assertRaises(
                    m.CloudGateDenied):
                m._fetch_dnse_once(session,self.valid_env(**changes))
            self.assertFalse(session.calls)

    def test_direct_helper_enforces_native_source_and_no_raw_in_receipt(self):
        session=self.Session(self.valid_payload())
        summary, payload=m._fetch_dnse_once(session,self.valid_env())
        self.assertEqual(summary["source_native_tf"],"M5")
        self.assertEqual(summary["provider_resolution"],"5")
        self.assertEqual(summary["observed_native_rows"],2)
        self.assertNotIn("observed_native_d1_rows",summary)
        self.assertFalse(summary["trade_signal_eligible"])
        self.assertFalse(summary["market_data_written_to_drive"])
        self.assertEqual(payload,self.valid_payload())
        self.assertEqual(len(session.calls),1)
        url,headers,timeout,redirects=session.calls[0]
        self.assertIn("resolution=5",url)
        self.assertIn("symbol=FPT",url)
        self.assertEqual((timeout,redirects),(25,False))
        self.assertNotIn("FAKE_MARKETDATA_SECRET",url+str(summary))
        session2=self.Session(self.valid_payload())
        observed=m.read_dnse_once(session2,self.valid_env())
        self.assertEqual(observed["observed_native_rows"],2)
        self.assertNotIn("raw_native",observed)

    def test_no_http_for_unicode_giant_or_millisecond_epoch(self):
        for value in ("١٧٩٤٠٠٠٠٠٠","1794000000000","9"*5000,
                      "0001794000000","not-an-epoch"):
            session=self.Session(self.valid_payload())
            with self.subTest(value=value[:20]),self.assertRaisesRegex(
                    m.CloudGateDenied,"BOUNDED_EPOCH_WINDOW_REQUIRED"):
                m._fetch_dnse_once(
                    session,self.valid_env(MST_DNSE_FROM_UNIX=value))
            self.assertFalse(session.calls)

    def test_request_builder_rejects_wrong_epoch_type_and_header_injection(self):
        cases=[
            {"from_unix":1794000000000},
            {"from_unix":True},
            {"to_unix":253402300800},
            {"date_header":"Fri, 13 Nov 2026\\r\\nX-Bad: trick"},
            {"date_header":"Fri, 13 Nov 2026\r\nX-Bad: trick"},
            {"nonce":None},
        ]
        for changes in cases:
            kwargs={"symbol":"FPT","from_unix":1794000000,
                    "to_unix":1794005000,"api_key":"FAKE_KEY",
                    "api_secret":"FAKE_SECRET",
                    "date_header":"Fri, 13 Nov 2026 00:00:00 +0000",
                    "nonce":"a"*32,"timeframe":"M5"}
            kwargs.update(changes)
            with self.subTest(changes=changes),self.assertRaises(
                    m.CloudGateDenied):
                m.build_dnse_request(**kwargs)

    def test_vendor_http_status_and_response_body_fail_closed(self):
        for status,raw in ((429,None),(302,None),(200,b""),
                           (200,b"x"*1_500_001),(200,"not-bytes")):
            session=self.Session(self.valid_payload(),status,raw)
            with self.subTest(status=status,length=len(raw) if raw is not None else 0),self.assertRaises(
                    m.CloudGateDenied):
                m._fetch_dnse_once(session,self.valid_env())
            self.assertEqual(len(session.calls),1)

    def test_vendor_declared_nexttime_unread_pages_never_pass(self):
        payload=self.valid_payload()
        payload["nextTime"]=1794000300
        session=self.Session(payload)
        with self.assertRaisesRegex(
                m.CloudGateDenied,"INCOMPLETE_PAGE_NO_ACCEPTANCE"):
            m._fetch_dnse_once(session,self.valid_env())
        self.assertEqual(len(session.calls),1)

    def test_very_large_price_and_volume_fail_closed_not_overflow(self):
        for field,value,expected in (
            ("o",10**500,"NATIVE_PRICE_INVALID"),
            ("h",float("inf"),"NATIVE_PRICE_INVALID"),
            ("v",2**63,"NATIVE_OHLCV_INVALID"),
        ):
            payload=self.valid_payload()
            payload[field][0]=value
            with self.subTest(field=field),self.assertRaisesRegex(
                    m.CloudGateDenied,expected):
                m.validate_dnse_native(
                    payload,1794000000,1794005000,timeframe="M5")

class DnseRealApiProbeWindowTests(unittest.TestCase):
    def test_tf_span_guards_prevent_truncated_native_ohlcv_probe(self):
        from scripts.mst_mfx_native_timeframes import MAX_SINGLE_PROBE_CALENDAR_DAYS
        for tf, days in MAX_SINGLE_PROBE_CALENDAR_DAYS.items():
            with self.subTest(timeframe=tf), self.assertRaisesRegex(
                    m.CloudGateDenied,"BOUNDED_EPOCH_WINDOW_REQUIRED"):
                m.build_dnse_request(
                    "FPT",1794000000,1794000000+(days+1)*86400,
                    "FAKE_KEY","FAKE_SECRET",
                    date_header="Fri, 13 Nov 2026 00:00:00 +0000",
                    nonce="a"*32,timeframe=tf)
        self.assertEqual(MAX_SINGLE_PROBE_CALENDAR_DAYS["D1"],95)
        self.assertLess(MAX_SINGLE_PROBE_CALENDAR_DAYS["M5"],95)

    def test_owner_guard_denies_long_m5_window_before_token_or_drive(self):
        env=owner_env(
            MST_MFX_SOURCE_MODE=m.MODE_DNSE_NATIVE,
            MST_SOURCE_TF="M5",
            MST_DNSE_READONLY_OWNER_ACCEPTED="true",
            MST_DNSE_SOURCE_RIGHTS_CONFIRMED="true",
            MST_DNSE_API_KEY="FAKE_KEY",MST_DNSE_API_SECRET="FAKE_SECRET",
            MST_DNSE_SYMBOL="FPT",
            MST_DNSE_FROM_UNIX="1794000000",
            MST_DNSE_TO_UNIX=str(1794000000+6*86400),
        )
        with self.assertRaisesRegex(m.CloudGateDenied,"BOUNDED_EPOCH_WINDOW_REQUIRED"):
            m.guard(env)
        env["MST_DNSE_TO_UNIX"]=str(1794000000+2*86400)
        self.assertEqual(m.guard(env)[0],m.MODE_DNSE_NATIVE)


if __name__=="__main__":
    unittest.main()
