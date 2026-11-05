"""Run fail-closed exact post-Boolean intersection audit on authenticated W1 packets.
No native Cherchi execution; never treats an absent result as an empty material.
"""
import argparse
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json, subprocess, sys, time
from zipfile import ZipFile

POINTS = (117, 4, 116, 123)
EXPECTED_SHA = '0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976'

def sha(b):return sha256(b).hexdigest()

def verify_manifest(z):
    if len(z.namelist()) != len(set(z.namelist())):
        raise ValueError('M26_DUPLICATED_ZIP_NAMES')
    manifest=json.loads(z.read('material-evidence-manifest.json'))
    if manifest.get('schema') != 'w1-selector-material-evidence-bundle-v1':
        raise ValueError('M26_MANIFEST_SCHEMA')
    entries=manifest.get('files')
    if not isinstance(entries,list) or not entries:
        raise ValueError('M26_MANIFEST_EMPTY')
    names=set(z.namelist())-{'material-evidence-manifest.json'}
    expected={row['file'] for row in entries}
    if len(expected)!=len(entries) or names!=expected:
        raise ValueError('M26_MEMBER_SET_DRIFT')
    for row in entries:
        b=z.read(row['file'])
        if len(b)!=row['bytes'] or sha(b)!=row['sha256']:
            raise ValueError('M26_MEMBER_DIGEST_DRIFT:'+row['file'])
    return manifest

def rational_stream(packet):
    v=packet['exact_vertices'];f=packet['faces'];flo=packet['vertices']
    if not isinstance(v,list) or not isinstance(f,list) or not isinstance(flo,list):raise ValueError('M26_BAD_ARRAYS')
    if not v:
        if f or flo or packet['construction_records']: raise ValueError('M26_MALFORMED_EMPTY')
    elif not f:raise ValueError('M26_ORPHAN_POINTS')
    if len(flo)!=len(v) or len(packet['construction_records'])!=len(v):raise ValueError('M26_MISSING_OR_MISMATCHED_VERTICES')
    out=[f'{len(v)} {len(f)}']
    for row in v:
        if len(row)!=3 or not all(isinstance(x,str) for x in row):raise ValueError('M26_BAD_EXACT_VERTEX')
        out.append(' '.join(row))
    for row in f:
        if len(row)!=3 or any(type(x)!=int or x<0 or x>=len(v) for x in row):raise ValueError('M26_BAD_FACE')
        out.append(' '.join(str(x) for x in row))
    return ('\n'.join(out)+'\n').encode()

def run(archive,binary,output,max_seconds=120):
    archive,binary,output=map(Path,(archive,binary,output))
    # pathlib.Path("./bin") stringifies to "bin"; Popen would then search PATH.
    # Pin an absolute executable path for deterministic execution from any cwd.
    binary=binary.resolve(strict=True)
    if not binary.is_file(): raise ValueError("M26_BINARY_NOT_A_FILE")
    output.parent.mkdir(parents=True,exist_ok=True)
    data={'schema':'w1-m26-post-boolean-exact-intersection-v1',
          'archive_sha256':sha(archive.read_bytes()),'cpp_source_sha256':sha(Path(__file__).with_name('m26_exact_intersection.cpp').read_bytes()),
          'binary_sha256':sha(binary.read_bytes()),'points':[],'new_native_boolean_calls':0,'new_newton_runs':0,
          'formal_material_admission':False,'full_solver_speedup':None}
    try:
      with ZipFile(archive) as z:
        if data['archive_sha256']!=EXPECTED_SHA:raise ValueError('M26_ARCHIVE_SHA_DRIFT')
        if z.testzip() is not None:raise ValueError('M26_BAD_ZIP')
        manifest=verify_manifest(z)
        root=json.loads(z.read('material-probe-result.json'))
        if root.get('status')!='COMPLETE_SELECTOR_MATERIAL_DIAGNOSTIC' or root.get('new_boolean_calls')!=4 or root.get('new_newton_runs')!=0:
            raise ValueError('M26_ORIGINAL_NATIVE_SCOPE_DRIFT')
        for index in POINTS:
            name=f'boolean-packet-{index:06d}.json'
            b=z.read(name)
            pkt=json.loads(b)
            point=json.loads(z.read(f'point-{index:06d}.json'))
            if point.get('raw_packet_sha256')!=sha(b) or point.get('evaluation')!=index or point.get('status')!='BOOLEAN_PACKET_RECORDED':
                raise ValueError('M26_PACKET_RECEIPT_DRIFT:'+str(index))
            expected_operation={117:'difference',4:'intersection',116:'difference',123:'difference'}[index]
            if point.get('boolean_operation') != expected_operation:
                raise ValueError('M26_UNEXPECTED_BOOLEAN_OPERATION')
            stream=rational_stream(pkt)
            t=time.monotonic()
            completed=subprocess.run([str(binary),'--max-seconds',str(max_seconds)],input=stream,capture_output=True,
                                     timeout=max_seconds+25,check=False)
            if completed.returncode not in (0,2,3,4):raise ValueError('M26_UNKNOWN_EXIT')
            stdout=completed.stdout.decode(errors='replace')
            pairs=dict(item.split('=',1) for item in stdout.splitlines() if '=' in item)
            result={'index':index,'operation':point['boolean_operation'],'packet_sha256':sha(b),'input_stream_sha256':sha(stream),'cpp_status':pairs.get('status'),
                    'return_code':completed.returncode,'timing_seconds':time.monotonic()-t,
                    'details':pairs}
            data['points'].append(result)
            if completed.returncode!=0: raise ValueError(f'M26_POINT_{index}_NOT_CERTIFIED:{pairs.get("status")}')
            expected_status='STRICT_EMPTY_NO_POSITIVE_MASS' if index==123 else 'EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE'
            if pairs.get('status') != expected_status: raise ValueError('M26_POINT_CLASSIFICATION_DRIFT:'+str(index))
        data['status']='COMPLETE_SAVED_OUTPUT_SELF_INTERSECTION_CERTIFICATION'
    except BaseException as e:
        data['status']='INCOMPLETE_OR_FAILED_NO_CERTIFICATION';data['error']=type(e).__name__+': '+str(e)
    if output.exists():raise FileExistsError('M26_OUTPUT_EXISTS')
    output.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    return data

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--archive',type=Path,required=True);a.add_argument('--binary',type=Path,required=True)
    a.add_argument('--output',type=Path,required=True);a.add_argument('--max-seconds',type=int,default=120)
    x=a.parse_args();r=run(x.archive,x.binary,x.output,x.max_seconds);print(json.dumps({k:v for k,v in r.items() if k!='points'},indent=2));sys.exit(0 if r['status'].startswith('COMPLETE_') else 2)
