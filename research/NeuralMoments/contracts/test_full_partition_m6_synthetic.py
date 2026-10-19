"""Synthetic native-shaped interfaces, testing orchestration only (NOT real native proof)."""
from __future__ import annotations
from fractions import Fraction as F
import sys
import types
from unittest.mock import patch
import numpy as np
import pytest

from . import full_partition_m6 as m6
from .native_teacher_replay import ReplayRejected,exact_raw_moments,boundary_rows

FACES=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
       [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]]


def box(lo,hi):
    x0,y0,z0=lo;x1,y1,z1=hi
    return [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
            (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]


def token(vertices):
    return m6.to_rational_tokens(vertices)


def raw(rows,faces,density):
    p,f=boundary_rows(rows,faces)
    return [float(x) for x in exact_raw_moments(p,f,F(density))]


class FakeRegion:
    @property
    def facts(self):return {'completed':True,'valid':True,'input_digest':'fake','region_digest':'fake'}


class FakeMesh:
    def __init__(self,mesh):
        if mesh is None:
            self.explicit_empty=True;self.rational_vertices=None
            self.vertices=[];self.faces=[]
        else:
            self.explicit_empty=False
            v,f=mesh
            self.vertices=[list(row) for row in v]
            self.faces=[list(row) for row in f]
            self.rational_vertices=token(v)
        self._region=FakeRegion()
    @classmethod
    def from_rationals(cls,v,f):
        points=[[F(x) for x in row] for row in v]
        return cls((points,f))
    def exact_region(self):return self._region
    def arrays(self):
        return np.asarray(self.vertices,dtype=float).reshape(-1,3),\
               np.asarray(self.faces,dtype=int).reshape(-1,3)


class FakeProblem:
    def __init__(self):
        self.normalization={'R':1.}
        self.original=FakeMesh((box((F(0),)*3,(F(2),)*3),FACES))
        inner=box((F(1,2),)*3,(F(3,2),)*3)
        self.design_regions=[types.SimpleNamespace(mesh=FakeMesh((inner,FACES)))]
        outer=box((F(0),)*3,(F(2),)*3)
        shell_vertices=outer+inner
        shell_faces=FACES+[[i+8 for i in reversed(f)] for f in FACES]
        self.fixed_regions=[types.SimpleNamespace(mesh=FakeMesh((shell_vertices,shell_faces)),density=1.25)]


class FakeNative:
    ExactMaterialRegion=FakeRegion
    def __init__(self):self.calls=[];self.reject=None
    def check_exact_material_partition(self,whole,parts):
        i=len(self.calls);self.calls.append(len(parts))
        out=dict(completed=True,complete_partition=True,union_equals_whole=True,
            no_positive_volume_overlap=True,part_subset_whole=[True]*len(parts),
            missing_whole_content=False,excess_union_content=False,
            positive_volume_overlap_pairs=[],partition_digest=('a' if i==0 else 'b' if i==1 else 'c')*64)
        if i==self.reject:out['union_equals_whole']=False
        return out
    def make_exact_material_region_from_rationals(self,*args):return FakeRegion()


class FakeEvaluator:
    def __init__(self,problem):
        self.normalization_origin=np.array([0.,0.,0.]);self.length=1.
        self.request=types.SimpleNamespace(material_density=1.,target_origin=[0.,0.,0.],
            target_axes=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        self.call_counts={'source':1,'boolean':1}
        self.stage_seconds={'source':0.01,'boolean':0.02}
        self.saved={
            'material_proof':{'exact_vertices':token(box((F(1,2),F(1,2),F(1,2)),
                (F(3,2),F(3,2),F(1))))},
            'variable_faces':FACES,
            'boolean_operation':'intersection',
            'quadric_source_identity':'source-hash-test',
            'quadric_source_vertices':[[1.,2.,3.]],
            'quadric_source_faces':[[0,1,2]],
        }
        lower=box((F(1,2),F(1,2),F(1,2)),(F(3,2),F(3,2),F(1)))
        upper=box((F(1,2),F(1,2),F(1)),(F(3,2),F(3,2),F(3,2)))
        self.retained=token(lower)
        self.cavity=token(upper)
        fixed=problem.fixed_regions[0].mesh
        self.fixed=raw(fixed.rational_vertices,fixed.faces,F(5,4))
        self.bad_source=False;self.rebuild_source=False
    def material(self,c):return self.saved
    def complement_of_saved_source(self,saved):
        self.call_counts['boolean']+=1
        self.stage_seconds['boolean']+=0.01
        if self.rebuild_source:self.call_counts['source']+=1
        return dict(variable_rational_vertices=self.cavity,variable_faces=FACES,
            variable_raw_moments=raw(self.cavity,FACES,F(1)),
            boolean_operation='subtraction',
            quadric_source_identity='altered' if self.bad_source else saved['quadric_source_identity'],
            quadric_source_vertices=saved['quadric_source_vertices'],
            quadric_source_faces=saved['quadric_source_faces'])


def fake_imports(monkeypatch):
    n=FakeNative()
    a=types.ModuleType('make_it_stand')
    b=types.ModuleType('make_it_stand.verification')
    c=types.ModuleType('make_it_stand.verification.cherchi_inprocess');c.InProcessCherchiEvaluator=FakeEvaluator
    d=types.ModuleType('make_it_stand.verification.spin_problem');d.MeshSnapshot=FakeMesh;d.SpinArtifactProblem=FakeProblem
    e=types.ModuleType('make_it_stand.verification.spin_common');e.native=lambda:n
    for mod in (a,b,c,d,e):monkeypatch.setitem(sys.modules,mod.__name__,mod)
    return n


def run_fake(monkeypatch,change=None):
    n=fake_imports(monkeypatch);p=FakeProblem();e=FakeEvaluator(p)
    if change:
        change(n,e)
    baseline={'schema':'W0_M5_LIVE_W0_W2_PARITY_V1',
             'training_admissible':False,'m4_native_evidence':
             {'native_execution_observed':True,'native_region_proved':True}}
    with patch.object(m6,'audit_native_w0_w2_once',return_value=baseline):
        result=m6.audit_native_full_partition_once(evaluator=e,problem=p,c=[1.]+[0.]*9,pins={})
    return result,n,e


def test_synthetic_full_partition_honors_exact_carve_and_fixed_density(monkeypatch):
    result,n,e=run_fake(monkeypatch)
    assert result['retained_plus_cavity_equals_design_r10_exact']
    assert result['fixed_plus_retained_density_weighted_moments_verified']
    assert [x['part_count'] for x in result['exact_partition_predicates']]==[2,2,3]
    assert n.calls==[2,2,3]
    assert e.call_counts=={'source':1,'boolean':2}
    assert result['native_full_partition_certified']
    assert len(result['exact_partition_predicates'][0]['native_predicate_facts']['part_subset_whole'])==2
    assert result['complement_stage_seconds']['boolean']==pytest.approx(.01)
    assert result['process_rss_hwm_after_bytes']>=result['process_rss_hwm_before_bytes']
    assert not result['smooth_derivative_certified']
    assert not result['newton_terminal_certified']
    assert not result['training_admissible']


@pytest.mark.parametrize('which',[0,1,2])
def test_synthetic_native_partition_predicate_failure_veto(monkeypatch,which):
    with pytest.raises(ReplayRejected,match='NATIVE_UNION_EQUALS_WHOLE_FAILED'):
        run_fake(monkeypatch,lambda n,e:setattr(n,'reject',which))


def test_complement_source_identity_change_rejected(monkeypatch):
    with pytest.raises(ReplayRejected,match='OPPOSITE_MATERIAL_SOURCE'):
        run_fake(monkeypatch,lambda n,e:setattr(e,'bad_source',True))


def test_complement_rebuilds_native_source_rejected(monkeypatch):
    with pytest.raises(ReplayRejected,match='COMPLEMENT_REBUILT_SOURCE'):
        run_fake(monkeypatch,lambda n,e:setattr(e,'rebuild_source',True))


def test_tampered_cavity_moments_rejected(monkeypatch):
    original=FakeEvaluator.complement_of_saved_source
    def altered(self,saved):
        d=original(self,saved);d['variable_raw_moments'][0]+=1
        return d
    with patch.object(FakeEvaluator,'complement_of_saved_source',altered):
        with pytest.raises(ReplayRejected,match='CAVITY_EXACT_MOMENTS'):
            run_fake(monkeypatch)
