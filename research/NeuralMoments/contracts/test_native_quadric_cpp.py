"""Compile true frozen native QuadricCoefficients.cpp, not a rewritten formula.

Only the unrelated manufacturing::computeContentSha256 link function is stubbed;
no hash output is measured. Runs single compiler process (no parallel jobs).
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

ROOT=Path(__file__).resolve().parents[3]
CPP=ROOT/'src/spin/QuadricCoefficients.cpp'
HEADER=ROOT/'include/spin/QuadricCoefficients.h'
PROBE=Path(__file__).with_name('native_quadric_probe.cpp')
EXPECTED={
    CPP:'ae831afe9191f67fb2659f112d1b85a8e2b61581',
    HEADER:'d315960a8d9616197df656a3c74b74b2da037798',
}


def git_blob_sha(path):
    data=path.read_bytes()
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()


def eigen_include():
    possibilities=[]
    if os.environ.get('EIGEN3_INCLUDE_DIR'):
        possibilities.append(Path(os.environ['EIGEN3_INCLUDE_DIR']))
    possibilities += [Path('/usr/include/eigen3'),Path('/usr/local/include/eigen3')]
    try:
        import importlib.util
        spec=importlib.util.find_spec('casadi')
        if spec and spec.origin:
            possibilities.append(Path(spec.origin).parent/'include/eigen3')
    except (ImportError,ValueError):
        pass
    for p in possibilities:
        if (p/'Eigen/Core').is_file():
            return p
    pytest.skip('SKIP: Eigen unavailable; do not claim production native C++ passed')


@pytest.fixture(scope='module')
def compiled_run():
    for path,sha in EXPECTED.items():
        assert path.is_file(),f'production source missing: {path}'
        assert git_blob_sha(path)==sha,f'frozen native source identity drift: {path}'
    assert shutil.which('g++'),'native compiler unavailable'
    eigen=eigen_include()
    with tempfile.TemporaryDirectory(prefix='w0-quadric-real-source-') as tmp:
        directory=Path(tmp)
        stub=directory/'hash_dependency_link_stub.cpp'
        stub.write_text('#include <string>\nnamespace manufacturing {std::string computeContentSha256(const std::string&) {return std::string(64,\'0\');}}\n',encoding='ascii')
        executable=directory/'native_quadric_probe'
        cmd=['g++','-std=c++17','-O1','-Wall','-Wextra',
             '-I'+str(ROOT/'include'),'-I'+str(eigen),
             str(CPP),str(stub),str(PROBE),'-o',str(executable)]
        compile_result=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
        assert compile_result.returncode==0, ('native compile failed: '+compile_result.stderr)
        run=subprocess.run([str(executable)],capture_output=True,text=True,timeout=15)
        assert run.returncode==0,('native test failed: '+run.stdout+run.stderr)
        data=json.loads(run.stdout)
        yield data


def test_real_native_compiled_math_coordinates(compiled_run):
    x=compiled_run
    assert x['status']=='PASS' and x['probe_points']==125
    for name in ('max_value_error','max_gradient_error','max_homogeneous_error'):
        assert x[name]<2e-14
    assert x['max_pullback_error']<2e-13
    assert x['positive_pullback_scale']>0
    assert x['hash_dependency_stubbed'] is True


def test_provenance_does_not_pretend_native_cherchi(compiled_run):
    assert compiled_run['hash_dependency_stubbed'] is True
    assert not any('cherchi' in k.lower() for k in compiled_run)
