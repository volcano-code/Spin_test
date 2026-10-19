"""Guard tests for forbidden fallback and honest native Cherchi identity."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from w4_cherchi_union import check_result,import_native,union_three,BACKEND


class CherchiIdentityGates(unittest.TestCase):
    def test_missing_native_never_calls_cgal(self):
        with self.assertRaisesRegex(RuntimeError,'CHERCHI_NATIVE_MODULE_NOT_INSTALLED'):
            import_native(Path('/definitely-absent/_cherchi_core_boolean.so'))

    def test_noncherchi_backend_fails_even_if_mesh_geometry_good(self):
        with self.assertRaisesRegex(ValueError,'NON_CHERCHI_BACKEND_REJECTED'):
            check_result(dict(backend='openscad-cgal-nef'), 'a'*64)

    def test_false_provenance_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'CHERCHI_EXACT_PROVENANCE_MISSING'):
            check_result(dict(backend=BACKEND,vertices=[[0,0,0]]*4,faces=[[0,1,2]]*4),'a'*64)

    def test_native_cannot_report_made_up_exact_proof(self):
        fake=dict(backend=BACKEND,vertices=[[0,0,0]]*4,faces=[[0,1,2]]*4,
                  exact_vertices=[['0/1']*3]*4,construction_records=[{}]*4)
        with self.assertRaisesRegex(ValueError,'CHERCHI_OUTPUT_NOT_CLOSED_OR_INVERTED'):
            check_result(fake,'a'*64)


if __name__=='__main__':unittest.main()
