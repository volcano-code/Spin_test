"""Reconstruct the original Noodles V7 92-union + 4-final-CGAL Boolean DAG.

This is a source-locked EXECUTION PLAN, not evidence of new CGAL calls.
A plan alone does not grant Boolean-material correctness or teacher admission.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
try:
    from . import m19_noodles_fda_audit as m19
except ImportError:
    import m19_noodles_fda_audit as m19


def plan(source_bundle):
    with ZipFile(source_bundle) as z:
        source=m19.pinned_json(m19.zip_member(z,m19.BUNDLE_MANIFEST),
            m19.SOURCE_MANIFEST_SHA256,m19.SOURCE_MANIFEST_GIT_BLOB,'ORIGINAL_MANIFEST')
        receipt=m19.pinned_json(m19.zip_member(z,m19.BUNDLE_CSG_RECEIPT),
            m19.CSG_RECEIPT_SHA256,m19.CSG_RECEIPT_GIT_BLOB,'ORIGINAL_CSG_RECEIPT')
    parts=source['parts'];names=source['construction']['fixed_parts']
    m19.require(len(parts)==94 and len(names)==93 and
                len(set(names))==93 and set(names)==set(parts)-{'outer-ellipsoid'},
                'WRONG_FROZEN_94_PART_RECIPE')
    m19.require(m19._digest_corpus(parts)==m19.CORPUS_DIGEST_188,
                'FROZEN_PART_IDENTITY_DRIFT')
    m19.require(receipt['backend_sha']==m19.HISTORIC_CSG_BACKEND_SHA256 and
                receipt['manifest_sha']==m19.SOURCE_MANIFEST_SHA256 and
                receipt['csg_executed_current_process']==96 and
                receipt['independent_partition_verified'] is False,
                'HISTORICAL_BACKEND_OR_CSG_RECEIPT_UNBOUND')
    leaves={n:{'model_obj':'OBJ/'+p['model_obj'],'model_sha256':p['sha256_model'],
               'expected_source_faces':p['audit']['triangles']} for n,p in parts.items()}
    steps=[];nodes=list(names);r=0
    while len(nodes)>1:
        next_nodes=[]
        for j in range(0,len(nodes),2):
            if j+1>=len(nodes):next_nodes.append(nodes[j]);continue
            a,b=nodes[j:j+2]
            target=f'fixed-union-level{r:02d}-pair{j//2:03d}.json'
            steps.append(dict(index=len(steps),kind='union',left=a,right=b,
                              output=target,role='fixed_union_intermediate'))
            next_nodes.append(f'({a}+{b})')
        nodes=next_nodes;r+=1
    fixed_root=nodes[0]
    envelope='outer-ellipsoid'
    for label,left,right,op in (
        ('design',envelope,fixed_root,'difference'),
        ('initial',envelope,fixed_root,'union'),
        ('fixed-inside-envelope',envelope,fixed_root,'intersection'),
        ('fixed-outside-envelope',fixed_root,envelope,'difference')):
        steps.append(dict(index=len(steps),kind=op,left=left,right=right,
                          output=label+'-rational.json',role='final_CSG_packet'))
    m19.require(len(steps)==96 and
                sum(s['role']=='fixed_union_intermediate' for s in steps)==92 and
                sum(s['role']=='final_CSG_packet' for s in steps)==4,
                'HISTORICAL_BOOLEAN_DAG_COUNT_DRIFT')
    expected=receipt['outputs']
    m19.require(set(expected)==set(m19.PACKETS), 'HISTORICAL_PACKET_SET_DRIFT')
    return {
        'schema':'w2-m20-frozen-noodles-historical-exact-boolean-dag-v1',
        'status':'READY_AS_SOURCE_LOCKED_PLAN_NOT_EXECUTED',
        'source_manifest_sha256':m19.SOURCE_MANIFEST_SHA256,
        'source_corpus_188_digest':m19.CORPUS_DIGEST_188,
        'historic_receipt_sha256':m19.CSG_RECEIPT_SHA256,
        'historical_backend_sha256':m19.HISTORIC_CSG_BACKEND_SHA256,
        'input_parts_total':94,'fixed_source_parts':93,
        'expected_exact_backend_operations':96,
        'fixed_union_operations':92,'final_CSG_operations':4,
        'fixed_unioned_expression':fixed_root,
        'leaf_sources':leaves,
        'ordered_operations':steps,
        'expected_historical_outputs':{k:dict(sha256=v['sha'],
                      triangles=v['faces']) for k,v in expected.items()},
        'protocol_of_original_CGAL_binary_available':False,
        'all_original_six_CSG_output_bytes_present':False,
        'current_native_operations':0,'new_cherchi_calls':0,
        'jacobian_J_D':None,'training_admitted':0,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-bundle',required=True)
    parser.add_argument('--output',required=True)
    a=parser.parse_args(argv)
    rec=plan(a.source_bundle)
    m19._atomic_exclusive_json(a.output,rec)
    print(json.dumps({'steps':96,'fixed_union':92,'final_boolean':4,
       'new_native_operations':0,'training_admitted':0},sort_keys=True))
    return 0  # Planning success, not native CSG success.
if __name__=='__main__':raise SystemExit(main())
