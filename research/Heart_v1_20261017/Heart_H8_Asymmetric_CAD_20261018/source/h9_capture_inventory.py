"""Read-only forensic inventory of partial H9 Cherchi side checkpoints.

Every input q is derived from the SHA-pinned H8f archive and independently
recomputed conditional event certificate BEFORE any side file is inspected.

This program NEVER replays/claims a fresh native call, never upgrades an
unverified packet, never certifies a smooth stratum or admits Newton. A
structurally complete gzip + JSON is not cryptographic runtime attestation.
"""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import zipfile
import zlib

from h9_frozen_input_gate import validate_pair
from h9_same_call_capture import SIDES, BACKEND

MAX_COMPRESSED = 32 * 1024**2
MAX_DECOMPRESSED = 512 * 1024**2
MAX_METADATA = 2 * 1024**2


class InventoryRejected(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise InventoryRejected(reason)


def sha_bytes(data):
    return sha256(data).hexdigest()


def unique_pairs(pairs):
    doc = {}
    for key, value in pairs:
        require(key not in doc, 'DUPLICATE_FORENSIC_JSON_KEY:'+key)
        doc[key] = value
    return doc


def invalid_float(value):
    raise InventoryRejected('NONFINITE_FORENSIC_JSON:'+value)


def decode(data):
    try:
        return json.loads(data, object_pairs_hook=unique_pairs,
                          parse_constant=invalid_float)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InventoryRejected('INVALID_FORENSIC_JSON') from exc


def regular_path(path):
    """Never follow symlinks, sockets or substituted nonregular evidence."""
    if not os.path.lexists(path):
        return False
    require(stat.S_ISREG(os.lstat(path).st_mode), 'NONREGULAR_OR_SYMLINK_CHECKPOINT:'+path.name)
    return True


def evidence_json(path):
    require(regular_path(path), 'CHECKPOINT_META_ABSENT:'+path.name)
    require(0 < path.stat().st_size <= MAX_METADATA, 'CHECKPOINT_META_OVERSIZE:'+path.name)
    result = decode(path.read_bytes())
    require(type(result) is dict, 'FORENSIC_METADATA_NOT_OBJECT')
    return result


def material_gzip(path):
    require(regular_path(path), 'CHECKPOINT_GZIP_ABSENT:'+path.name)
    require(0 < path.stat().st_size <= MAX_COMPRESSED, 'CHECKPOINT_GZIP_OVERSIZE:'+path.name)
    data = bytearray()
    try:
        with gzip.open(path, 'rb') as stream:
            while True:
                block = stream.read(1 << 20)
                if not block:
                    break
                require(len(data)+len(block) <= MAX_DECOMPRESSED,
                        'CHECKPOINT_GZIP_EXPANSION_TOO_LARGE')
                data.extend(block)
    except (EOFError, OSError, zlib.error) as exc:
        raise InventoryRejected('CHECKPOINT_GZIP_CORRUPTED') from exc
    result = decode(bytes(data))
    require(type(result) is dict, 'CHECKPOINT_MATERIAL_NOT_OBJECT')
    return result, sha_bytes(path.read_bytes()), sha_bytes(data)


def expected_q(base_q, plan_item):
    require(type(base_q) is list and len(base_q) == 10,
            'FROZEN_Q_SHAPE_DRIFT')
    q = list(base_q)
    q[7] = plan_item['c7']
    return q


def material_identity(material, q):
    require(material.get('quadric_coefficients') == q,
            'CHECKPOINT_CROSS_COEFFICIENT_OR_NONFROZEN_Q')
    require(type(material.get('boolean_backend_identity')) is str and
            material['boolean_backend_identity'].startswith(BACKEND) and
            material.get('material_proof', {}).get('schema') == 'cherchi-same-call-material-v1',
            'CHECKPOINT_NOT_DECLARED_CHERCHI_SAME_CALL')
    require(type(material.get('variable_faces')) is list and
            type(material.get('variable_rational_vertices')) is list and
            len(material['variable_faces']) > 3 and
            len(material['variable_rational_vertices']) > 3,
            'CHECKPOINT_GEOMETRY_OR_CONSTRUCTION_INCOMPLETE')


def inspect_side(native_dir, item, base_q):
    index, side = item['index'], item['side']
    identity = f'{index:02d}-{side}'
    unverified = Path(native_dir) / f'unverified-{identity}.json.gz'
    unverified_meta = Path(native_dir) / f'unverified-{identity}.json'
    promoted = Path(native_dir) / f'side-{identity}.json.gz'
    promoted_meta = Path(native_dir) / f'side-{identity}.json'
    paths = (unverified, unverified_meta, promoted, promoted_meta)
    present = [regular_path(x) for x in paths]
    row = {'index':index, 'side':side, 'planned_c7':item['c7'],
           'evidence_paths_present':[x.name for x,p in zip(paths,present) if p],
           'native_runtime_attested':False, 'accepted_newton_step_observed':False,
           'qualified_smooth_neighborhood':False}
    if not any(present):
        row['state']='NO_SIDE_PACKET_CAPTURED'
        return row
    q=expected_q(base_q,item)
    # Incomplete pair remains forensic material only. No proof of native origin.
    if present[0] and present[1]:
        proof=evidence_json(unverified_meta)
        mat, zipped_sha, json_sha=material_gzip(unverified)
        require(proof.get('schema')=='heart-h9-unverified-same-call-checkpoint-v1'
                and proof.get('index')==index and proof.get('side')==side
                and proof.get('coefficients')==q
                and proof.get('archive_sha256')==zipped_sha
                and proof.get('material_json_sha256')==json_sha
                and proof.get('backend_identity')==mat.get('boolean_backend_identity')
                and proof.get('strict_native_boundary_certified') is False
                and proof.get('independent_fraction_moments_certified') is False
                and proof.get('newton_admitted') is False,
                'UNVERIFIED_FORENSIC_CAPTURE_IDENTITY_OR_SHA_DRIFT')
        material_identity(mat,q)
        row['unverified_material_sha256']=zipped_sha
        row['unverified_checkpoint_schema_verified']=True
    elif present[0] or present[1]:
        row['state']='PARTIAL_UNVERIFIED_CHECKPOINT_NOT_QUALIFIED'
    if present[2] and present[3]:
        meta=evidence_json(promoted_meta)
        mat, zipped_sha, _=material_gzip(promoted)
        material_identity(mat,q)
        require(meta.get('index')==index and meta.get('side')==side
                and meta.get('q')==q and meta.get('c7')==item['c7']
                and meta.get('material_sha256')==zipped_sha
                and meta.get('native_geometry_valid') is True
                and meta.get('newton_admitted') is False
                and meta.get('actual_accepted_step') is False,
                'PROMOTED_FORENSIC_PAIR_IDENTITY_OR_SHA_DRIFT')
        if present[0] and present[1]:
            require(row.get('unverified_material_sha256') == zipped_sha,
                    'LEFTOVER_FORENSIC_SOURCE_DIFFERS_FROM_PROMOTED_BYTES')
            # Hard links may disappear after optional cleanup; if still
            # present they MUST resolve to the same immutable inode.
            a,b=os.stat(unverified),os.stat(promoted)
            require((a.st_dev,a.st_ino)==(b.st_dev,b.st_ino),
                    'PROMOTED_FORENSIC_COPY_NOT_SAME_INODE')
        row['state']='COMPLETE_PROMOTED_PAIR_STRUCTURAL_ONLY_NOT_NATIVE_ATTESTED'
        row['promoted_material_sha256']=zipped_sha
    elif present[2] or present[3]:
        row['state']='PARTIAL_PROMOTED_PAIR_NOT_QUALIFIED'
    elif present[0] and present[1]:
        row['state']='COMPLETE_UNVERIFIED_CHECKPOINT_NOT_QUALIFIED'
    return row


def inventory(artifact,certificate,native_dir):
    frozen=validate_pair(artifact,certificate)
    with zipfile.ZipFile(artifact) as z:
        saved=decode(z.read('artifacts/h8f-all81-points/report.json'))
    require(saved.get('completed_samples')==81 and
            saved.get('input_request_sha256')==frozen['frozen_request_sha256'],
            'FROZEN_H8F_REPORT_NOT_BOUND')
    base_q=saved['target_q']
    output={'schema':'heart-h9-partial-native-forensic-inventory-v1',
            'status':'REVIEW_NOT_A_FRESH_CHERCHI_EXECUTION',
            'original_h8f_artifact_sha256':frozen['source_artifact_sha256'],
            'historical_ci_conclusion':'failure',
            'four_planned_side_points':frozen['four_new_native_probe_plan'],
            'side_records':[], 'unverified_complete_checkpoints':0,
            'promoted_complete_structural_pairs':0,
            'new_cherchi_calls_verified_by_this_inventory':0,
            'newton_admitted':False,'accepted_newton_step_observed':False,
            'continuous_smooth_neighborhood_certified':False,
            'final_heart_obj_produced':False}
    if not Path(native_dir).is_dir():
        output['status']='NO_NATIVE_SIDE_DIRECTORY'
        return output
    any_error=False
    for item in frozen['four_new_native_probe_plan']:
        try:
            row=inspect_side(native_dir,item,base_q)
        except (InventoryRejected,OSError,TypeError,KeyError,ValueError) as exc:
            row={'index':item['index'],'side':item['side'],
                 'state':'REJECTED_CHECKPOINT_DO_NOT_RESUME_OR_PUBLISH',
                 'reason':f'{type(exc).__name__}: {exc}',
                 'native_runtime_attested':False}
            any_error=True
        output['side_records'].append(row)
        output['unverified_complete_checkpoints']+=int(
            'unverified_checkpoint_schema_verified' in row)
        output['promoted_complete_structural_pairs']+=int(
            row['state']=='COMPLETE_PROMOTED_PAIR_STRUCTURAL_ONLY_NOT_NATIVE_ATTESTED')
    if any_error:
        output['status']='REJECTED_ONE_OR_MORE_UNTRUSTED_CHECKPOINTS'
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--certificate',type=Path,required=True)
    p.add_argument('--native-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        raise FileExistsError('REFUSE_OVERWRITE_FORENSIC_INVENTORY')
    try:
        report=inventory(args.artifact,args.certificate,args.native_dir)
    except Exception as exc:
        report={'schema':'heart-h9-partial-native-forensic-inventory-failure-v1',
                'status':'REJECTED_FROZEN_INPUT_OR_ARCHIVE',
                'reason':f'{type(exc).__name__}: {exc}',
                'new_cherchi_calls_verified_by_this_inventory':0,
                'newton_admitted':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:
        json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')
    print('H9_SIDE_FORENSIC_INVENTORY',report['status'],flush=True)
    return 0 if report['status'] in ('REVIEW_NOT_A_FRESH_CHERCHI_EXECUTION','NO_NATIVE_SIDE_DIRECTORY') else 2


if __name__=='__main__':
    raise SystemExit(main())
