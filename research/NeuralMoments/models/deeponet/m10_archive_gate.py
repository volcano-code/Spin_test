"""W5 M10 read-only byte-pinned gate for W0 81-point and W2 25-point reports.

The W0 M9 finite-point report is real, while original source CI is FAILED and
point 60 exhibits a nontrivial symbolic construction change. Matching exact
historical bytes never promotes the 81 local J observations to a certified
smooth/ambient derivative training set; numerical finite differences alone
cannot supply proof of a continuous neighborhood or a native terminal Newton.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .m9_archive_gate import inspect_historical_manifest

W0_M9_REPORT_GIT_BLOB='177fe9126d76d94236ecdca2d4750232f78f627a'
W0_M9_SOURCE_REF='c040e8268089eb6c04d6f83bf423e658cb551b87'
W0_M9_WORKFLOW=39123384402
W0_M9_ARTIFACT_SHA256='99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'


def _blob(b:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()


def inspect_w0_m9_report(path: str|Path)->dict:
    file=Path(path)
    if not file.is_file() or file.is_symlink():
        raise ValueError('W0 report must be a real pinned file, not a symlink')
    data=file.read_bytes()
    if _blob(data)!=W0_M9_REPORT_GIT_BLOB:
        raise ValueError('W0 M9 report Git blob mismatch')
    record=json.loads(data)
    witness=record.get('point60_witness')
    counts=record.get('independent_feature_classification')
    if not (record.get('schema')=='W0_M9_REAL_H8F_81_ARCHIVE_AUDIT_V1'
            and record.get('scope')=='RECONSTRUCTED_H8_NONAUTHOR_CAD_FINITE_POINTS_ONLY'
            and record.get('github_workflow_run')==W0_M9_WORKFLOW
            and record.get('github_original_workflow_conclusion')=='failure'
            and record.get('sha256_archive')==W0_M9_ARTIFACT_SHA256
            and record.get('checked_packet_identities')==81
            and record.get('fraction_reintegrated_sample_count')==81
            and record.get('independent_closed_oriented_surfaces')==81
            and record.get('fraction_max_abs_error')==0.0
            and record.get('anomaly_point')==60
            and record.get('certified_smooth_neighborhood') is False
            and record.get('certified_newton_direction') is False
            and record.get('newton_converged') is False
            and record.get('training_admissible') is False
            and isinstance(witness,dict)
            and witness.get('normalized_symbolic_triangle_identity') is False
            and witness.get('same_raw_material_face_indexing') is False
            and witness.get('added_oriented_triangles')==17
            and witness.get('removed_oriented_triangles')==17
            and isinstance(counts,dict)
            and counts.get('CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE')==1):
        raise ValueError('W0 historical evidence cannot certify native smooth training')
    if len(record.get('fraction_reintegrated_per_sample_max_abs_error',{}))!=81:
        raise ValueError('W0 claimed count does not match point ledger')
    return {'byte_pinned_W0_report':True,'W0_report_git_blob':W0_M9_REPORT_GIT_BLOB,
            'historical_native_samples_numeric_reintegrated':81,
            'H8f_81_real_numeric_material_observations':True,
            'original_workflow_conclusion':'failure',
            'point60_symbolic_branch_change':True,
            'permissible_native_J_supervision_samples':0,
            'source_archive_newton_converged':False,
            'W5_downloaded_original_native_zip':False,
            'material_and_continuum_geometry_certified':False,
            'training_admitted':False}


def inspect_joint_historical_gate(*,w0_report: str|Path,
                                  w2_manifest: str|Path)->dict:
    w0=inspect_w0_m9_report(w0_report)
    w2=inspect_historical_manifest(w2_manifest)
    if w2.get('training_allowed') or w0.get('training_admitted'):
        raise ValueError('unexpected historical admission, mandatory review')
    return {'W0_H8f_81':w0,'W2_H8e_25':w2,
            'certified_smooth_J_admitted_total':0,
            'no_native_Cherchi_evaluator_invoked':True,
            'no_training_from_original_archived_labels':True,
            'source_CI_status_preserved':'failure'}
