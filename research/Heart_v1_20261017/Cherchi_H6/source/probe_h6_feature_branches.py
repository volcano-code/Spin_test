"""Read-only 25-point Cherchi source/provenance branch classifier.

No full moment integration or optimization. Actual native source + Cherchi Boolean
are executed at all q points. A correspondence mismatch is preserved, not
silently renamed to an equivalent triangulation.
"""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from heart_h6_authority import verify_v4_proxy
from heart_h6_cherchi_jacobian import planned_samples

def h(obj):
    return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def packet_features(packet,design,source_vertices,operation):
    # EXACT rational token input vertex matching, matching the production
    # InProcessCherchiEvaluator construction-resolution policy.
    lookup={}
    for object_index,points in enumerate((design,source_vertices)):
        for idx,p in enumerate(points):
            key=tuple(Fraction(float(x)) for x in p)
            lookup.setdefault(key,[]).append((object_index,idx))
    features=[];classification=Counter()
    for rec in packet['construction_records']:
        kind=rec['point_type'];loc=[]
        for item in rec['operand_coordinates_exact']:
            key=tuple(Fraction(x) for x in item)
            possible=lookup.get(key,[])
            if len(possible)!=1:
                classification['AMBIGUOUS_OR_UNMATCHED']+=1
                loc.append(('UNRESOLVED',len(possible)))
            else:loc.append(possible[0])
        label=(kind,tuple(loc))
        features.append(h(label));classification[kind]+=1
    oriented=Counter()
    for face in packet['faces']:
        keys=[features[int(i)] for i in face]
        oriented[min(tuple(keys),tuple(keys[1:]+keys[:1]),tuple(keys[2:]+keys[:2]))]+=1
    return dict(type_counts=dict(classification),
        canonical_triangles=h(sorted(oriented.items())),
        constructed_vertex_features=h(sorted(features)),
        geometric_faces=len(packet['faces']),geometric_vertices=len(packet['vertices']),
        input_operation=operation)

def run(frozen,registration,directions,output):
    import _make_it_stand as native
    import _cherchi_core_boolean as cherchi
    doc,reg=verify_v4_proxy(frozen,registration)
    raw=doc['requests'][1]['request'];config=doc['evaluator_settings']
    q=np.asarray(reg['event']['quadric_coefficients'],dtype=float)
    origin=np.asarray(raw['target_origin'],dtype=float);axes=np.asarray(raw['target_axes'],dtype=float)
    design=np.asarray(raw['design_vertices'],dtype=float)
    target_design=(design-origin)@axes.T
    faces=np.asarray(raw['design_faces'],dtype=np.int32)
    settings=native.SpinTriangulationSettings()
    for key in ('icosphere_subdivisions','maximum_radius_doublings','truncation_radius','algebraic_finite_map'):
        setattr(settings,key,config[key])
    settings.maximum_icosphere_subdivisions=settings.icosphere_subdivisions
    settings.retain_fixed_normal_provenance=True
    settings.paper_projective_hyperboloid=True
    samples,layouts=planned_samples(q,directions)
    expected='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1'
    rows=[]
    for index,at in enumerate(samples):
        source=native.evaluate_spin_it_faster_source_motion(at,target_design,settings)
        if not source['defined'] or not source['side_selection_defined']:
            raise ValueError('SOURCE_NOT_DEFINED_AT_'+str(index)+':'+source['diagnostic'])
        sv=np.asarray(source['vertices'])@axes.T+origin
        sf=np.asarray(source['faces'],dtype=np.int32)
        operation='intersection' if source['interior_is_positive'] else 'difference'
        packet=cherchi.boolean(design.tolist(),faces.tolist(),sv.tolist(),sf.tolist(),operation)
        if packet.get('backend')!=expected:raise ValueError('CHERCHI_BACKEND_MISMATCH_NO_FALLBACK')
        f=packet_features(packet,design,sv,operation)
        source_sig={
            'source_faces':h(sf.tolist()),
            'source_normal_edges':h(np.asarray(source['source_normal_edges']).tolist()),
            'source_normal_vertices':h(np.asarray(source['source_normal_vertices']).tolist()),
            'source_projective_rays':h(source['source_projective_rays']),
            'source_face_caps':h(np.asarray(source['face_is_cap']).tolist()),
            'source_surface_type':str(source['surface_type']),
            'source_radius':float(source['truncation_radius']),
            'source_vertices':len(sv),'source_faces_count':len(sf),
        }
        rows.append({'index':index,'coefficients':at.tolist(),**source_sig,**f})
        print('BRANCH',index,'/',len(samples)-1,'cherchi faces=',f['geometric_faces'],flush=True)
    base=rows[0]
    comparison=[]
    keys=[k for k in base if k not in ('index','coefficients')]
    for row in rows[1:]:
        unequal={k:{'base':base[k],'perturbed':row[k]} for k in keys if base[k]!=row[k]}
        comparison.append(dict(index=row['index'],unequal_fields=unequal,actual_geometric_topology_stable='canonical_triangles' not in unequal and 'geometric_faces' not in unequal and 'geometric_vertices' not in unequal))
    summary=Counter(k for c in comparison for k in c['unequal_fields'])
    out={'schema':'heart-h6-cherchi-v4-proxy-feature-branches-v1',
        'scope':'HISTORICAL_V4_PROXY_ONLY_NOT_AUTHENTIC_EVAL60',
        'input_sha256':sha256(Path(frozen).read_bytes()).hexdigest(),
        'registration_sha256':sha256(Path(registration).read_bytes()).hexdigest(),
        'evaluated_points':len(samples),'directions':directions,
        'any_change_count':sum(bool(c['unequal_fields']) for c in comparison),
        'feature_changes_by_type':dict(summary),
        'verified_original_eval60':False,
        'topology_neighborhood_certified':False,
        'rows':rows,'comparisons':comparison}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print('FEATURE_DIAGNOSTIC',json.dumps({k:out[k] for k in ('evaluated_points','any_change_count','feature_changes_by_type')}),flush=True)
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--archived-v4',type=Path,required=True)
    parser.add_argument('--registered-q',type=Path,required=True)
    parser.add_argument('--directions',default='0,4,8')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();dirs=[int(x) for x in args.directions.split(',')]
    run(args.archived_v4,args.registered_q,dirs,args.output)
