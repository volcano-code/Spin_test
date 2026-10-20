"""W2 M14 independent, fail-closed algebraic handoff; no native/derivative certification."""
from fractions import Fraction
from functools import reduce
from math import gcd
from pathlib import Path
import argparse,hashlib,json,re

M13_SHA="2de535d1243802eba1826870001e7d7dc8c34ba8f6d911e933bc201da14ee8fc"
SOURCE="0bcc187b3005478baa586a6d6f450e73811ca342"
W0_SCHEMA_GIT_BLOB="52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc"
W0_LEGACY_GATE_GIT_BLOB="b42ec6d9b389675123250d79f9cc9efb1b658c07"
W3_STAGE11_GIT_BLOB="342b5e6968ba029c2af389de8de4a394543f422e"

def require(ok,reason):
    if not ok:raise ValueError(reason)

def strict_json(raw):
    def pairs(rows):
        d={}
        for k,v in rows:
            require(k not in d,"DUPLICATE_JSON_KEY");d[k]=v
        return d
    def invalid(token):raise ValueError("NONFINITE_JSON_NUMBER:"+token)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def git_blob(raw):return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def rational(s):
    require(type(s) is str and re.fullmatch(r"-?\d+/(?:[1-9]\d*)",s),"INVALID_RATIONAL_TOKEN")
    return Fraction(s)

def inspect(m13_path,*,w0_schema=None,w0_gate=None,w3_report=None):
    raw=Path(m13_path).read_bytes()
    require(sha(raw)==M13_SHA,"UNPINNED_M13_FULL_REPORT")
    d=strict_json(raw)
    require(d["historical_workflow_conclusion"]=="failure" and d["new_native_calls"]==0
        and d["training_admitted_count"]==0 and d["w0_projective_protocol_officially_adopted"] is False
        and d["independent_native_continuity_proved"] is False,"FORGED_SCIENTIFIC_RELEASE")
    records=d["records"];require(len(records)==81,"WRONG_81_COUNT")
    rays=set();unit=0
    for i,r in enumerate(records):
        require(r["index"]==i and r["training_admitted"] is False and r["derivative_J_D"] is None
            and r["certified_continuous_neighborhood"] is False
            and r["native_boolean_material_proof_from_this_certificate"] is False,
            "UNAUTHORIZED_DERIVATIVE_OR_SAMPLE")
        c=[rational(v) for v in r["exact_native_c_tokens"]]
        q=[rational(v) for v in r["exact_monomial_q_tokens"]]
        require(len(c)==len(q)==10 and q==[v*(2 if j>=7 else 1) for j,v in enumerate(c)],
            "NATIVE_TO_MONOMIAL_MAPPING_DRIFT")
        n=[int(v) for v in r["positive_primitive_ray_identity"]["primitive_signed_integer_c"]]
        a=rational(r["exact_positive_scale"])
        require(len(n)==10 and a>0 and reduce(gcd,map(abs,n))==1
            and c==[a*v for v in n],"PROJECTIVE_IDENTITY_INVALID")
        key=tuple(n);require(key not in rays,"DUPLICATE_POSITIVE_RAY");rays.add(key)
        require(r["exact_raw_c_equals_positive_scale_times_integer_ray"] is True
            and all(x["exact_factor_relation"] is True and x["sign_consistent"] is True
                for x in r["exact_positive_scale_probes"]),"M13_EXACT_PROBE_FAILED")
        unit+=int(r["raw_archived_c_unit_compatible"] is True)
        if i==60:
            require(r["raw_archived_c_unit_compatible"] is False and
                "FEATURE_CHANGE" in r["original_constructive_status"],"POINT60_WRONGLY_CERTIFIED")
    require(len(rays)==81 and unit==17,"M13_17_64_COUNTS_DRIFT")
    checks={}
    for name,path,pin in (("w0_schema",w0_schema,W0_SCHEMA_GIT_BLOB),
             ("w0_legacy_gate",w0_gate,W0_LEGACY_GATE_GIT_BLOB),
             ("w3_stage11",w3_report,W3_STAGE11_GIT_BLOB)):
        if path is None:checks[name]={"observed":False};continue
        data=Path(path).read_bytes();require(git_blob(data)==pin,name+"_BLOB_DRIFT")
        if name=="w3_stage11":
            v=strict_json(data)
            require(v["new_cherchi_native_calls"]==0 and v["new_real_native_side_count"]==0
                    and v["newton_admitted"] is False,"W3_STATUS_UPGRADED")
        checks[name]={"observed":True,"git_blob_sha1":pin}
    return {"schema":"w2-m14-algebraic-handoff-v1",
       "status":"PINNED_EXACT_RAY_ONLY_NO_RELEASE","original_report_sha256":M13_SHA,
       "frozen_source_commit":SOURCE,"original_workflow_conclusion":"failure",
       "checked_raw_coefficient_vectors":81,"distinct_positive_integer_rays":81,
       "unit_compatible_raw_vectors":17,"nonunit_raw_vectors":64,
       "point60_feature_change_preserved":True,"external_evidence":checks,
       "w0_projective_protocol_approved":False,"w3_native_continuity_proved":False,
       "new_native_calls":0,"J_D":None,"training_admitted":0}

def main():
    p=argparse.ArgumentParser();p.add_argument("--m13",required=True);p.add_argument("--output",required=True)
    p.add_argument("--w0-schema");p.add_argument("--w0-gate");p.add_argument("--w3-report")
    a=p.parse_args()
    result=inspect(a.m13,w0_schema=a.w0_schema,w0_gate=a.w0_gate,w3_report=a.w3_report)
    with Path(a.output).open("x",encoding="utf-8") as f:json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
    print(json.dumps({"checked":81,"unit":17,"nonunit":64,"training_admitted":0}))
if __name__=="__main__":main()
