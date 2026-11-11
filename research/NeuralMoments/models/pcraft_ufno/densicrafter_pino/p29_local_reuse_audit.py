#!/usr/bin/env python3
"""W6 P29: inspect an existing TRELLIS environment without reinstalling it.

New evidence: RTX 5090 D 32GB, CUDA toolkit 12.8; base Python 3.13.5 /
PyTorch 2.8.0+cu128 is NOT evidence about the separate trellis environment.
No pip/conda install, git checkout/pull, model download, cleanup or repair.
Writes only reports/caches under --root; imports execute in isolated children.
Imports alone do NOT certify extension kernels or end-to-end generation.

Example:
  python3 p29_local_reuse_audit.py --root /opt/w6-p29-lin \
    --python /home/lin/anaconda3/envs/trellis/bin/python \
    --repo /home/lin/xvxinyao/DensiCrafter/TRELLIS
CPU-only self-tests: python3 p29_local_reuse_audit.py --self-test
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

GIB = 1024**3
MODULES = ("numpy", "torchvision", "trimesh", "PIL", "easydict",
           "utils3d", "spconv.pytorch", "kaolin", "nvdiffrast.torch",
           "xformers.ops", "flash_attn")
CACHE_DIRS = {
    "HOME": "probe_home", "XDG_CACHE_HOME": "cache/xdg",
    "HF_HOME": "cache/huggingface", "HF_HUB_CACHE": "cache/huggingface/hub",
    "HF_XET_CACHE": "cache/huggingface/xet", "TORCH_HOME": "cache/torch",
    "TORCH_EXTENSIONS_DIR": "cache/torch_extensions",
    "CUDA_CACHE_PATH": "cache/cuda", "TRITON_CACHE_DIR": "cache/triton",
    "TORCHINDUCTOR_CACHE_DIR": "cache/torchinductor",
    "PIP_CACHE_DIR": "cache/pip", "CONDA_PKGS_DIRS": "cache/conda_pkgs",
    "MPLCONFIGDIR": "cache/matplotlib", "NUMBA_CACHE_DIR": "cache/numba",
    "TMPDIR": "tmp", "TEMP": "tmp", "TMP": "tmp",
}


def child_env(root: Path, inherited=None):
    """Only child processes are changed; never modify the caller's shell."""
    env = dict(os.environ if inherited is None else inherited)
    for key in ("PYTHONPATH", "PYTHONHOME", "LD_PRELOAD", "LD_LIBRARY_PATH",
                "TRANSFORMERS_CACHE", "PYTORCH_TRANSFORMERS_CACHE"):
        env.pop(key, None)
    env.update({key: str(root / rel) for key, rel in CACHE_DIRS.items()})
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               HF_HUB_DISABLE_TELEMETRY="1", PYTHONNOUSERSITE="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", GIT_OPTIONAL_LOCKS="0")
    return env


def run_command(argv, *, cwd: Path, env, timeout=60):
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, text=True,
                              capture_output=True, timeout=timeout, check=False)
        status = "PASS" if proc.returncode == 0 else "FAILED"
        return {"status": status, "returncode": proc.returncode,
                "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-12000:],
                "output_truncated": max(len(proc.stdout), len(proc.stderr)) > 12000}
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "timeout_seconds": timeout}
    except OSError as exc:
        return {"status": "UNAVAILABLE", "error": str(exc)}


def python_probe(executable, code, *, root: Path, env, timeout=60):
    # -I excludes user site/PYTHONPATH; -B prevents pyc writes into old environments.
    return run_command([str(executable), "-I", "-B", "-c", code],
                       cwd=root, env=env, timeout=timeout)


def validate_workspace(root: Path, min_free_gib=40.0):
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace must be an existing directory")
    if not math.isfinite(min_free_gib) or min_free_gib < 0:
        raise ValueError("min_free_gib must be finite and non-negative")
    if root.stat().st_dev != Path("/").stat().st_dev:
        raise ValueError("workspace is not on the root filesystem; do not use /home or /data")
    free = shutil.disk_usage(root).free / GIB
    if free < min_free_gib:
        raise ValueError(f"workspace has {free:.2f} GiB free; policy reserve is {min_free_gib:.2f} GiB")
    return root, free


def weight_inventory(root: Path, limit=2000):
    """Bounded metadata scan; do not load/hash/copy large checkpoints."""
    if not root.is_dir():
        return {"exists": False, "path": str(root)}
    matches, examined, truncated = [], 0, False
    for current, dirs, names in os.walk(root, followlinks=False):
        depth = len(Path(current).relative_to(root).parts)
        dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__"})
        if depth >= 5:
            truncated |= bool(dirs)
            dirs[:] = []
        for name in sorted(names):
            examined += 1
            if examined > limit:
                truncated = True
                break
            path = Path(current) / name
            if path.suffix.lower() in {".pt", ".pth", ".ckpt", ".safetensors", ".bin"}:
                try:
                    matches.append({"path": str(path), "bytes": path.stat().st_size})
                except OSError:
                    matches.append({"path": str(path), "unreadable": True})
        if examined > limit:
            break
    return {"exists": True, "path": str(root), "files_examined": min(examined, limit),
            "scan_incomplete": truncated, "weights_found": matches,
            "note": "Metadata only; presence does not prove a complete usable checkpoint."}


METADATA_PROBE = r'''
import importlib.metadata as md, json, sys
prefixes = ('torch','numpy','kaolin','spconv','cumm','nvdiffrast','xformers',
            'flash','triton','pillow','transformers','huggingface','trimesh','utils3d')
packages = sorted((d.metadata.get('Name',''), d.version) for d in md.distributions()
                  if d.metadata.get('Name','').lower().startswith(prefixes))
print(json.dumps({'executable':sys.executable,'python':sys.version,'prefix':sys.prefix,
                  'packages':packages}, indent=2))
'''
TORCH_PROBE = r'''
import json, torch
print(json.dumps({'torch':torch.__version__,'torch_cuda':torch.version.cuda,
                  'cuda_available':torch.cuda.is_available()}, indent=2), flush=True)
if not torch.cuda.is_available():
    raise RuntimeError('CUDA unavailable in the target trellis interpreter')
print(json.dumps({'device':torch.cuda.get_device_name(0),
                  'capability':torch.cuda.get_device_capability(0),
                  'compiled_arches':torch.cuda.get_arch_list()}, indent=2), flush=True)
free, total = torch.cuda.mem_get_info()
if free < 1024**3:
    raise RuntimeError('less than 1 GiB free GPU memory: skip smoke; do not stop other jobs')
with torch.inference_mode():
    x = torch.eye(64, device='cuda', dtype=torch.float32)
    for dtype in (torch.float32, torch.float16):
        a = x.to(dtype)
        out = a @ a
        if not torch.isfinite(out).all() or not torch.allclose(out, a):
            raise RuntimeError('CUDA matrix multiplication verification failed')
    torch.cuda.synchronize()
print('TORCH_CUDA_FP32_FP16_MATMUL_PASS')
'''


def audit(args):
    root, free = validate_workspace(args.root, args.min_free_gib)
    for rel in set(CACHE_DIRS.values()):
        (root / rel).mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = root / "reports" / ("reuse-" + stamp)
    out.mkdir(parents=True, exist_ok=False)
    env = child_env(root)
    report = {"schema": "W6_P29_LOCAL_REUSE_AUDIT_V1", "workspace": str(root),
              "workspace_free_gib": free, "target_python": str(args.python),
              "repo_candidate": str(args.repo), "probes": {},
              "limits": {"installs_performed": False, "model_downloads_requested": False,
                         "extension_cuda_kernels_validated": False,
                         "trellis_generation_validated": False}}
    for name, argv in (("gpu_processes", ["nvidia-smi"]),
                       ("toolkit", ["nvcc", "--version"])):
        report["probes"][name] = run_command(argv, cwd=root, env=env, timeout=15)
    if args.python.is_file():
        report["probes"]["environment_metadata"] = python_probe(args.python, METADATA_PROBE, root=root, env=env)
        report["probes"]["torch_cuda_kernel"] = ({"status": "SKIPPED_BY_USER"} if args.skip_gpu
            else python_probe(args.python, TORCH_PROBE, root=root, env=env, timeout=90))
        for module in MODULES:
            code = ("import importlib; m=importlib.import_module(" + repr(module) + "); "
                    "print(getattr(m,'__file__',None)); print(getattr(m,'__version__','version_unavailable'))")
            report["probes"][module] = python_probe(args.python, code, root=root, env=env)
    else:
        report["probes"]["environment_metadata"] = {"status": "TARGET_INTERPRETER_NOT_FOUND"}
    report["repo_exists"] = args.repo.is_dir()
    if args.repo.is_dir():
        for key, tail in (("repo_head", ["rev-parse", "HEAD"]),
                          ("repo_changes", ["status", "--porcelain=v1", "--untracked-files=no"])):
            report["probes"][key] = run_command(["git", "-C", str(args.repo), *tail],
                                                    cwd=root, env=env, timeout=15)
        report["weights"] = weight_inventory(args.repo / "pretrained-models")
    report["attention_backends_are_optional_choices"] = ["xformers.ops", "flash_attn"]
    report["decision"] = "DIAGNOSTIC_ONLY_REVIEW_LOGS_BEFORE_INSTALL_OR_GENERATION"
    path = out / "p29_reuse_audit.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    for name, result in report["probes"].items():
        print(f"{name}: {result['status']}")
    print(f"REPORT={path}")
    print("No environment was installed/upgraded; no TRELLIS inference was performed.")
    return path


class SelfTests(unittest.TestCase):
    def test_environment_is_not_mutated(self):
        source = {"HOME": "/old", "LD_PRELOAD": "unsafe.so", "PYTHONPATH": "/old"}
        new = child_env(Path("/tmp/work"), source)
        self.assertEqual(source["HOME"], "/old")
        self.assertNotIn("LD_PRELOAD", new)
        self.assertNotIn("PYTHONPATH", new)
    def test_all_cache_paths_are_redirected(self):
        env = child_env(Path("/tmp/work"), {})
        self.assertTrue(all(env[k].startswith("/tmp/work/") for k in CACHE_DIRS))
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
    def test_failed_import_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            r = python_probe(sys.executable, "import p29_module_that_does_not_exist", root=Path(d), env=child_env(Path(d)))
            self.assertEqual(r["status"], "FAILED")
            self.assertIn("ModuleNotFoundError", r["stderr"])
    def test_child_timeout_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            r = python_probe(sys.executable, "import time; time.sleep(5)", root=Path(d), env=child_env(Path(d)), timeout=.05)
            self.assertEqual(r["status"], "TIMEOUT")
    def test_metadata_probe_is_stdlib_only(self):
        with tempfile.TemporaryDirectory() as d:
            r = python_probe(sys.executable, METADATA_PROBE, root=Path(d), env=child_env(Path(d)))
            self.assertEqual(r["status"], "PASS", r)
            self.assertIn("python", json.loads(r["stdout"]))
    def test_workspace_reserve_rejects_insufficient_space(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                validate_workspace(Path(d), 1e12)
    def test_weight_scan_does_not_read_file_contents(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "model.safetensors"
            p.write_text("not a model")
            r = weight_inventory(Path(d))
            self.assertEqual(len(r["weights_found"]), 1)
            self.assertEqual(p.read_text(), "not a model")
    def test_weight_scan_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                (Path(d) / f"{i}.pt").write_text("x")
            self.assertTrue(weight_inventory(Path(d), limit=1)["scan_incomplete"])
    def test_missing_weights_not_claimed_present(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(weight_inventory(Path(d) / "missing")["exists"])


def main():
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path.home()/"anaconda3/envs/trellis/bin/python")
    parser.add_argument("--repo", type=Path, default=Path.home()/"xvxinyao/DensiCrafter/TRELLIS")
    parser.add_argument("--min-free-gib", type=float, default=40)
    parser.add_argument("--skip-gpu", action="store_true", help="Skip only the small PyTorch CUDA kernel smoke")
    args = parser.parse_args()
    try:
        audit(args)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Audit stopped safely: {exc}\n")

if __name__ == "__main__":
    main()
