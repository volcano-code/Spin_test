#!/usr/bin/env python3
"""W4 P16: exact IEEE-754 rational chain/moment replay on real P14/P15 OBJ.

Crucial distinction: exact moments of *serialized binary64* triangular
surfaces != proof of equality to native Cherchi implicit rational geometry.
A true nonzero exact source-vs-microweld signed volume disproves strict
set equality of these serialized boundary representations. Paired changes
in the outer and F oriented triangular chains cancel as formal chains.

No native Cherchi invocation, geometry substitution, W0 admission or
Spin-It Faster optimization is performed here.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = 'W4P16ExactBinary64OrientedChainAndMomentsV1'
P14_SHA256 = '11485d0659ca9933205179de1c968f42e7c27dfaf0ca77a8c28c96125b60ad72'
P15_SHA256 = '0e2d48e40efe5110512b3929a3b90718e1b65b5382a11494e5d6bba473193a56'
CHERCHI_COMMIT = '7bd6c2697695f555f9a15d7e154e084d841316f0'
P15_COMMIT = 'ac03b316d2e49cee585d762cf80d11633d03c2a1'
NAMES = ('M', 'LX', 'LY', 'LZ', 'QXX', 'QYY', 'QZZ', 'QYZ', 'QXZ', 'QXY')
CASES = ('rotate_1p5','translate_y_008','translate_xy_012_m008')
OUTER_DIR = 'p13-native-Cherchi-domain'
P14_DIR = 'p14-cherchi-junction-study'


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_obj_binary64(path: Path):
    """Independent strict OBJ parser; vertices are exactly IEEE-754 binary64.

    Fraction.from_float supplies the exact underlying binary rational.
    The parser never welds, reindexes, or computes a mesh Boolean.
    """
    vv,ff = [],[]
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        cells=raw.split()
        if not cells or cells[0].startswith('#'):
            continue
        if cells[0]=='v':
            if len(cells)!=4:raise ValueError('OBJ_VERTEX_COUNT_NOT_THREE')
            xyz=tuple(float(c) for c in cells[1:4])
            if not all(math.isfinite(x) for x in xyz):
                raise ValueError('OBJ_NONFINITE_VERTEX')
            vv.append(tuple(0.0 if x==0.0 else x for x in xyz))
        elif cells[0]=='f':
            if len(cells)!=4:raise ValueError('OBJ_ONLY_TRIANGLES_ALLOWED')
            face=[]
            for item in cells[1:4]:
                token=item.split('/')[0]
                if not token or not token.isdecimal() or int(token)<1:
                    raise ValueError('OBJ_FACE_INDEX_INVALID')
                face.append(int(token)-1)
            if len(set(face))<3:raise ValueError('OBJ_FACE_HAS_DUPLICATE_INDEX')
            ff.append(tuple(face))
    if not vv or not ff or max(max(f) for f in ff)>=len(vv):
        raise ValueError('OBJ_EMPTY_OR_OUT_OF_BOUNDS')
    return vv,ff


def exact_ten(vertices,faces)->tuple[Fraction,...]:
    """Compute all 10 signed tetrahedral raw moments as exact Fractions."""
    v=[tuple(Fraction.from_float(x) for x in point) for point in vertices]
    zero=Fraction(0);m=zero;L=[zero,zero,zero]
    Q=[[zero,zero,zero],[zero,zero,zero],[zero,zero,zero]]
    for ia,ib,ic in faces:
        a,b,c=v[ia],v[ib],v[ic]
        det=(a[0]*(b[1]*c[2]-b[2]*c[1])+
             a[1]*(b[2]*c[0]-b[0]*c[2])+
             a[2]*(b[0]*c[1]-b[1]*c[0]))
        w=det/6;m+=w
        s=tuple(a[k]+b[k]+c[k] for k in range(3))
        for i in range(3):L[i]+=w*s[i]/4
        for i in range(3):
            for j in range(i,3):
                Q[i][j]+=w*(s[i]*s[j]+a[i]*a[j]+b[i]*b[j]+c[i]*c[j])/20
    return (m,*L,Q[0][0],Q[1][1],Q[2][2],Q[1][2],Q[0][2],Q[0][1])


def oriented_counter(vertices,faces)->Counter:
    """Formal oriented triangle chain, equivalent only under cyclic rotation.

    Exact vertices are binary64 hexadecimal triples. Different triangulations
    require common refinement before implying equality of geometric sets.
    """
    refs=[tuple(float(x).hex() for x in pt) for pt in vertices]
    out=Counter()
    for a,b,c in faces:
        tri=(refs[a],refs[b],refs[c])
        key=min(tri,tri[1:]+tri[:1],tri[2:]+tri[:2])
        out[key]+=1
    return out


def chain_difference(*terms:tuple[int,Counter])->dict:
    d=Counter()
    for sign,c in terms:
        for k,n in c.items():d[k]+=sign*n
    return {k:n for k,n in d.items() if n}


def eq_frac_payload(value:Fraction)->dict[str,Any]:
    return dict(numerator=str(value.numerator),denominator=str(value.denominator),
                decimal_projection=float(value),is_zero=not bool(value))


def check_sources(p14:Path,p15:Path):
    p14,p15=Path(p14),Path(p15)
    p14log=p14/P14_DIR/'p14-junction-native-study.json'
    p15log=p15/'p15-inherited-sliver-study.json'
    if sha(p14log)!=P14_SHA256 or sha(p15log)!=P15_SHA256:
        raise ValueError('FROZEN_P14_OR_P15_ACTUAL_REPORT_DIGEST_MISMATCH')
    s14=json.loads(p14log.read_text());s15=json.loads(p15log.read_text())
    if (s14.get('schema')!='W4P14CherchiShaftCavityJunctionStudyV1' or
        s14.get('status')!='COMPLETED_NEGATIVE_NATIVE_JUNCTION_STUDY' or
        s14.get('admissible_candidate') is not None or
        s14.get('real_D_native_trials')!=11 or
        s14.get('W0_approved') is not False):
        raise ValueError('P14_HISTORICAL_NATIVE_NEGATIVE_STATUS_CHANGED')
    if (s15.get('schema')!='W4P15InheritedNativeSliverRepairV1' or
        s15.get('status')!='FLOAT64_MICROWELD_CANDIDATE_AVAILABLE_NOT_EXACT_CHERCHI' or
        s15.get('source_P14_report_sha256')!=P14_SHA256 or
        s15.get('native_source_commit')!=CHERCHI_COMMIT or
        s15.get('selected')!=CASES[0] or
        s15.get('exact_Cherchi_implicit_geometry_certified') is not False or
        s15.get('W0_physical_tip_or_FD_approved') is not False or
        s15.get('SpinIt_Faster_optimization_executed') is not False):
        raise ValueError('P15_NUMERIC_POSTPROCESS_CLAIMS_MODIFIED')
    old=p14/OUTER_DIR/'p13-outer-cherchi-union.obj'
    new=p15/'outer_numeric_microweld.obj'
    if (sha(old)!=s15['original_Cherchi_outer_sha256'] or
        sha(new)!=s15['outer_cleaned_sha256'] or
        s14['source_sha256']['outer']!=sha(old)):
        raise ValueError('NATIVE_OR_CLEANED_OUTER_ORIGIN_UNTRUSTED')
    if (s15['outer_micro_weld']['merged_near_vertex_pairs']!=14 or
        s15['outer_micro_weld']['removed_exact_sliver_faces']!=28 or
        s15['outer_micro_weld']['maximum_vertex_representative_displacement']>=1e-15):
        raise ValueError('P15_CHANGE_BUDGET_UNEXPECTED')
    byname={c['name']:c for c in s15['cases']}
    if set(byname)!=set(CASES):
        raise ValueError('P15_CANDIDATE_NAMES_CHANGED')
    srcs={}
    for name in CASES:
        case=byname[name]
        nativeF=p14/P14_DIR/name/'F_retained_cherchi.obj'
        nativeD=p14/P14_DIR/name/'D_minus_shaft_cherchi.obj'
        cleanF=p15/name/'F_numeric_microweld.obj'
        if (case['status']!='FLOAT_MESH_POSTPROCESS_CONDITIONAL_PASS_NOT_NATIVE_EXACT' or
            case['F_original_native_sha256']!=sha(nativeF) or
            case['D_original_native_sha256']!=sha(nativeD) or
            case['F_postprocessed_sha256']!=sha(cleanF) or
            case['F_postprocess']['merged_near_vertex_pairs']!=14 or
            case['F_postprocess']['removed_exact_sliver_faces']!=28 or
            case['F_postprocess']['maximum_vertex_representative_displacement']>=1e-15):
            raise ValueError('P15_NATIVE_CASE_OR_FILE_SHA_INVALID_'+name)
        same_call=json.loads(Path(str(nativeF)+'.native.json').read_text())
        if (same_call.get('returncode')!=0 or same_call.get('output_sha256')!=sha(nativeF) or
            same_call.get('source_sha256',[None,None])[1]!=sha(nativeD)):
            raise ValueError('P14_NATIVE_F_SAME_CALL_PROVENANCE_MISMATCH_'+name)
        srcs[name]=dict(nativeF=nativeF,nativeD=nativeD,cleanF=cleanF)
    return old,new,srcs


def analyze(p14:Path,p15:Path,output:Path):
    originalM,cleanM,sources=check_sources(p14,p15)
    oldv,oldf=read_obj_binary64(originalM)
    newv,newf=read_obj_binary64(cleanM)
    old_chain=oriented_counter(oldv,oldf)
    new_chain=oriented_counter(newv,newf)
    delta_chain=chain_difference((1,old_chain),(-1,new_chain))
    if not delta_chain:
        raise ValueError('P15_ORIENTED_OUTER_CHANGE_UNEXPECTEDLY_ZERO')
    old10=exact_ten(oldv,oldf);new10=exact_ten(newv,newf)
    exact_delta=tuple(a-b for a,b in zip(old10,new10))
    if not exact_delta[0]:
        raise ValueError('EXPECTED_SERIALIZED_FLOAT_EXACT_NONIDENTITY_NOT_FOUND')
    if max(abs(float(x)) for x in exact_delta)>=1e-12:
        raise ValueError('NUMERIC_BOUNDARY_CHANGE_NOT_SMALL')
    report=dict(schema=SCHEMA,
        status='EXACT_BINARY64_MOMENT_CANCELLATION_WITH_STRICT_SURFACE_NONIDENTITY',
        source_P14_run=39462578208,source_P15_run=39555122736,
        native_reference_Cherchi_commit=CHERCHI_COMMIT,P15_source_commit=P15_COMMIT,
        source_P14_sha256=P14_SHA256,source_P15_sha256=P15_SHA256,
        original_M_sha256=sha(originalM),cleaned_M_sha256=sha(cleanM),
        arithmetic='EXACT_FRACTION_OF_SAVED_IEEE754_BINARY64_VERTICES',
        polynomial_basis=list(NAMES),
        vertex_coordinates_not_original_implicit_rationals=True,
        exact_implicit_Cherchi_surface_certified=False,
        full_set_equality_original_vs_microweld=False,
        exact_saved_binary64_outer_volume_difference=eq_frac_payload(exact_delta[0]),
        exact_saved_binary64_outer_moment_delta={k:eq_frac_payload(v) for k,v in zip(NAMES,exact_delta)},
        native_outer_face_count=len(oldf),cleaned_outer_face_count=len(newf),
        signed_oriented_chain_change_term_count=len(delta_chain),
        signed_chain_face_difference_preserved_for_all_three=True,
        exact_original_F_plus_D_moments_equal_outer=True,
        exact_cleaned_F_plus_D_moments_equal_cleaned_outer=True,
        native_original_P14_remains_rejected=True,cases=[],
        native_implicit_point_exact_identity_certified=False,
        W0_physical_tip_or_FD_approved=False,W2_teacher_training_allowed=False,
        Faster_optimization_executed=False,MuJoCo_real_optimized_before_after_executed=False)
    for name in CASES:
        items=sources[name]
        fv,ff=read_obj_binary64(items['nativeF'])
        gv,gf=read_obj_binary64(items['cleanF'])
        dv,df=read_obj_binary64(items['nativeD'])
        oldF=exact_ten(fv,ff);newF=exact_ten(gv,gf);d10=exact_ten(dv,df)
        deltaF=tuple(a-b for a,b in zip(oldF,newF))
        native_r=tuple(a-b-c for a,b,c in zip(old10,oldF,d10))
        welded_r=tuple(a-b-c for a,b,c in zip(new10,newF,d10))
        diff_M_F=tuple(a-b for a,b in zip(exact_delta,deltaF))
        if any(native_r) or any(welded_r) or any(diff_M_F):
            raise ValueError('EXACT_SIGNED_TEN_MOMENT_ADDITIVITY_OR_PAIR_DELTA_FAILED_'+name)
        chainF=oriented_counter(fv,ff)
        chainCleanF=oriented_counter(gv,gf)
        delta_equal=not chain_difference((1,old_chain),(-1,new_chain),(-1,chainF),(1,chainCleanF))
        if not delta_equal:
            raise ValueError('EXACT_ORIENTED_CHAIN_MICROWELD_DELTA_MISMATCH_'+name)
        chainD=oriented_counter(dv,df)
        native_chain_residual=chain_difference((1,old_chain),(-1,chainF),(-1,chainD))
        welded_chain_residual=chain_difference((1,new_chain),(-1,chainCleanF),(-1,chainD))
        if native_chain_residual!=welded_chain_residual:
            raise ValueError('P16_CHAIN_RESIDUAL_CHANGED_BY_MICROWELD_'+name)
        report['cases'].append(dict(name=name,
            source_F_sha256=sha(items['nativeF']),source_D_sha256=sha(items['nativeD']),
            cleaned_F_sha256=sha(items['cleanF']),
            native_F_faces=len(ff),cleaned_F_faces=len(gf),D_faces=len(df),
            exact_oriented_chain_change_identical_for_M_and_F=True,
            exact_original_signed_tetra_ten_moment_residual_all_zero=True,
            exact_cleaned_signed_tetra_ten_moment_residual_all_zero=True,
            exact_outer_delta_equals_retained_F_delta_all_ten=True,
            exact_native_volume_delta=eq_frac_payload(deltaF[0]),
            saved_triangle_chain_residual_terms_native=len(native_chain_residual),
            saved_triangle_chain_residual_terms_cleaned=len(welded_chain_residual),
            boundary_chain_residual_is_nonzero=bool(native_chain_residual),
            exact_implicit_boolean_proved=False,author_original_CAD_proved=False))
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--p14-root',required=True,type=Path)
    p.add_argument('--p15-root',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    r=analyze(a.p14_root,a.p15_root,a.out)
    print(json.dumps(dict(status=r['status'],
        original_vs_cleaned_exact_volume_delta=r['exact_saved_binary64_outer_volume_difference'],
        cases=[dict(name=k['name'],exact_signed_ten=True,
                    oriented_chain_delta=True,
                    native_chain_residual_terms=k['saved_triangle_chain_residual_terms_native'])
               for k in r['cases']],
        W0_approved=r['W0_physical_tip_or_FD_approved']),indent=2))


if __name__=='__main__':
    main()
