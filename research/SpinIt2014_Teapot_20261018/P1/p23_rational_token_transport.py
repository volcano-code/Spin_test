#!/usr/bin/env python3
"""P23 W4-owned exact Cherchi-rational to W0 mesh-boundary diagnostic."""
from __future__ import annotations
import argparse, ast, importlib.util, json, subprocess, sys, unittest
from fractions import Fraction
from pathlib import Path
BASE_W0="51cbfd33d08063404d7e0c40e4256dd0e38efa1a"
BASE_CORE="58fd12c1306c1c01679a19172e276eef0b30542"
CTX=None
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError("MODULE_SPEC_UNAVAILABLE:"+str(path))
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
def head(root):
    return subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],check=True,capture_output=True,text=True,timeout=30).stdout.strip()
def fname(node):
    return node.id if isinstance(node,ast.Name) else node.attr if isinstance(node,ast.Attribute) else None
def wrapped(path):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="from_rationals" and isinstance(n.func.value,ast.Name) and n.func.value.id=="MeshSnapshot" and n.args:
            a=n.args[0]
            if isinstance(a,ast.Call) and fname(a.func)=="canonical_mesh_rational_rows": return True
    return False
def adapter(rows,replay,rt):
    if not isinstance(rows,(list,tuple)) or not rows: raise ValueError("EXACT_MESH_VERTICES_REQUIRED")
    out=[]
    for row in rows:
        if not isinstance(row,(list,tuple)) or len(row)!=3: raise ValueError("EXACT_MESH_VERTEX_TRIPLE_REQUIRED")
        out.append(tuple(rt.fraction_to_rational_text(replay.frac(x)) for x in row))
    return tuple(out)
def configure(a):
    w0,core=a.w0_root.resolve(),a.core_root.resolve();wh,ch=head(w0),head(core)
    if a.require_fixed:
        if wh!=a.expected_w0_commit: raise SystemExit("W0_COMMIT_MISMATCH:"+wh)
    elif wh!=BASE_W0 or a.expected_w0_commit!=BASE_W0: raise SystemExit("BASELINE_W0_IDENTITY_MISMATCH:"+wh)
    if ch!=BASE_CORE: raise SystemExit("CORE_COMMIT_MISMATCH:"+ch)
    cp=core/"python";sys.path.insert(0,str(cp));contracts=w0/"research/NeuralMoments/contracts"
    replay=load(contracts/"native_teacher_replay.py","_p23_w0_replay")
    rt=load(cp/"make_it_stand/verification/rational_text.py","_p23_rational_text")
    from make_it_stand.verification.spin_problem import _canonical_rational_vertices
    return dict(w0=wh,core=ch,replay=replay,rt=rt,mesh=_canonical_rational_vertices,
                helper=getattr(replay,"canonical_mesh_rational_rows",None),
                replay_path=contracts/"native_teacher_replay.py",
                partition_path=contracts/"full_partition_m6.py",fixed=a.require_fixed)
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=CTX;cls.r=CTX["replay"];cls.rt=CTX["rt"]
        cls.mesh=CTX["mesh"];cls.helper=CTX["helper"]
    def convert(self,rows):
        if self.c["fixed"]:
            self.assertTrue(callable(self.helper),"W0 canonical helper missing")
            return self.helper(rows)
        return adapter(rows,self.r,self.rt)
    def test_replay_parser_accepts_binary_tokens(self):
        self.assertEqual(self.r.frac("0b101101/0b1101"),Fraction(45,13))
        self.assertEqual(self.r.frac("-0b101/0b11"),Fraction(-5,3))
        self.assertEqual(self.r.frac("0/1"),Fraction(0))
        self.assertEqual(self.r.frac("0b0/0b1"),Fraction(0))
    def test_mesh_boundary_rejects_raw_binary_and_accepts_canonical(self):
        raw=[["0b101101/0b1101","-0b101/0b11","0/1"]]
        with self.assertRaises(ValueError): self.mesh(raw)
        canonical=self.convert(raw)
        self.assertEqual(canonical,(("45/13","-5/3","0/1"),))
        self.assertEqual(self.mesh(canonical),canonical)
    def test_large_binary_rational_roundtrip_is_exact_without_float(self):
        n=(1<<20000)+123456789;d=(1<<19999)+987654321
        canonical=self.convert([[f"0b{n:b}/0b{d:b}","0b1/0b11","0/1"]])
        parsed=self.rt.fraction_from_rational_text(canonical[0][0]);exact=Fraction(n,d)
        self.assertEqual(parsed,exact)
        self.assertNotEqual(Fraction.from_float(float(parsed)),parsed)
        self.assertEqual(self.mesh(canonical),canonical)
    def test_malformed_tokens_and_shapes_rejected(self):
        for token in ("0b2/0b1","0b1/-0b1","1/0"):
            with self.subTest(token=token),self.assertRaises(ValueError): self.r.frac(token)
        for rows in ([],[["0/1","0/1"]],[["0b1/0b1","0/1","0/1","0/1"]]):
            with self.subTest(rows=rows),self.assertRaises(ValueError): self.convert(rows)
    def test_both_retained_call_sites_use_shared_helper_after_fix(self):
        a,b=wrapped(self.c["replay_path"]),wrapped(self.c["partition_path"])
        if self.c["fixed"]:
            self.assertTrue(callable(self.helper));self.assertTrue(a);self.assertTrue(b)
            sample=[["0b101101/0b1101","-0b101/0b11","0/1"]]
            self.assertEqual(self.helper(sample),(("45/13","-5/3","0/1"),))
            self.assertEqual(self.mesh(self.helper(sample)),self.helper(sample))
        else:
            self.assertIsNone(self.helper);self.assertFalse(a);self.assertFalse(b)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--w0-root",type=Path,required=True);p.add_argument("--core-root",type=Path,required=True)
    p.add_argument("--expected-w0-commit",required=True);p.add_argument("--require-fixed",action="store_true")
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    global CTX;CTX=configure(a)
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    ok=result.wasSuccessful() and not result.skipped and not result.expectedFailures
    status=("P23_W0_RATIONAL_BOUNDARY_FIX_VERIFIED" if ok else "P23_W0_FIX_TEST_FAILED") if a.require_fixed else ("P23_KNOWN_W0_FORMAT_MISMATCH_REPRODUCED_PENDING_FIX" if ok else "P23_BASELINE_REPRODUCTION_FAILED")
    report=dict(schema="W4_P23_RATIONAL_TOKEN_TRANSPORT_V1",status=status,w0_commit=CTX["w0"],core_commit=CTX["core"],
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=ok,
        require_fixed=a.require_fixed,formal_M6_executed=False,cherchi_native_calls=0,
        float_round_trip_used_for_exact_token_conversion=False,native_set_equality_proved=False,
        scope="W4_OWNED_EXACT_TOKEN_BOUNDARY_DIAGNOSTIC_ONLY")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True));return 0 if ok else 1
if __name__=="__main__": raise SystemExit(main())
