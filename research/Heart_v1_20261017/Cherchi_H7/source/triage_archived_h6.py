"""Read archived H6 reports as historical evidence, without re-running native Cherchi."""
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

def summarize(numerical_path,feature_path):
    nb=Path(numerical_path).read_bytes();fb=Path(feature_path).read_bytes()
    n=json.loads(nb);f=json.loads(fb)
    if (n.get('scope')!='ARCHIVED_V4_PROXY_NOT_AUTHORITATIVE_EVAL60_NOT_FORMAL_HEART'
        or f.get('scope')!='HISTORICAL_V4_PROXY_ONLY_NOT_AUTHENTIC_EVAL60'
        or n.get('sample_count')!=25 or f.get('evaluated_points')!=25
        or n.get('columns_evaluated')!=[0,4,8] or f.get('directions')!=[0,4,8]
        or n.get('original_evaluation_60_reproduced') is not False
        or n.get('original_newton_converged') is not False
        or f.get('topology_neighborhood_certified') is not False):
        raise ValueError('NOT_ORIGINAL_H6_V4_PROXY_EVIDENCE')
    if (len(n['evaluated_points'])!=25 or len(f['rows'])!=25
        or len(f['comparisons'])!=24 or len(n['checks'])!=9):
        raise ValueError('INCOMPLETE_H6_EVIDENCE')
    if any(n['evaluated_points'][i]['quadric_coefficients'] != f['rows'][i]['coefficients']
           or n['evaluated_points'][i]['index']!=i or f['rows'][i]['index']!=i
           for i in range(25)):
        raise ValueError('H6_FEATURE_NUMERICAL_Q_MISMATCH')
    counts=Counter(); per_direction={str(i):Counter() for i in (0,4,8)}
    for expected,c in enumerate(f['comparisons'],start=1):
        if c['index']!=expected:raise ValueError('H6_COMPARISON_INDEX_MISMATCH')
        difference=set(c['unequal_fields'])
        if not difference:label='no_digest_change'
        elif 'constructed_vertex_features' in difference:
            label='construction_provenance_digest_change'
        elif difference=={'canonical_triangles'}:
            label='face_connectivity_digest_change_only'
        else:label='unclassified_feature_digest_change'
        counts[label]+=1
        per_direction[str((0,4,8)[(expected-1)//8])][label]+=1
    return dict(schema='heart-h7-archived-h6-hash-triage-v1',
        scope='HISTORICAL_V4_PROXY_ONLY',original_eval60_authenticated=False,
        native_boolean_replayed_this_run=False,
        raw_numerical_sha256=sha256(nb).hexdigest(),
        raw_feature_sha256=sha256(fb).hexdigest(),
        numerical_checks_passed=sum(x['numeric_passed'] is True for x in n['checks']),
        maximum_reported_error=max(x['maximum_relative_error'] for x in n['checks']),
        digest_categories=dict(counts),
        by_direction={k:dict(v) for k,v in per_direction.items()},
        retessellation_exactly_certified_count=0,
        full_neighborhood_smoothness_certified=False,
        next_step='Recompute the exact Cherchi packet and source operands at each q; compare per-q certified plane chains and construction provenance')

def main():
    import argparse
    p=argparse.ArgumentParser()
    h6=Path(__file__).resolve().parents[2]/'Cherchi_H6'/'evidence'
    p.add_argument('--numerical',type=Path,default=h6/'three-column-numerical-report.json')
    p.add_argument('--features',type=Path,default=h6/'three-column-feature-classification.json')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    r=summarize(a.numerical,a.features)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(r,sort_keys=True))

if __name__=='__main__':main()
