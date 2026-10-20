"""Reproduce the ORIGINAL W3 promotion race and verify Stage14 remedy.

Storage-only synthetic fixture. NEVER counts as a new Cherchi evaluation.

Examples:
  python tests/reproduce_h9_stage14_race.py --source /path/to/stage13/source --mode original
  python tests/reproduce_h9_stage14_race.py --source ./source --mode fixed
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

WORKER = r'''
import json, sys, time
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import h9_same_call_capture as cp
root=Path(sys.argv[2]);actor=sys.argv[3]
proof=json.loads((root/'seed-proof.json').read_text())
meta={'index':0,'side':'left-coarse','q':proof['coefficients'],
      'material_sha256':proof['archive_sha256'],'native_geometry_valid':True,'newton_admitted':False}
if actor=='A':
    old=cp._atomic_write_json
    def hold(path,body):
        if Path(path).name=='side-00-left-coarse.json':
            (root/'a_is_publishing').write_text('linked')
            limit=time.monotonic()+10
            while not (root/'release_a').exists() and time.monotonic()<limit:time.sleep(.004)
        return old(path,body)
    cp._atomic_write_json=hold
try:
    cp.promote_after_full_audit(root,proof,meta)
    status={'actor':actor,'result':'success'}
except BaseException as e:
    status={'actor':actor,'result':'rejected','error':str(e)}
(root/f'result_{actor}.json').write_text(json.dumps(status))
'''


def exercise(source: Path, mode: str):
    source=source.resolve()
    sys.path.insert(0,str(source))
    import h9_same_call_capture as cp
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        q=[float(i) for i in range(10)]
        backend='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'
        material={'quadric_coefficients':q,'boolean_backend_identity':backend,
                  'material_proof':{'schema':'cherchi-same-call-material-v1'}}
        proof=cp.capture_same_call(root,index=0,side='left-coarse',coefficients=q,
                                    material=material,backend_identity=backend)
        (root/'seed-proof.json').write_text(json.dumps(proof))
        processes=[]
        try:
            a=subprocess.Popen([sys.executable,'-c',WORKER,str(source),str(root),'A'])
            processes.append(a)
            for _ in range(1000):
                if (root/'a_is_publishing').exists():break
                time.sleep(.005)
            assert (root/'a_is_publishing').is_file(), 'A never started final metadata step'
            b=subprocess.Popen([sys.executable,'-c',WORKER,str(source),str(root),'B'])
            processes.append(b)
            if mode=='original':
                b.wait(timeout=8)
                assert b.returncode==0
            else:
                time.sleep(.22)
                assert b.poll() is None, 'second writer did not respect promotion lease'
            (root/'release_a').write_text('go')
            for proc in processes:proc.wait(timeout=8)
            states=[json.loads((root/f'result_{who}.json').read_text()) for who in ('A','B')]
            final=root/'side-00-left-coarse.json.gz'
            meta=root/'side-00-left-coarse.json'
            state={'schema':'heart-h9-stage14-promotion-race-reproduction-v1',
                   'mode':mode,'fixture':'SYNTHETIC_STORAGE_FIXTURE_NOT_CHERCHI',
                   'original_h8f_artifact_untouched':True,
                   'processes':states, 'formal_gzip_exists':final.is_file(),
                   'formal_json_exists':meta.is_file(),
                   'formal_sha_matches_source':final.is_file() and cp.digest(final)==proof['archive_sha256'],
                   'metadata_denies_newton':meta.is_file() and json.loads(meta.read_text())['newton_admitted'] is False,
                   'lock_exists':(root/'.h9-promotion-00-left-coarse.lock').is_file(),
                   'new_cherchi_evaluations':0,'newton_admitted':False}
            if mode=='original':
                assert states[1]['result']=='success' and state['formal_json_exists'] and not state['formal_gzip_exists'], state
            else:
                assert states[0]['result']=='success' and states[1]['result']=='rejected' and state['formal_sha_matches_source'] and state['metadata_denies_newton'],state
            return state
        finally:
            for proc in processes:
                if proc.poll() is None:proc.kill();proc.wait(timeout=3)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--mode',choices=['original','fixed'],required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args();status=exercise(a.source,a.mode)
    text=json.dumps(status,indent=2,sort_keys=True)+'\n'
    if a.output:a.output.write_text(text)
    print(text)

if __name__=='__main__':main()
