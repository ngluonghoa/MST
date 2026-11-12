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


if __name__=="__main__":
    unittest.main()
