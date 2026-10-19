"""M7 optional *actual installed source* original-objective independent KKT.

This mode is available only on the trusted Spin/Cherchi host with precisely
pinned production Python sources, a run journal frozen externally, and a
saved Spin2014 objective contract. Does NOT redo Cherchi Boolean or Newton.
Even success cannot replace actual independent final geometry/derivative proof.
"""
from __future__ import annotations

from pathlib import Path
import importlib
import re

from .native_teacher_replay import need, ReplayRejected, sha256_file
from .terminal_archive_m7 import _json
from .original_stationarity_m7 import recompute_original_kkt

SHA=re.compile(r'[0-9a-f]{64}\Z')


def _source(name, expected_sha):
    need(type(expected_sha) is str and SHA.fullmatch(expected_sha),
         'EXTERNAL_ORIGINAL_PHYSICS_SOURCE_PIN_REQUIRED:'+name)
    try:
        module=importlib.import_module(name)
    except (ImportError,RuntimeError,OSError) as e:
        raise ReplayRejected('ORIGINAL_OBJECTIVE_PRODUCTION_SOURCE_UNAVAILABLE:'+name) from e
    need(sha256_file(module.__file__)==expected_sha,
         'ORIGINAL_PHYSICS_MODULE_SHA_MISMATCH:'+name)
    return module


def recheck_archived_original_objective(directory, terminal_review, *,
                                       expected_faster_material_sha256,
                                       expected_objective_contract_sha256):
    need(type(terminal_review) is dict and terminal_review.get('schema')==
         'W0_M7_PINNED_NUMERICAL_TERMINAL_REVIEW_V1' and
         terminal_review.get('numerical_terminal_record_consistent') is True and
         terminal_review.get('training_admissible') is False,
         'PINNED_TERMINAL_ARCHIVE_FIRST')
    physics=_source('make_it_stand.verification.faster_material',
                    expected_faster_material_sha256)
    contract_module=_source('make_it_stand.verification.spin2014_objective_contract',
                            expected_objective_contract_sha256)
    spin=importlib.import_module('make_it_stand.spin')
    need(callable(getattr(physics,'_independent_spin2014_rotational_physics',None)),
         'PRODUCTION_INDEPENDENT_OBJECTIVE_UNAVAILABLE')
    root=Path(directory)
    config=_json((root/'configuration.json').read_text(),'configuration')
    native=_json((root/'native-result.json').read_text(),'native')
    result=_json((root/'result.json').read_text(),'result')
    objective=config.get('objective_definition')
    need(type(objective) is dict and
         objective.get('objective_profile')=='SPIN2014_OBJECTIVES_QUADRIC_V1'
         and objective.get('schema')=='spin2014-shared-objective-contract-v1',
         'INDEPENDENT_ORIGINAL_OBJECTIVE_CONFIG_MISSING')
    params=objective.get('settings')
    need(type(params) is dict,'ORIGINAL_OBJECTIVE_SETTINGS_MISSING')
    settings=spin.Spin2014QuadricObjectiveConfig(**params)
    contract=contract_module.Spin2014ObjectiveContract(settings)
    need(contract.definition==objective and
         contract.identity==config.get('objective_contract_identity')==
         result['identity'].get('objective_contract_identity'),
         'EXACT_ORIGINAL_OBJECTIVE_IDENTITY_MISMATCH')
    run=native['native_run'];req=config['request']
    need(run.get('objective_profile')=='SPIN2014_OBJECTIVES_QUADRIC_V1',
         'NATIVE_ORIGINAL_PROFILE_NOT_PROVED')
    method=physics._independent_spin2014_rotational_physics
    def objective_fn(total_moments):
        return method(total_moments,settings)
    report=recompute_original_kkt(
        total_r=terminal_review['total_moments_from_archived_fixed_plus_exact_D'],
        native_c=run['quadric_coefficients'],
        multipliers=run['multipliers'],mu=run['multiplier_mu'],
        equation_tolerance=req['settings']['equation_tolerance'],
        objective=objective_fn,mode=req['mode'],
        original_objective_profile=run['objective_profile'])
    check=result['identity'].get('original_objective_terminal_check')
    need(type(check) is dict and check.get('objective_contract_identity')==contract.identity,
         'PRODUCTION_ORIGINAL_TERMINAL_CHECK_MISSING')
    need(abs(report['equation_norm']-float(check['raw_equation_residual']))<=1e-10,
         'INDEPENDENT_ORIGINAL_RESIDUAL_DIFFERENT_FROM_TERMINAL')
    report['original_objective_python_source_sha256']=expected_faster_material_sha256
    report['original_objective_contract_source_sha256']=expected_objective_contract_sha256
    report['original_objective_contract_identity']=contract.identity
    report['production_objective_source_matched_external_pins']=True
    report['independent_original_equation_calculated_from_archived_F_and_exact_D']=True
    report['fixed_geometry_independently_certified_in_this_check']=False
    report['training_admissible']=False
    return report
