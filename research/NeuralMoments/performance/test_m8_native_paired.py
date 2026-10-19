"""M8 native-gate contract checks: source/ABI untouched and refusal without native."""
from fractions import Fraction
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from m5_native_call_instrumentation import InclusiveExclusiveLedger
from m8_exact_construction_trial import reference_fraction as exact_fraction
from m8_native_paired_gate import clone_paired_classes,native_pair

ARCHIVE=Path(os.environ.get('W1_M8_H8E_ARCHIVE','/mnt/data/h8e-25point-39121571756.zip'))
H8C=Path(os.environ.get('W1_M8_H8C_ARCHIVE','/mnt/data/h8c-reference-39118951636.zip'))

class MimicOriginalEvaluator:
    def __init__(self):
        self.request=SimpleNamespace(target_axes=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],target_origin=[0.,0.,-.115])
        self.normalization_origin=[0.,0.,0.];self.length=1.
    def __call__(self,tokens):
        coords=tuple(tuple(exact_fraction(x) for x in line) for line in tokens)
        return self._target_view(coords)
    def _target_view(self,points):
        import numpy as np
        orig=[Fraction(float(v)) for v in self.normalization_origin]
        tgt=[Fraction(float(v)) for v in self.request.target_origin]
        axes=[[Fraction(float(v)) for v in row] for row in self.request.target_axes]
        length=Fraction(self.length)
        rows=[]
        for x in points:
            m=[(x[i]-orig[i])/length-tgt[i] for i in range(3)]
            rows.append(tuple(sum(m[i]*axes[i][j] for i in range(3)) for j in range(3)))
        return np.asarray([[float(x) for x in row] for row in rows]),tuple(rows)

class TestNativeGate(unittest.TestCase):
    def test_two_clones_return_exact_same_coordinates(self):
        g0=InclusiveExclusiveLedger();g1=InclusiveExclusiveLedger()
        Original,Candidate,labels,parse=clone_paired_classes(MimicOriginalEvaluator,g0,g1)
        values=[['0b100/0b11','0b100/0b11','0/1'] for _ in range(5)]
        a=Original()(values);b=Candidate()(values)
        self.assertEqual(a[1],b[1])
        self.assertEqual(a[0].tobytes(),b[0].tobytes())
        self.assertGreater(parse.cache_info().hits,5)
        self.assertEqual(g0.summary()['all_returned'],True)
        self.assertEqual(g1.summary()['all_returned'],True)
        self.assertTrue(labels)
    def test_original_function_global_untouched(self):
        before=MimicOriginalEvaluator.__call__.__globals__['exact_fraction']
        clone_paired_classes(MimicOriginalEvaluator,InclusiveExclusiveLedger(),InclusiveExclusiveLedger())
        self.assertIs(MimicOriginalEvaluator.__call__.__globals__['exact_fraction'],before)
    def test_bad_parser_always_rejected(self):
        Original,Candidate,_,_=clone_paired_classes(MimicOriginalEvaluator,InclusiveExclusiveLedger(),InclusiveExclusiveLedger())
        for engine in (Original(),Candidate()):
            with self.assertRaises((ValueError,ZeroDivisionError)):
                engine([['1/0','1/1','1/1']])
    def test_native_guard_fail_closed_before_fake_success(self):
        self.assertTrue(H8C.is_file())
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaisesRegex(ValueError,'M5_PRODUCTION_SOURCE_UNPINNED'):
                native_pair(H8C,p,p/'output')
            rec=json.loads((p/'output/failure.json').read_text())
            self.assertEqual(rec['status'],'FAILED_NO_NATIVE_MATH_ADMISSION')
            self.assertFalse((p/'output/baseline-performance.json').exists())
            self.assertIsNone(rec['full_solver_speedup'])

if __name__=='__main__':unittest.main()
