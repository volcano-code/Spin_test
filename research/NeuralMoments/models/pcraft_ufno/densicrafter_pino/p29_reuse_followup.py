#!/usr/bin/env python3
"""P29 focused follow-up: extract existing tracebacks; test tiny CUDA kernels.

No pip/conda operations, checkpoint downloads, or TRELLIS generation.
Uses the already SHA-verified sibling p29_local_reuse_audit.py for cache policy.
GPU tests are forward-only smokes, not model compatibility certification.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

HELPER_SHA = '264437a38a2115f402fa7b10350bf1858615f2196fb772f185fee9b6bbe60b7b'


def read_report(path):
    content = Path(path).read_bytes()
    doc = json.loads(content)
    if not isinstance(doc, dict) or doc.get('schema') != 'W6_P29_LOCAL_REUSE_AUDIT_V1':
        raise ValueError('Expected a W6_P29_LOCAL_REUSE_AUDIT_V1 report')
    if not isinstance(doc.get('probes'), dict):
        raise ValueError('report.probes must be an object')
    if not isinstance(doc.get('target_python'), str) or not Path(doc['target_python']).is_absolute():
        raise ValueError('Report must contain an absolute target_python')
    return doc, hashlib.sha256(content).hexdigest()


def load_helper(path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != HELPER_SHA:
        raise ValueError('Sibling reuse audit differs from the tested version; no execution performed')
    spec = importlib.util.spec_from_file_location('p29_verified_helper', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_child(python, code, root, env, timeout=180):
    """Keep errors and kill the probe process group on timeout; do not poll."""
    try:
        p = subprocess.Popen([str(python), '-I', '-B', '-c', code], cwd=root,
                             env=env, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    except OSError as exc:
        return {'status': 'UNAVAILABLE', 'error': str(exc)}
    status = None
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = p.communicate()
        status = 'TIMEOUT'
    status = status or ('PASS' if p.returncode == 0 else
                        'SKIPPED_RESOURCE' if p.returncode == 77 else 'FAILED')
    return {'status': status, 'returncode': p.returncode,
            'stdout': stdout[-20000:], 'stderr': stderr[-20000:],
            'output_truncated': max(len(stdout), len(stderr)) > 20000}


METADATA = r'''
import importlib.util as iu, importlib.metadata as md, json, sys
out = {'executable':sys.executable, 'python':sys.version, 'sys_path':sys.path,
       'module_specs':{}, 'distributions':[]}
for name in ('utils3d', 'trellis', 'xformers', 'flash_attn', 'spconv'):
    try:
        s = iu.find_spec(name)
        out['module_specs'][name] = None if s is None else {
            'origin':s.origin, 'search_locations':list(s.submodule_search_locations or [])}
    except Exception as e:
        out['module_specs'][name] = {'error':repr(e)}
for d in md.distributions():
    name = d.metadata.get('Name','')
    if any(k in name.lower() for k in ('utils3d','trellis','xformers','flash','spconv','cumm')):
        text = d.read_text('direct_url.json')
        out['distributions'].append({'name':name,'version':d.version,
            'install_root':str(d.locate_file('')),
            'direct_url':json.loads(text) if text else None})
print(json.dumps(out, indent=2))
'''
GPU_HEADER = r'''
import json, torch
if not torch.cuda.is_available():
    raise RuntimeError('CUDA is unavailable in the recorded trellis interpreter')
free, total = torch.cuda.mem_get_info()
if free < 1024**3:
    print('SKIPPED: less than 1 GiB free GPU memory')
    raise SystemExit(77)
print(json.dumps({'torch':torch.__version__, 'cuda':torch.version.cuda,
 'gpu':torch.cuda.get_device_name(0),'capability':torch.cuda.get_device_capability(0)}), flush=True)
'''
FLASH = GPU_HEADER + r'''
import flash_attn

def reference(packed):
    q, k, v = packed.detach().cpu().double().unbind(dim=2)
    q, k, v = [x.transpose(1,2) for x in (q,k,v)]
    return (torch.softmax(q @ k.transpose(-1,-2) / q.shape[-1]**0.5, dim=-1) @ v).transpose(1,2).float()

torch.manual_seed(29)
with torch.no_grad():
    qkv = torch.randn(1,32,3,2,64,device='cuda',dtype=torch.float16)
    expected = reference(qkv)
    out = flash_attn.flash_attn_qkvpacked_func(qkv, dropout_p=0.0, causal=False)
    torch.cuda.synchronize()
    torch.testing.assert_close(out.float().cpu(), expected, atol=0.02, rtol=0.02)
    print('FLASH_QKVPACKED_FP16_FORWARD_PASS', flush=True)
    cumulative = torch.tensor([0,11,32],device='cuda',dtype=torch.int32)
    out = flash_attn.flash_attn_varlen_qkvpacked_func(
        qkv.reshape(32,3,2,64), cumulative, 21, dropout_p=0.0, causal=False)
    expected = torch.cat([reference(qkv[:,:11])[0],reference(qkv[:,11:])[0]],dim=0)
    torch.cuda.synchronize()
    torch.testing.assert_close(out.float().cpu(), expected, atol=0.02, rtol=0.02)
    print('FLASH_VARLEN_QKVPACKED_FP16_FORWARD_PASS', flush=True)
'''
SPCONV = GPU_HEADER + r'''
import spconv.pytorch as spconv
from spconv.core import ConvAlgo
with torch.no_grad():
    # All four active points lie in every point's 3x3x3 neighbourhood.
    idx = torch.tensor([[0,1,1,1],[0,1,2,1],[0,2,1,1],[0,2,2,1]],device='cuda',dtype=torch.int32)
    features = torch.arange(1,9,device='cuda',dtype=torch.float32).repeat(4,1)
    x = spconv.SparseConvTensor(features,idx,[4,4,4],1)
    conv = spconv.SubMConv3d(8,8,3,padding=1,bias=False,algo=ConvAlgo.Native).cuda().eval()
    conv.weight.fill_(1)
    out = conv(x).features
    torch.cuda.synchronize()
    # Independent oracle: four neighbours * sum(1..8) = 144 per output channel.
    torch.testing.assert_close(out,torch.full((4,8),144.0,device='cuda'),rtol=1e-5,atol=1e-4)
    print('SPCONV_NATIVE_SUBM3D_FP32_FORWARD_PASS', flush=True)
'''


def inspect_source(path):
    if not path:
        return {'candidate': None, 'exists': False}
    root = Path(path)
    info = {'candidate': str(root), 'exists': root.is_dir(), 'files': {}}
    for rel in ('setup.sh', 'trellis/modules/attention/__init__.py',
                'trellis/modules/sparse/__init__.py'):
        p = root / rel
        if p.is_file() and p.stat().st_size <= 200000:
            text = p.read_text(encoding='utf-8', errors='replace')
            info['files'][rel] = {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'selected_lines':[{'line':i,'text':line} for i,line in enumerate(text.splitlines(),1)
                   if any(k in line for k in ('utils3d','ATTN_BACKEND','flash_attn','xformers'))]}
    return info


def main(args):
    doc, digest = read_report(args.input)
    helper = load_helper(Path(__file__).with_name('p29_local_reuse_audit.py'))
    root, free = helper.validate_workspace(args.root, 40)
    for rel in set(helper.CACHE_DIRS.values()):
        (root / rel).mkdir(parents=True, exist_ok=True)
    env = helper.child_env(root)
    env.update(ATTN_BACKEND='flash_attn', SPARSE_ATTN_BACKEND='flash_attn',
               SPCONV_ALGO='native', MAX_JOBS='2')
    target = Path(doc['target_python'])
    if not target.is_file():
        raise ValueError(f'Recorded interpreter missing: {target}')
    out = root / 'reports' / ('followup-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema':'W6_P29_REUSE_FOLLOWUP_V1','original_report_sha256':digest,
        'original_report':doc, 'workspace_free_gib':free,
        'source_check':inspect_source(doc.get('repo_candidate')),
        'probes':{}, 'scope':'FORWARD_KERNEL_SMOKES_NOT_MODEL_GENERATION',
        'installs_performed':False, 'model_downloads_requested':False,
        'trellis_generation_validated':False}
    result_path = out / 'p29_followup.json'
    def save():
        result_path.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    save()  # Preserve original errors even if a later probe fails.
    for name in ('environment_metadata','utils3d','xformers.ops'):
        print('\n===== ORIGINAL ' + name + ' =====', flush=True)
        print(json.dumps(doc['probes'].get(name, {'status':'NOT_IN_REPORT'}),ensure_ascii=False,indent=2), flush=True)
    print('\nSOURCE_CHECK=' + json.dumps(report['source_check'],ensure_ascii=False),flush=True)
    report['probes']['package_origins'] = run_child(target,METADATA,root,env,60)
    save()
    print('package_origins: '+report['probes']['package_origins']['status'],flush=True)
    for name, code in (('flash_attention_forward',FLASH),('spconv_native_forward',SPCONV)):
        print('Running '+name,flush=True)
        report['probes'][name] = ({'status':'SKIPPED_BY_USER'} if args.skip_kernels else
                                  run_child(target,code,root,env,180))
        save()
        print(name+': '+report['probes'][name]['status'],flush=True)
        if report['probes'][name]['status'] != 'PASS':
            print(report['probes'][name].get('stderr',''),flush=True)
    print('REPORT='+str(result_path),flush=True)
    print('No package installation or generation performed; review the report before any repair.')


class SelfTests(unittest.TestCase):
    def test_report_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json'; p.write_text('{}')
            with self.assertRaises(ValueError): read_report(p)
    def test_report_preserves_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json'; doc={'schema':'W6_P29_LOCAL_REUSE_AUDIT_V1','target_python':'/usr/bin/python3',
                                    'probes':{'utils3d':{'stderr':'original traceback'}}}
            p.write_text(json.dumps(doc)); before=p.read_bytes()
            result,sha=read_report(p)
            self.assertEqual(result,doc); self.assertEqual(len(sha),64); self.assertEqual(p.read_bytes(),before)
    def test_unverified_helper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'helper.py'; p.write_text("raise RuntimeError('must not execute')")
            with self.assertRaises(ValueError): load_helper(p)
    def test_probe_sources_compile(self):
        for source in (METADATA,FLASH,SPCONV): compile(source,'probe','exec')
    def test_source_inspection_is_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'setup.sh'; p.write_text('pip install utils3d\n')
            r=inspect_source(d)
            self.assertEqual(r['files']['setup.sh']['selected_lines'][0]['line'],1)
            self.assertEqual(p.read_text(),'pip install utils3d\n')
    def test_no_repo_claim_when_missing(self):
        self.assertFalse(inspect_source(None)['exists'])
    def test_failed_child_is_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            r=run_child(sys.executable,"raise RuntimeError('expected')",Path(d),os.environ.copy())
            self.assertEqual(r['status'],'FAILED'); self.assertIn('expected',r['stderr'])
    def test_timeout_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            r=run_child(sys.executable,'import time; time.sleep(5)',Path(d),os.environ.copy(),.05)
            self.assertEqual(r['status'],'TIMEOUT')
    def test_resource_skip_is_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            r=run_child(sys.executable,'raise SystemExit(77)',Path(d),os.environ.copy())
            self.assertEqual(r['status'],'SKIPPED_RESOURCE')
    def test_spconv_oracle(self):
        pts=[(1,1,1),(1,2,1),(2,1,1),(2,2,1)]
        for p in pts:
            neighbours=sum(all(abs(a-b)<=1 for a,b in zip(p,q)) for q in pts)
            self.assertEqual(neighbours*sum(range(1,9)),144)

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    else:
        parser=argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--input',type=Path,required=True)
        parser.add_argument('--root',type=Path,default=Path('/opt/w6-p29-lin'))
        parser.add_argument('--skip-kernels',action='store_true')
        try:
            main(parser.parse_args())
        except (OSError,ValueError,KeyError,TypeError) as exc:
            parser.exit(2,'Stopped safely: '+str(exc)+'\n')
