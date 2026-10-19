"""W0 M7: read-only, externally pinned *numerical terminal archive* review.

Does NOT run a Newton solver or construct a Cherchi Boolean. The input is an
existing production solve_cherchi_inprocess_and_seal_faster() directory.
Integrity + exact rational moment arithmetic != authentic native execution,
correct sealed geometry, a smooth derivative, or training-ready truth.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import os
import re
import struct

import numpy as np

from .native_teacher_replay import (ReplayRejected, need, digest, boundary_rows,
                                    exact_raw_moments, compare_floats, vector10,
                                    matrix10, finite_double)

SCHEMA = 'W0_M7_PINNED_TERMINAL_ARCHIVE_V1'
REQUIRED_FILES = frozenset((
    'configuration.json','events.jsonl','native-result.json','result.json',
    'complete.json','terminal-material-reference.json',
    'terminal-complement.json','terminal-complement-reference.json',
    'record-verification.json',
))
SHA = re.compile(r'[0-9a-f]{64}\Z')
EVALUATION = re.compile(r'evaluation-[0-9]{6}\.json\Z')
TIMING_KEYS = frozenset(('monotonic_ns','elapsed_ns','evaluator_wall_seconds',
                         'residual_evaluation_seconds','derivative_evaluation_seconds'))


def _finite(x, where, *, positive=False):
    v = finite_double(x, where)
    need(not positive or v > 0, where + ': NONPOSITIVE')
    return v


def _json(text, where):
    def pairs(rows):
        result={}
        for k,v in rows:
            need(k not in result, where+': DUPLICATE_JSON_KEY:'+k)
            result[k]=v
        return result
    def reject(s):
        raise ReplayRejected(where+': NONFINITE_JSON_CONSTANT:'+s)
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=reject)
    except (ValueError,TypeError,OverflowError) as exc:
        if isinstance(exc,ReplayRejected): raise
        raise ReplayRejected(where+': MALFORMED_JSON') from exc


def _read_exact_file(root, filename, sha):
    need(type(filename) is str and (filename in REQUIRED_FILES or EVALUATION.fullmatch(filename)),
         'UNEXPECTED_ARCHIVE_FILENAME')
    need(type(sha) is str and SHA.fullmatch(sha), 'BAD_EXTERNAL_PIN:'+filename)
    path=root / filename
    need(not path.is_symlink() and path.is_file(), 'ARCHIVE_FILE_MISSING_OR_SYMLINK:'+filename)
    # No symlink-following even if the path changes between the two checks.
    fd=os.open(path, os.O_RDONLY | getattr(os,'O_NOFOLLOW',0))
    try:
        with os.fdopen(fd,'rb') as f:
            data=f.read(128*1024*1024+1)
    except BaseException:
        raise
    need(len(data)<=128*1024*1024,'ARCHIVE_FILE_EXCEEDS_FIXED_REVIEW_LIMIT:'+filename)
    actual=hashlib.sha256(data).hexdigest()
    need(actual==sha,'EXTERNALLY_PINNED_SHA_MISMATCH:'+filename)
    return data


def _proj(value):
    if type(value) is dict:
        return {key:_proj(v) for key,v in value.items() if key not in TIMING_KEYS}
    if type(value) is list:
        return [_proj(x) for x in value]
    return value


def _same_c(a, b, name):
    left,right=vector10(a,name+'.left'),vector10(b,name+'.right')
    need(struct.pack('<10d',*left)==struct.pack('<10d',*right),name+': NATIVE_C_BIT_MISMATCH')
    return left


def _r10_close(a,b,name):
    return compare_floats(vector10(a,name),b,label=name)


def _j_transform(c, native_j, event):
    """Production Jacobian-coordinate chain rule, not Hessian symmetry."""
    native_j=np.asarray(matrix10(native_j),dtype=np.float64)
    payload=event.get('evaluation_payload')
    need(type(payload) is dict,'TERMINAL_EVENT_PAYLOAD_REQUIRED')
    need(event.get('solver_coordinate_identity')=='literal_monomial_unit_sphere_v1',
         'SOLVER_COORDINATE_CONVENTION_CHANGED')
    solver_J=np.asarray(matrix10(payload.get('solver_moment_jacobian')),dtype=np.float64)
    s=np.asarray(vector10(payload.get('solver_coordinates'),'solver_s'),dtype=np.float64)
    inv=np.array([1.]*7+[.5]*3,dtype=np.float64)
    p=s*inv
    length=float(np.linalg.norm(p))
    need(math.isfinite(length) and length>0,'SOLVER_COORDINATE_PULLBACK_ZERO')
    p=p/length
    need(np.max(np.abs(p-np.asarray(c)))<=1e-11,'SOLVER_VS_NATIVE_C_MISMATCH')
    expected=native_j@((np.eye(10)-np.outer(p,p))*inv[None,:]/length)
    error=float(np.max(np.abs(expected-solver_J)))
    need(math.isfinite(error) and error<=1e-10,'SOLVER_JACOBIAN_CHAIN_RULE_MISMATCH')
    return error


def review_pinned_terminal_archive(directory, external_pins):
    """Review frozen archives only; NEVER return a teacher acceptance grant.

    Pins must be frozen by an independent collector AFTER the writer closes
    and BEFORE review. Pre-run pins separately cover the original source/model.
    Rehashing the journal in this same review is not authentication.
    """
    need(type(external_pins) is dict and set(external_pins)==
         {'schema','files','expected_c_sha256','expected_problem_digest'},
         'EXTERNALLY_FROZEN_TERMINAL_PIN_SET_REQUIRED')
    need(external_pins['schema']==SCHEMA,'TERMINAL_PIN_SCHEMA_UNSUPPORTED')
    need(type(external_pins['expected_c_sha256']) is str and SHA.fullmatch(external_pins['expected_c_sha256']),
         'BAD_EXTERNAL_C_PIN')
    need(type(external_pins['expected_problem_digest']) is str and SHA.fullmatch(external_pins['expected_problem_digest']),
         'BAD_EXTERNAL_PROBLEM_PIN')
    pins=external_pins['files']
    need(type(pins) is dict and set(pins).issuperset(REQUIRED_FILES) and
         all(type(key) is str and
             (key in REQUIRED_FILES or EVALUATION.fullmatch(key)) for key in pins),
         'FULL_ARCHIVE_FILE_PINS_REQUIRED')
    evaluation_names={name for name in pins if EVALUATION.fullmatch(name)}
    need(bool(evaluation_names), 'FULL_ARCHIVE_FILE_PINS_REQUIRED')
    root=Path(directory)
    need(root.is_dir() and not root.is_symlink(), 'REAL_ARCHIVE_DIRECTORY_REQUIRED')
    data={key:_read_exact_file(root,key,sha) for key,sha in pins.items()}
    objs={key:_json(value.decode('utf-8'),key) for key,value in data.items()
          if key != 'events.jsonl'}
    config=objs['configuration.json'];done=objs['complete.json'];result=objs['result.json'];
    native=objs['native-result.json'];terminal=objs['terminal-material-reference.json'];
    complement=objs['terminal-complement.json'];cref=objs['terminal-complement-reference.json'];
    record=objs['record-verification.json']
    need(config.get('schema')=='cherchi-inprocess-formal-run-v1','PRODUCTION_RUN_CONFIG_SCHEMA_MISMATCH')
    need(config.get('initialization')=='REQUEST_SEED_ONLY','UNFROZEN_NATIVE_INITIALIZATION')
    req=config.get('request')
    need(type(req) is dict and type(req.get('settings')) is dict,
         'FROZEN_REQUEST_AND_SETTINGS_REQUIRED')
    settings=req['settings']
    need(settings.get('equation_profile')=='DUAL_MONOMIAL_RAW_V1','UNSUPPORTED_EQUATION_PROFILE')
    threshold=_finite(settings.get('equation_tolerance'),'frozen.equation_tolerance',positive=True)
    need(threshold<=1e-12,'RELAXED_TERMINAL_TOLERANCE')
    need(done.get('complete') is True and done.get('status')==result.get('status')=='CONVERGED',
         'RUN_NOT_COMPLETED_AND_CONVERGED')
    identity=result.get('identity')
    need(type(identity) is dict and identity.get('problem_digest')==external_pins['expected_problem_digest'],
         'TERMINAL_PROBLEM_PIN_MISMATCH')
    need(native.get('schema')=='cherchi-numerical-terminal-v1'
         and native.get('material_audit_complete') is False,'NATIVE_RESULT_SCHEMA_MISMATCH')
    need(native.get('configuration_sha256')==pins['configuration.json'],
         'NATIVE_RESULT_CONFIG_BINDING_MISMATCH')
    run=native.get('native_run')
    need(type(run) is dict and run.get('status')=='CONVERGED',
         'NOT_CONVERGED_NATIVE_NEWTON')
    need(run==identity.get('native_run'),'NATIVE_RUN_IDENTITY_MISMATCH')
    c=vector10(run.get('quadric_coefficients'),'native_accepted_c')
    need(abs(math.sqrt(sum(x*x for x in c))-1.)<=1e-12,'NONUNIT_NATIVE_TERMINAL_C')
    need(digest(list(c))==external_pins['expected_c_sha256'],'TERMINAL_COEFFICIENT_PIN_MISMATCH')
    residual=_finite(run.get('raw_equation_residual'),'native_raw_equation_residual')
    need(0<=residual<=threshold,'NATIVE_TERMINAL_RAW_RESIDUAL_UNQUALIFIED')
    need(run.get('equation_profile')==settings['equation_profile'],
         'NATIVE_EQUATION_PROFILE_MISMATCH')
    refname=terminal.get('evaluation_file')
    need(type(refname) is str and EVALUATION.fullmatch(refname) and refname in pins,
         'EXTERNALLY_PINNED_TERMINAL_MATERIAL_REQUIRED')
    material=objs[refname]
    _same_c(c,terminal.get('coefficients'),'reference_terminal_c')
    _same_c(c,material.get('quadric_coefficients'),'material_terminal_c')
    need(terminal.get('sha256')==pins[refname] and
         terminal.get('geometry_hash')==material.get('geometry_hash'),
         'TERMINAL_MATERIAL_REFERENCE_MISMATCH')
    source=material.get('quadric_source_identity')
    need(type(source) is str and SHA.fullmatch(source) and
         source==digest({'vertices':material.get('quadric_source_vertices'),
                        'faces':material.get('quadric_source_faces'),
                        'coefficients':list(c)}), 'TERMINAL_SOURCE_IDENTITY_MISMATCH')
    geometry=digest({'vertices':material.get('material_proof',{}).get('exact_vertices'),
                     'faces':material.get('variable_faces')})
    need(geometry==material.get('geometry_hash'),'TERMINAL_GEOMETRY_HASH_MISMATCH')
    # Explicitly pinned completion does not entail geometry/material authority.
    need(cref.get('schema')=='cherchi-terminal-complement-reference-v1'
         and cref.get('evaluation_file')=='terminal-complement.json'
         and cref.get('sha256')==pins['terminal-complement.json']
         and cref.get('retained_reference_sha256')==pins['terminal-material-reference.json']
         and cref.get('configuration_sha256')==pins['configuration.json']
         and cref.get('material_audit_complete') is False,
         'COMPLEMENT_REFERENCE_BINDING_MISMATCH')
    _same_c(c,complement.get('quadric_coefficients'),'complement_terminal_c')
    need(complement.get('quadric_source_identity')==source,
         'TERMINAL_COMPLEMENT_SOURCE_CHANGED')
    operations={'intersection':'subtraction','subtraction':'intersection'}
    need(material.get('boolean_operation') in operations and
         complement.get('boolean_operation')==operations[material['boolean_operation']],
         'TERMINAL_COMPLEMENT_NOT_OPPOSITE_SIDE')
    cc=identity.get('terminal_complement')
    binding=identity.get('external_terminal_binding')
    need(type(cc) is dict and cc.get('status')=='PASSED'
         and cc.get('geometry_hash')==complement.get('geometry_hash')
         and cc.get('topology_hash')==complement.get('topology_hash')
         and cc.get('quadric_source_identity')==source,
         'SEALED_TERMINAL_COMPLEMENT_MISMATCH')
    need(type(binding) is dict and binding.get('retained_geometry')==geometry
         and binding.get('complement_geometry')==complement.get('geometry_hash')
         and binding.get('retained_topology')==material.get('topology_hash')
         and binding.get('complement_topology')==complement.get('topology_hash'),
         'SEALED_TERMINAL_GEOMETRY_BINDING_MISMATCH')
    need(record.get('record_integrity_valid') is True and
         record.get('core_admission') is False,'UNVERIFIED_OR_OVERPROMOTED_PRODUCTION_RECORD')
    text=data['events.jsonl'].decode('utf-8')
    need(text.endswith('\n') and len(text.splitlines())>=3,'INCOMPLETE_TERMINAL_EVENT_LOG')
    events=[_json(line,'events.jsonl') for line in text.splitlines()]
    need(events[-1].get('kind')=='RUN_TERMINATED' and
         events[-1].get('status')=='CONVERGED' and
         events[-1].get('evaluation_count')==done.get('evaluation_count'),
         'RUN_TERMINAL_LOG_MISMATCH')
    # Real Newton journals have many evaluation checkpoints; every MAP_SAVED
    # must bind a distinct externally pinned file, not merely the last one.
    mapped=[e for e in events if e.get('kind') in ('MAP_SAVED','MAP_REJECTED')]
    need(bool(mapped) and
         [e.get('evaluation') for e in mapped] == list(range(1,len(mapped)+1)) and
         len(mapped)==done.get('evaluation_count'),
         'NONCONTIGUOUS_NEWTON_MAP_CHECKPOINTS')
    saved=[row for row in mapped if row['kind']=='MAP_SAVED']
    claimed=set()
    for item in saved:
        i=item['evaluation']
        filename=item.get('evaluation_file')
        need(filename==f'evaluation-{i:06d}.json' and filename not in claimed
             and filename in evaluation_names and
             item.get('sha256')==pins[filename],
             'MISSING_OR_UNPINNED_NEWTON_EVALUATION')
        material_item=objs[filename]
        need(type(material_item) is dict and
             material_item.get('quadric_coefficients')==item.get('coefficients') and
             material_item.get('geometry_hash')==item.get('geometry_hash') and
             material_item.get('evaluation_map_identity')==config.get('evaluation_map_identity') and
             material_item.get('boolean_backend_identity')==config.get('boolean_backend_identity'),
             'NONTERMINAL_EVALUATION_ATTACHMENT_MISMATCH')
        claimed.add(filename)
    need(claimed==evaluation_names,'UNREFERENCED_PINNED_EVALUATION')
    newton=[e['event'] for e in events if e.get('kind')=='NEWTON_EVENT']
    need(newton and _proj(newton)==_proj(run.get('events')),
         'NATIVE_NEWTON_EVENT_LEDGER_MISMATCH')
    need(newton[-1].get('type')=='attempt_terminal' and
         newton[-1].get('reason')=='converged', 'NEWTON_LAST_ATTEMPT_NOT_CONVERGED')
    accepted=[e for e in newton if e.get('type')=='evaluation'
              and e.get('outcome')=='accepted' and
              type(e.get('step')) in (int,float) and e['step']>0]
    need(accepted,'NO_ACTUAL_ACCEPTED_NEWTON_UPDATE')
    last=accepted[-1]
    _same_c(c,last.get('quadric_coefficients'),'last_accepted_terminal_c')
    need(last.get('evaluation_index')==run.get('function_evaluations')
         and newton[-1].get('evaluation_index')==last.get('evaluation_index')
         and done.get('evaluation_count')==run.get('function_evaluations'),
         'NEWTON_EVALUATION_COUNTER_MISMATCH')
    need(last.get('material_geometry_hash')==geometry,'LAST_ACCEPTED_GEOMETRY_MISMATCH')
    payload=last.get('evaluation_payload')
    need(type(payload) is dict and payload.get('geometry_hash')==geometry
         and payload.get('boolean_backend_identity')==config.get('boolean_backend_identity')
         and payload.get('evaluation_map_identity')==config.get('evaluation_map_identity'),
         'LAST_ACCEPTED_NATIVE_MAP_PROVENANCE_MISMATCH')
    need(material.get('boolean_backend_identity')==config.get('boolean_backend_identity')
         and material.get('evaluation_map_identity')==config.get('evaluation_map_identity'),
         'TERMINAL_MATERIAL_CONTEXT_CHANGED')
    # Reintegrate exact *target* rational boundary independently; validates
    # saved r_D, total r, and retained/fixed cache accounting, NOT Boolean set.
    pts,triangles=boundary_rows(material.get('variable_rational_vertices'),
                                material.get('variable_faces'))
    density=Fraction.from_float(_finite(req.get('material_density'),'material_density',positive=True))
    rd=exact_raw_moments(pts,triangles,density)
    _r10_close(material.get('variable_raw_moments'),rd,'TERMINAL_VARIABLE_R10')
    fixed=vector10(binding.get('fixed_moments_target'),'bound_fixed_rF')
    total=[float(a)+float(b) for a,b in zip(fixed,rd)]
    _r10_close(material.get('raw_moments'),total,'TERMINAL_TOTAL_R10')
    _r10_close(payload.get('solver_raw_moments'),total,'NATIVE_SOLVER_TOTAL_R10')
    _r10_close(binding.get('variable_moments_target'),rd,'BOUND_VARIABLE_R10')
    _r10_close(binding.get('total_moments_target'),total,'BOUND_TOTAL_R10')
    need(payload.get('variable_raw_moments')==material.get('variable_raw_moments'),
         'TERMINAL_PAYLOAD_VARIABLE_R_CHANGED')
    jacobian_error=_j_transform(c,material.get('moment_jacobian'),last)
    # No assumption that Jc is symmetric; transformation is a chain rule.
    return {
       'schema':'W0_M7_PINNED_NUMERICAL_TERMINAL_REVIEW_V1',
       'external_archive_bytes_checked':len(data),
       'pinned_saved_evaluation_count':len(saved),
       'mapped_evaluation_count':len(mapped),
       'journal_sha256':pins['events.jsonl'],
       'native_terminal_c_sha256':digest(list(c)),
       'quadric_source_sha256':source,
       'retained_geometry_sha256':geometry,
       'complement_geometry_sha256':complement.get('geometry_hash'),
       'raw_equation_residual_recorded':residual,
       'frozen_equation_tolerance':threshold,
       'jacobian_solver_chain_rule_max_error':jacobian_error,
       'exact_rD_reintegrated':True,
       'exact_rD_rational_tokens':[f'{v.numerator}/{v.denominator}' for v in rd],
       'total_moments_from_archived_fixed_plus_exact_D':total,
       'fixed_moments_are_independently_sealed':False,
       'numerical_terminal_record_consistent':True,
       'production_evidence_verifier_executed':False,
       'independent_physical_objective_residual_verified':False,
       'native_full_partition_certified':False,
       'smooth_derivative_neighborhood_certified':False,
       'newton_terminal_independently_certified':False,
       'training_admissible':False,
       'scope':'PINNED_ARCHIVE_NUMERIC_CONSISTENCY_ONLY_NOT_NATIVE_AUTHORITY',
    }
