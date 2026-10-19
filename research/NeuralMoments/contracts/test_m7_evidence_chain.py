"""M7 terminal/M6 evidence crosswalk is mathematical identity only."""
import copy
import pytest

from .native_teacher_replay import ReplayRejected,digest
from .m7_evidence_chain import review_terminal_partition_chain
from .test_terminal_archive_m7 import make_pinned_archive
from .terminal_archive_m7 import review_pinned_terminal_archive


def make_parts(terminal):
    facts=[]
    for index,name in enumerate(('fixed_plus_design','design_cut','full_outer')):
        n=2 if index!=2 else 3
        signature=str(index+1)*64
        native=dict(completed=True,complete_partition=True,union_equals_whole=True,
                    no_positive_volume_overlap=True,missing_whole_content=False,
                    excess_union_content=False,part_subset_whole=[True]*n,
                    positive_volume_overlap_pairs=[],partition_digest=signature)
        facts.append(dict(label=name,part_count=n,partition_digest=signature,
                          native_predicate_facts=native))
    return dict(schema='W0_M6_NATIVE_COMPLETE_MATERIAL_PARTITION_V1',
        native_full_partition_certified=True,training_admissible=False,
        smooth_derivative_certified=False,newton_terminal_certified=False,
        complement_additional_source_calls=0,complement_additional_boolean_calls=1,
        retained_plus_cavity_equals_design_r10_exact=True,
        fixed_plus_retained_density_weighted_moments_verified=True,
        exact_partition_predicates=facts,
        M5_evidence=dict(schema='W0_M5_LIVE_W0_W2_PARITY_V1',
                         training_admissible=False,m4_native_evidence=dict(
                            native_execution_observed=True,native_region_proved=True,
                            training_admissible=False,
                            frozen_native_c_sha256=terminal['native_terminal_c_sha256'],
                            source_geometry_sha256=terminal['retained_geometry_sha256'],
                            source_quadric_sha256=terminal['quadric_source_sha256'])))


def prepared(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    terminal=review_pinned_terminal_archive(root,pins)
    part=make_parts(terminal)
    return terminal,part


def test_cross_window_evidence_only_consistent(tmp_path):
    t,p=prepared(tmp_path)
    v=review_terminal_partition_chain(t,p,expected_partition_sha256=digest(p))
    assert v['exact_partition_predicate_count']==3
    assert v['all_three_m6_witnesses_structurally_bound']
    assert not v['training_admissible']
    assert not v['proof_of_actual_independent_native_execution']


@pytest.mark.parametrize('mutate,needle',[
    (lambda p:p.update(native_full_partition_certified=False),'PARTITION_CLAIM'),
    (lambda p:p.update(training_admissible=True),'PARTITION_CLAIM'),
    (lambda p:p['exact_partition_predicates'].pop(),'ALL_THREE'),
    (lambda p:p['exact_partition_predicates'][0]['native_predicate_facts'].update(complete_partition=False),'NATIVE_COMPLETE_PARTITION_FAILED'),
    (lambda p:p['exact_partition_predicates'][1]['native_predicate_facts'].update(missing_whole_content=True),'NATIVE_MISSING'),
    (lambda p:p['exact_partition_predicates'][2].update(partition_digest='0'*64),'WITNESS_BINDING'),
    (lambda p:p['M5_evidence']['m4_native_evidence'].update(frozen_native_c_sha256='0'*64),'REPLAY_C'),
    (lambda p:p['M5_evidence']['m4_native_evidence'].update(source_quadric_sha256='0'*64),'QUADRIC_SOURCE'),
    (lambda p:p['M5_evidence']['m4_native_evidence'].update(source_geometry_sha256='0'*64),'RETAINED_GEOMETRY'),
    (lambda p:p.update(complement_additional_source_calls=1),'PARTITION_CLAIM'),
    (lambda p:p.update(retained_plus_cavity_equals_design_r10_exact=False),'INDEPENDENT_F_D'),
])
def test_malformed_chain_rejected_even_if_local_digest_rewritten(tmp_path,mutate,needle):
    t,p=prepared(tmp_path);mutate(p)
    # Even granting a malicious writer a fresh pin does not make false facts coherent.
    with pytest.raises(ReplayRejected,match=needle):
        review_terminal_partition_chain(t,p,expected_partition_sha256=digest(p))


def test_external_m6_digest_cannot_silently_follow_modified_archive(tmp_path):
    t,p=prepared(tmp_path);sha=digest(p);p['exact_partition_predicates'][0]['native_predicate_facts']['union_equals_whole']=False
    with pytest.raises(ReplayRejected,match='EXTERNAL_M6_PARTITION_EVIDENCE_SHA_MISMATCH'):
        review_terminal_partition_chain(t,p,expected_partition_sha256=sha)


def test_raw_m6_claims_not_substitutable_by_generic_mapping(tmp_path):
    t,p=prepared(tmp_path)
    p['exact_partition_predicates'][1]['native_predicate_facts']={'completed':True}
    with pytest.raises(ReplayRejected,match='NATIVE_COMPLETE_PARTITION_FAILED'):
        review_terminal_partition_chain(t,p,expected_partition_sha256=digest(p))
