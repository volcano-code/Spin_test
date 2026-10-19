"""W0 M7: cross-link archived Newton terminal and independent M6 partition.

This checks a *declared and externally pinned* evidence chain's internal
consistency. A matching SHA does NOT establish that native code actually ran.
The two results are separate frozen evaluations and must have identical c,
retained material, and exact source identity. Training is always blocked.
"""
from __future__ import annotations

from .native_teacher_replay import ReplayRejected, digest, need
from .full_partition_m6 import partition_result


ORDER=('fixed_plus_design','design_cut','full_outer')


def review_terminal_partition_chain(terminal, partition, *, expected_partition_sha256):
    need(type(terminal) is dict and terminal.get('schema')==
         'W0_M7_PINNED_NUMERICAL_TERMINAL_REVIEW_V1' and
         terminal.get('training_admissible') is False and
         terminal.get('numerical_terminal_record_consistent') is True and
         terminal.get('production_evidence_verifier_executed') is False,
         'PINNED_M7_TERMINAL_REVIEW_REQUIRED')
    need(type(expected_partition_sha256) is str and len(expected_partition_sha256)==64 and
         all(c in '0123456789abcdef' for c in expected_partition_sha256),
         'EXTERNAL_M6_EVIDENCE_SHA_REQUIRED')
    need(type(partition) is dict and digest(partition)==expected_partition_sha256,
         'EXTERNAL_M6_PARTITION_EVIDENCE_SHA_MISMATCH')
    need(partition.get('schema')=='W0_M6_NATIVE_COMPLETE_MATERIAL_PARTITION_V1'
         and partition.get('native_full_partition_certified') is True and
         partition.get('training_admissible') is False and
         partition.get('smooth_derivative_certified') is False and
         partition.get('newton_terminal_certified') is False and
         partition.get('complement_additional_source_calls')==0 and
         partition.get('complement_additional_boolean_calls')==1,
         'M6_COMPLETE_SAME_SOURCE_PARTITION_CLAIM_REQUIRED')
    predicates=partition.get('exact_partition_predicates')
    need(type(predicates) is list and len(predicates)==3,
         'M6_ALL_THREE_PARTITIONS_REQUIRED')
    for name,row in zip(ORDER,predicates):
        need(type(row) is dict and row.get('label')==name and
             type(row.get('native_predicate_facts')) is dict,
             'M6_FULL_NATIVE_PARTITION_WITNESS_MISSING:'+name)
        checked=partition_result(row['native_predicate_facts'],name,row.get('part_count'))
        need(checked['partition_digest']==row.get('partition_digest') and
             checked['structural_flags_checked'] is True,
             'M6_PARTITION_WITNESS_BINDING_MISMATCH:'+name)
    m5=partition.get('M5_evidence')
    need(type(m5) is dict and m5.get('schema')=='W0_M5_LIVE_W0_W2_PARITY_V1' and
         m5.get('training_admissible') is False,
         'M5_INDEPENDENT_REFERENCE_EVIDENCE_REQUIRED')
    m4=m5.get('m4_native_evidence')
    need(type(m4) is dict and m4.get('native_execution_observed') is True and
         m4.get('native_region_proved') is True and
         m4.get('training_admissible') is False,
         'M4_SOURCE_AND_NATIVE_REGION_EVIDENCE_REQUIRED')
    need(m4.get('frozen_native_c_sha256')==terminal['native_terminal_c_sha256'],
         'M6_REPLAY_C_DIFFERS_FROM_SAVED_TERMINAL')
    need(m4.get('source_geometry_sha256')==terminal['retained_geometry_sha256'],
         'M6_RETAINED_GEOMETRY_DIFFERS_FROM_TERMINAL')
    need(m4.get('source_quadric_sha256')==terminal['quadric_source_sha256'],
         'M6_QUADRIC_SOURCE_CHANGED')
    need(partition.get('retained_plus_cavity_equals_design_r10_exact') is True and
         partition.get('fixed_plus_retained_density_weighted_moments_verified') is True,
         'M6_INDEPENDENT_F_D_MATERIAL_R10_REQUIRED')
    return {
        'schema':'W0_M7_TERMINAL_AND_PARTITION_IDENTITY_CHAIN_V1',
        'precommitted_M6_archive_sha256':expected_partition_sha256,
        'shared_native_c_sha256':terminal['native_terminal_c_sha256'],
        'shared_retained_geometry_sha256':terminal['retained_geometry_sha256'],
        'shared_quadric_source_sha256':terminal['quadric_source_sha256'],
        'exact_partition_predicate_count':len(predicates),
        'all_three_m6_witnesses_structurally_bound':True,
        'native_newton_record_and_m6_claims_consistent':True,
        'proof_of_actual_independent_native_execution':False,
        'independent_derivative_neighborhood_certified':False,
        'independent_newton_terminal_certified':False,
        'training_admissible':False,
    }
