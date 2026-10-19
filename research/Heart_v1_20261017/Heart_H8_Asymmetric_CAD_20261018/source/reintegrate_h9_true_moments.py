"""W3 H9: independently re-integrate actual archived Cherchi rational materials.

This is *historical evidence replay*, NOT four new native evaluations,
NOT a production smooth-neighborhood certificate, and NOT Newton admission.
The source output from H8f is independently integrated with Python Fraction
oriented tetrahedra rather than trusting the recorded native moment array.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import time

from certify_h9_interior_edge_crossing import (
    archival_data, exact_line_witness, qvec, SOURCE_IDS, DESIGN_IDS,
    need,
)

INTEGER = re.compile(r"-?(?:0b[01]+|[0-9]+)\Z")
DENOMINATOR = re.compile(r"(?:0b[01]+|[0-9]+)\Z")
MOMENT_PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))


def exact_token(token):
    """Lossless integer/binary rational grammar as emitted by pinned Cherchi."""
    need(isinstance(token, str), "NON_STRING_RATIONAL_TOKEN")
    parts=token.split('/')
    need(len(parts)==2 and INTEGER.fullmatch(parts[0]) is not None
         and DENOMINATOR.fullmatch(parts[1]) is not None,
         "INVALID_CHERCHI_RATIONAL_TOKEN")
    def parse(s):
        negative=s.startswith('-')
        digits=s[1:] if negative else s
        if digits.startswith('0b'):
            n=int(digits[2:],2)
        else:
            n=int(digits,10)
        return -n if negative else n
    n,d=parse(parts[0]),parse(parts[1])
    need(d>0,"NONPOSITIVE_CHERCHI_DENOMINATOR")
    return Fraction(n,d)


def exact_ten_moments(coords, triangles):
    """Independent, exact (V,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY) integration."""
    vertices=[tuple(exact_token(t) for t in v) for v in coords]
    output=[Fraction(0)]*10
    n=len(vertices)
    for face in triangles:
        need(len(face)==3 and all(type(i) is int and 0<=i<n for i in face)
             and len(set(face))==3, "INVALID_RATIONAL_FACE")
        a,b,c=[vertices[i] for i in face]
        det=(a[0]*(b[1]*c[2]-b[2]*c[1])+
             a[1]*(b[2]*c[0]-b[0]*c[2])+
             a[2]*(b[0]*c[1]-b[1]*c[0]))
        if det==0:continue
        output[0]+=det/6
        sm=[a[i]+b[i]+c[i] for i in range(3)]
        for i in range(3): output[i+1]+=det*sm[i]/24
        for k,(i,j) in enumerate(MOMENT_PAIRS):
            diag=a[i]*a[j]+b[i]*b[j]+c[i]*c[j]
            output[k+4]+=det*(sm[i]*sm[j]+diag)/120
    return tuple(output)


def oriented_edge_audit(triangles, vertex_count):
    """Independent combinatorial manifold+orientation, not CGAL self intersection."""
    counter=Counter()
    for face in triangles:
        need(len(face)==3 and all(type(i) is int and 0<=i<vertex_count for i in face)
             and len(set(face))==3,"NON_TRIANGLE_FACE_OR_REPEATED_VERTEX")
        a,b,c=face
        for edge in ((a,b),(b,c),(c,a)):
            counter[edge]+=1
    undirected={tuple(sorted(key)) for key in counter}
    wrong=[edge for edge in undirected if counter[edge]!=1 or counter[edge[::-1]]!=1]
    need(not wrong, "NON_MANIFOLD_OR_INCONSISTENT_ORIENTED_EDGE_CHAIN")
    return {'manifold_edges_checked':len(undirected),
            'triangle_count':len(triangles),
            'oriented_edge_pair_multiplicity_one':True,
            'global_self_intersection_checked':False}


def check_mass_snapshot(material, expected_moments, expected_native_moments):
    start=time.perf_counter()
    rational=material['variable_rational_vertices']
    faces=material['variable_faces']
    structure=oriented_edge_audit(faces,len(rational))
    exact=exact_ten_moments(rational,faces)
    need(exact[0]>0,'EXACT_ORIENTED_MASS_NOT_POSITIVE')
    normalized=[float(x) for x in exact]
    need(len(expected_moments)==10 and len(expected_native_moments)==10 and
         all(math.isfinite(x) for x in expected_moments+expected_native_moments),
         'UNTRUSTWORTHY_RECORDED_MOMENT_VECTOR')
    def scaled_error(v):
        return max(abs(float(exact[j])-v[j])/max(1.,abs(v[j])) for j in range(10))
    err=scaled_error(expected_moments)
    native_err=scaled_error(expected_native_moments)
    need(err<=1e-10 and native_err<=1e-10, 'EXACT_FRACTION_MOMENTS_DISAGREE_WITH_ARCHIVED_NATIVE')
    return {'exact_rational_volume':str(exact[0]),
            'raw_ten_moments_from_independent_fraction':normalized,
            'max_scaled_error_vs_archived_independent':err,
            'max_scaled_error_vs_archived_production':native_err,
            'edge_structure':structure,
            'wall_seconds':time.perf_counter()-start}


def historical_replay(zip_path):
    req,report,points=archival_data(Path(zip_path))
    design=[qvec(req['request']['design_vertices'][i]) for i in DESIGN_IDS]
    results={}
    for i in (59,60):
        point,material=points[i]
        result=check_mass_snapshot(material,point['independent_variable_raw_moments'],
                                   point['production_variable_raw_moments'])
        source=[qvec(material['quadric_source_vertices'][j]) for j in SOURCE_IDS]
        edges=exact_line_witness(*source,*design)
        need(0<edges['source_segment_parameter']<1 and
             0<edges['design_segment_parameter']<1,
             f'ARCHIVED_SOURCE_DESIGN_EDGES_NOT_INTERIOR_{i}')
        need((edges['determinant']>0)-(edges['determinant']<0)==(1 if i==59 else -1),
             f'ARCHIVED_EDGE_ORIENTATION_SIGN_DRIFT_{i}')
        result.update({'index':i,'c7':point['coefficients'][7],
            'frozen_material_archive_sha256':point['exact_same_call_material_archive_sha256'],
            'semantic_facet_switch_already_archived':i==60,
            'segment_source_parameter_approximate':float(edges['source_segment_parameter']),
            'segment_design_parameter_approximate':float(edges['design_segment_parameter']),
            'edge_event_exact_sign':1 if i==59 else -1})
        results[str(i)]=result
    left,right=(points[i][0] for i in (59,60))
    dx=right['coefficients'][7]-left['coefficients'][7]
    needs=report['analytic_10_by_10_jacobian']
    j7=[row[7] for row in needs]
    finite_secant=[(right['independent_variable_raw_moments'][i]-
                    left['independent_variable_raw_moments'][i])/dx for i in range(10)]
    deviation=max(abs(s-j)/max(1.,abs(j)) for s,j in zip(finite_secant,j7))
    return {'schema':'heart-h9-independent-h8f-endpoints-reintegration-v1',
            'source':'ARCHIVED_REAL_CHERCHI_MATERIAL_REINTEGRATION_NOT_NEW_NATIVE_CALLS',
            'historic_run_id':39123384402,'historic_run_conclusion':'failure',
            'frozen_artifact_zip_sha256':'99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9',
            'reintegrated_real_historical_samples':[59,60],
            'materials':results,
            'left_to_right_ten_moment_finite_secant':finite_secant,
            'baseline_native_analytic_jacobian_column7':j7,
            'max_scaled_secant_difference_vs_base_analytic_jacobian':deviation,
            'new_real_native_calls_this_run':0,
            'continuous_boolean_branch_certified':False,
            'actual_accepted_newton_step':False,'newton_admitted':False,
            'final_heart_obj_produced':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    data=historical_replay(a.artifact)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf8') as f:
        json.dump(data,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')
    print('H9_REINTEGRATED_BOTH_TRUE_ARCHIVED_SIDES_NOT_NEW_NATIVE_CALLS',json.dumps({
      'samples':data['reintegrated_real_historical_samples'],
      'max_scaled_secant_disagreement':data['max_scaled_secant_difference_vs_base_analytic_jacobian'],
      'seconds':{k:v['wall_seconds'] for k,v in data['materials'].items()}},sort_keys=True))

if __name__=='__main__': main()
