import unittest
from m29_native_campaign_gate import aggregate, H8C_SHA, H8E_SHA, NATIVE

def good():
    m13={"state":"READY_TO_BUILD","blockers":[]}
    m19={"state":"READY_FOR_REAL_H8E_PROFILING","blockers":[],
         "archive_sha256":H8C_SHA,
         "checks":{"native_modules":{"modules":{n:{"sha256":"sha-"+n} for n in NATIVE}}}}
    m23={"status":"READY_TO_RUN_FOUR_INDEPENDENT_SOLVER_PROCESSES","blockers":[],
         "archive_sha256":H8E_SHA,"module_sha256":{n:"sha-"+n for n in NATIVE}}
    return m13,m19,m23

class M29GateTests(unittest.TestCase):
    def test_all_gates_pass(self):
        r=aggregate(*good())
        self.assertEqual(r["state"],"READY_FOR_M29_NATIVE_NUMERICAL_CAMPAIGN")
        self.assertEqual(r["blockers"],[])
        self.assertEqual(r["production_native_calls"],0)
        self.assertFalse(r["production_admitted"])
    def test_m13_blocker_propagates(self):
        a,b,c=good();a["state"]="BLOCKED";a["blockers"]=["memory"]
        r=aggregate(a,b,c)
        self.assertEqual(r["state"],"BLOCKED")
        self.assertTrue(any(x.startswith("m13_pinned") for x in r["blockers"]))
    def test_m19_blocker_propagates(self):
        a,b,c=good();b["state"]="BLOCKED";b["blockers"]=["native module"]
        r=aggregate(a,b,c)
        self.assertTrue(any(x.startswith("m19_real") for x in r["blockers"]))
    def test_m23_blocker_propagates(self):
        a,b,c=good();c["status"]="BLOCKED";c["blockers"]=["no source"]
        r=aggregate(a,b,c)
        self.assertTrue(any(x.startswith("m23_full") for x in r["blockers"]))
    def test_h8c_hash_mismatch_fails(self):
        a,b,c=good();b["archive_sha256"]="0"*64
        r=aggregate(a,b,c)
        self.assertTrue(any(x.startswith("h8c_archive") for x in r["blockers"]))
    def test_h8e_hash_mismatch_fails(self):
        a,b,c=good();c["archive_sha256"]="0"*64
        r=aggregate(a,b,c)
        self.assertTrue(any(x.startswith("h8e_archive") for x in r["blockers"]))
    def test_missing_module_fails(self):
        a,b,c=good();del b["checks"]["native_modules"]["modules"][NATIVE[0]]
        r=aggregate(a,b,c)
        self.assertTrue(any(x.startswith("three_native_modules") for x in r["blockers"]))
    def test_module_sha_drift_fails(self):
        a,b,c=good();c["module_sha256"][NATIVE[1]]="different"
        r=aggregate(a,b,c)
        self.assertTrue(any(x.startswith("native_module_hashes") for x in r["blockers"]))
    def test_success_never_means_production_admission(self):
        r=aggregate(*good())
        self.assertFalse(r["production_admitted"])
        self.assertFalse(r["jacobian_certified"])
        self.assertIsNone(r["full_solver_speedup"])

if __name__=="__main__":unittest.main()
