"""W0 M16: byte-pinned, read-only W0/W2/W5/W6 consumer interface audit.

No teacher data is imported or released.  W5/W6 source files from their
independent branches are mirrored as historical frozen Git blobs.  The audit
rejects changing those bytes without deliberate review; no live-head claims.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

SOURCE = '0bcc187b3005478baa586a6d6f450e73811ca342'
PINS = {
    'w0_schema': '52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc',
    'w0_validator': 'fe5f71e7cb2b6c6ad45f48c49ab4042f797a113e',
    'w2_manifest': '41e7c4dc65a029a3cc7ce746c694bc8a03cdad70',
    'w5_contract_gate': '14b2ab225a032188fe16570414ef321af9a81e00',
    'w6_teacher_gate': '24dafd66dce83d3076d4133cae8fdeff34671dae',
}
RELATIVE = {
    'w0_schema': 'schema_v1.json',
    'w0_validator': 'validate_contract_v1.py',
    'w2_manifest': 'frozen_external_m16/w2_teacher_manifest.json',
    'w5_contract_gate': 'frozen_external_m16/w5_contract_gate.py',
    'w6_teacher_gate': 'frozen_external_m16/w6_teacher_gate.py',
}

class InterfaceRejected(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise InterfaceRejected(reason)


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def strict_json(raw: bytes):
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            need(k not in obj, 'DUPLICATE_JSON_KEY')
            obj[k] = v
        return obj
    def nonfinite(value):
        raise InterfaceRejected('NONFINITE_JSON')
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    except (UnicodeError, ValueError, TypeError) as exc:
        if isinstance(exc, InterfaceRejected):
            raise
        raise InterfaceRejected('INVALID_JSON') from exc


def source_assignments(data: bytes):
    """Read real Python module constant declarations WITHOUT executing code."""
    try:
        root = ast.parse(data.decode('utf-8'))
    except (UnicodeError, SyntaxError) as exc:
        raise InterfaceRejected('INVALID_FROZEN_PYTHON_SOURCE') from exc
    names = {}
    for node in root.body:
        if isinstance(node, ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant):
                names[node.targets[0].id] = node.value.value
    return root, names


def semantic_review(documents):
    """The semantic review cannot release data, even when given synthetic documents."""
    need(set(documents)==set(PINS), 'MISSING_SOURCE_SLOTS')
    schema = strict_json(documents['w0_schema'])
    manifest = strict_json(documents['w2_manifest'])
    need(schema.get('title')=='MomentContractV1' and
         schema.get('properties',{}).get('source_sha',{}).get('const')==SOURCE and
         schema['properties']['coefficients']['properties']['cross_mapping']['const']==
         'q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2',
         'W0_CONTRACT_SCHEMA_MISMATCH')
    need(manifest.get('schema')=='w2-cherchi-teacher-v2-pre-w0', 'W2_NOT_V2_MANIFEST')
    splits=manifest.get('data_splits')
    need(type(splits) is dict and set(splits)=={'train','val','test','excluded'} and
         all(type(splits[k]) is list for k in splits), 'W2_SPLITS_INCOMPLETE')
    need(not splits['train'] and not splits['val'] and not splits['test'] and
         len(splits['excluded'])==1 and type(splits['excluded'][0].get('count')) is int and
         splits['excluded'][0]['count']==81 and
         splits['excluded'][0].get('derivatives_admitted')==0 and
         type(manifest.get('native_teacher_runs')) is int and manifest['native_teacher_runs']==0 and
         type(manifest.get('training_samples')) is int and manifest['training_samples']==0 and
         manifest['label_convention']['w0_verifier_integrated'] is False,
         'W2_FORMAL_TEACHER_DATA_STILL_NOT_RELEASED')
    w5, w5const=source_assignments(documents['w5_contract_gate'])
    w6, w6const=source_assignments(documents['w6_teacher_gate'])
    need(w5const.get('W2_SCHEMA')=='w2-cherchi-teacher-v1-pre-w0' and
         w5const.get('W0_SCHEMA')=='MomentContractV1' and
         w5const.get('W0_SOURCE_SHA')==SOURCE,
         'W5_CONSUMER_VERSION_OBSERVATION_CHANGED')
    need(w6const.get('KNOWN_PRE_W0_SCHEMA')=='w2-cherchi-teacher-v1-pre-w0',
         'W6_CONSUMER_VERSION_OBSERVATION_CHANGED')
    # Check actual source AST, not prose asserting that an importer is safe.
    w5_fn=next((n for n in w5.body if isinstance(n,ast.FunctionDef) and n.name=='check_w0_contract'),None)
    need(w5_fn is not None, 'W5_CONTRACT_FUNCTION_MISSING')
    w5_norm_tol=[]
    for node in ast.walk(w5_fn):
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='_require'
            and len(node.args)>1 and isinstance(node.args[1],ast.Constant)
            and 'native unit-normalized' in str(node.args[1].value)):
            clause=node.args[0]
            if isinstance(clause,ast.Compare) and len(clause.comparators)==1 and isinstance(clause.comparators[0],ast.Constant):
                w5_norm_tol.append(clause.comparators[0].value)
    need(w5_norm_tol==[1e-9], 'W5_UNIT_C_TOLERANCE_OBSERVATION_CHANGED')
    need(b'<= 1e-12' in documents['w0_validator'], 'W0_UNIT_C_RULE_NOT_PINNED')
    w6_gate=next((n for n in w6.body if isinstance(n,ast.FunctionDef) and n.name=='require_native_teacher'),None)
    need(w6_gate is not None and any(
        isinstance(n,ast.Raise) and isinstance(n.exc,ast.Call) and
        isinstance(n.exc.func,ast.Name) and n.exc.func.id=='TeacherUnavailable'
        for n in ast.walk(w6_gate)), 'W6_FAIL_CLOSED_NATIVE_IMPORTER_CHANGED')
    return {
        'schema':'W0_M16_FROZEN_INTERFACE_AUDIT_V1',
        'w2_manifest_schema':manifest['schema'],
        'w2_archived_excluded':81,
        'w2_formal_teacher_samples':0,
        'w5_legacy_expected_schema':w5const['W2_SCHEMA'],
        'w5_native_unit_tolerance':w5_norm_tol[0],
        'w0_native_unit_tolerance':1e-12,
        'w5_current_v2_schema_compatible':False,
        'w6_v2_native_teacher_admitted':False,
        'blockers':['W5_V1_ONLY_WHILE_W2_V2', 'W5_W0_UNIT_NORM_TOLERANCE_1E9_VS_1E12',
                    'W2_FORMAL_NATIVE_JACOBIAN_NOT_RELEASED',
                    'W0_INDEPENDENT_NATIVE_SEAL_AND_NEWTON_NOT_PRESENT'],
        'historical_h8f_failure_preserved':True,
        'W5_native_training_admitted':False,
        'W6_native_training_admitted':False,
        'training_admissible':False,
    }


def audit_pinned(root: Path | None = None):
    path=Path(root) if root is not None else Path(__file__).resolve().parent
    docs={}
    for name,relative in RELATIVE.items():
        p=path/relative
        need(p.is_file() and not p.is_symlink(), 'MISSING_FROZEN_SOURCE:'+name)
        raw=p.read_bytes()
        need(blob_sha1(raw)==PINS[name], 'SOURCE_GIT_BLOB_DRIFT:'+name)
        docs[name]=raw
    result=semantic_review(docs)
    result['git_blob_sha1_pins']=dict(PINS)
    result['snapshots_frozen_not_current_head_attestation']=True
    return result


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError('DO_NOT_OVERWRITE_W0_M16')
    result=audit_pinned()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write('\n')
    print('W0_M16_INTERFACE_BLOCKED_NO_NATIVE_TRAINING',len(result['blockers']))
    return 0 # CI validates denial: this is NOT teacher release.

if __name__=='__main__':
    raise SystemExit(main())
