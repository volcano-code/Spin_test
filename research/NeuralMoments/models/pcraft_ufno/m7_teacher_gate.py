"""Fail-closed W2 historical candidate reader for W6 M7 only.

This is an audit *of counts and categories*, never a real teacher importer.
Real Cherchi labels must be admitted by an external independent native
material+W0 derivative-neighborhood verifier after source/geometry/solver
seals; a forged NATIVE_VERIFIED flag and positive counts are insufficient.
H8f 81 archived point candidates are EXCLUDED from M7 training/evaluation.
"""
from __future__ import annotations

from typing import Mapping


class NativeTeacherNotReady(ValueError):
    pass


def audit_manifest(manifest: Mapping) -> dict:
    if not isinstance(manifest,Mapping):
        raise TypeError('W2 manifest object required')
    splits=manifest.get('data_splits')
    if not isinstance(splits,dict):
        raise ValueError('W2 data_splits must be explicit')
    train=splits.get('train')
    test=splits.get('test')
    excluded=splits.get('excluded')
    if not all(isinstance(x,list) for x in (train,test,excluded)):
        raise ValueError('W2 train/test/excluded must be explicit lists')
    excluded_count=sum(x.get('count',0) for x in excluded if isinstance(x,dict)
                       and type(x.get('count',0)) is int and x.get('count',0)>=0)
    candidate_index=manifest.get('m9_real_h8f_81_evidence')
    report={
        'w2_schema':manifest.get('schema'),
        'declared_native_teacher_runs':manifest.get('native_teacher_runs'),
        'declared_training_samples':manifest.get('training_samples'),
        'archived_excluded_candidates':excluded_count,
        'W2_h8f_81_source_verified':isinstance(candidate_index,dict),
        'published_train_split_entries':len(train),
        'published_test_split_entries':len(test),
        'Jacobian_training_admitted':0,
        'admitted_for_training':False,
        'blockers':['W0 independently sealed native material and tangent/neighborhood evidence not supplied',
                    'W2 archived finite-point H8f candidates explicitly excluded',
                    'No independently qualified production training set']
    }
    if manifest.get('pending_dependency'):
        report['blockers'].append('W2 declares pending dependency: '+str(manifest['pending_dependency']))
    if (manifest.get('schema') != 'w2-cherchi-teacher-v2-pre-w0' or
        manifest.get('native_teacher_runs')!=0 or
        manifest.get('training_samples')!=0 or train or test):
        report['blockers'].append('Unreviewed manifest change or train split: fail closed')
    return report


def require_native_training(manifest: Mapping)->None:
    checked=audit_manifest(manifest)
    raise NativeTeacherNotReady('W6 M7: W2 training blocked: '+'; '.join(checked['blockers']))
