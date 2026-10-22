#!/usr/bin/env python3
"""Build the frozen native preparation stack; never execute material geometry.

Run from the P20 checkout with a separate, clean source checkout at SOURCE_SHA.
The CI caller installs cmake<4, ninja, pybind11==3.0.1, numpy, pkg-config,
libgmp-dev, libmpfr-dev and the Boost thread/system development packages first.
All compile targets are explicit and Ninja uses one worker. Every subprocess
inherits a 6 GiB address-space limit. A shared 3540-second deadline leaves one
minute within a 60-minute envelope for failure cleanup and evidence writing.
No tracked source is patched. Only pinned dependency checkouts are populated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

SOURCE_SHA = "58fd12c1306c1c01679a19172e276eef0cb30542"
LIBIGL_SHA = "f06fb13014aadff7eb1d7423ac018620441a3657"
CGAL_SHA = "f7c3c8212b56c0d6dae63787efc99093f4383415"
EIGEN_SHA = "21ae2afd4edaa1b69782c67a54182d34efe43f9c"
CHERCHI_SHA = "7bd6c2697695f555f9a15d7e154e084d841316f0"
AS_LIMIT = 6 * 1024**3
CHERCHI_RELATIVE = (
    "external/reference-sources-20260917/sources/"
    "InteractiveAndRobustMeshBooleans-" + CHERCHI_SHA
)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Build:
    def __init__(self, args):
        self.source = args.source_checkout.resolve(strict=True)
        self.root = args.build_root.resolve()
        self.evidence = args.evidence.resolve()
        paths = (self.source, self.root, self.evidence)
        if any(a == b or a in b.parents or b in a.parents
               for i, a in enumerate(paths) for b in paths[i + 1:]):
            raise ValueError("source, build and evidence paths must be separate non-nested directories")
        self.evidence.mkdir(parents=True, exist_ok=False)
        self.root.mkdir(parents=True, exist_ok=False)
        self.started = time.monotonic()
        self.deadline = self.started + args.timeout_seconds
        self.env = os.environ.copy()
        self.env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                        CMAKE_BUILD_PARALLEL_LEVEL="1")
        self.requested_tools = (args.cmake, args.ninja, args.python)
        self.report = {
            "schema": "w4-p20-frozen-native-build-v1",
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "source_checkout": str(self.source), "source_sha": SOURCE_SHA,
            "builder_script_sha256": sha256(Path(__file__).resolve(strict=True)),
            "build_root": str(self.root), "evidence": str(self.evidence),
            "policy": {"ninja_workers": 1, "rlimit_as_bytes": AS_LIMIT,
                       "shared_subprocess_deadline_seconds": args.timeout_seconds,
                       "maximum_overall_envelope_seconds": 3600,
                       "linker_flags": "unmodified upstream CMake defaults"},
            "steps": [], "status": "RUNNING", "geometry_calls": 0,
            "teacher_calls": 0, "optimizer_calls": 0,
            "formal_m6_resource_admission": False,
            "w0_or_w2_approval": False,
        }

    @staticmethod
    def executable(value: str) -> str:
        found = shutil.which(value)
        if not found:
            raise ValueError("required executable missing: " + value)
        return str(Path(found).resolve(strict=True))

    def run(self, name, command, *, cwd=None, env=None):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("shared native-build deadline exhausted")
        log = self.evidence / f"{len(self.report['steps']) + 1:02d}-{name}.log"
        step = {"name": name, "command": [str(x) for x in command],
                "cwd": str(cwd or self.source), "log": log.name}
        self.report["steps"].append(step)
        started = time.monotonic()

        def limit():
            resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))

        process = None
        with log.open("xb") as output:
            try:
                process = subprocess.Popen(
                    step["command"], cwd=cwd or self.source,
                    env=env or self.env, stdout=output, stderr=subprocess.STDOUT,
                    start_new_session=True, preexec_fn=limit)
                process.wait(timeout=remaining)
                step["returncode"] = process.returncode
            except BaseException:
                if process is not None and process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                step["returncode"] = process.returncode if process else None
                raise
            finally:
                step["wall_seconds"] = time.monotonic() - started
        step["log_sha256"] = sha256(log)
        if process.returncode:
            raise RuntimeError(f"{name} failed with exit {process.returncode}; see {log.name}")
        return log.read_text(errors="replace").strip()

    def git(self, name, repository, *arguments):
        return self.run(name, ["git", "-C", repository, *arguments])

    def identity(self, name, repository, expected):
        head = self.git(name + "-head", repository, "rev-parse", "HEAD")
        if head != expected:
            raise ValueError(name + " source revision mismatch")
        self.git(name + "-tracked-clean", repository, "diff", "--exit-code", "HEAD", "--")
        tree = self.git(name + "-tree", repository, "rev-parse", "HEAD^{tree}")
        return {"path": str(repository), "head": head, "git_tree": tree,
                "tracked_files_match_head": True}

    def clone_pinned(self, name, destination, url, revision):
        if not destination.exists():
            destination.mkdir(parents=True)
            self.run(name + "-init", ["git", "init", destination])
            self.git(name + "-origin", destination, "remote", "add", "origin", url)
            self.git(name + "-fetch", destination, "fetch", "--depth", "1",
                     "--filter=blob:none", "origin", revision)
            self.git(name + "-checkout", destination, "checkout", "--detach", "FETCH_HEAD")
        identity = self.identity(name, destination, revision)
        status = self.git(name + "-status", destination, "status", "--porcelain=v1")
        if status:
            raise ValueError(name + " dependency checkout is not clean")
        return identity

    def check_untracked(self, name):
        output = self.git(name, self.source, "ls-files", "--others", "--exclude-standard")
        allowed = CHERCHI_RELATIVE + "/"
        if any(path != CHERCHI_RELATIVE and not path.startswith(allowed)
               for path in output.splitlines()):
            raise ValueError("unexpected untracked file in frozen source checkout")

    def execute(self):
        self.cmake, self.ninja, self.python = map(self.executable, self.requested_tools)
        self.compiler = self.executable("c++")
        self.c_compiler = self.executable("cc")
        self.report["repositories_before"] = {
            "core": self.identity("core-before", self.source, SOURCE_SHA)}
        self.check_untracked("source-untracked-before")
        versions = {
            "cmake": self.run("cmake-version", [self.cmake, "--version"]),
            "ninja": self.run("ninja-version", [self.ninja, "--version"]),
            "compiler": self.run("compiler-version", [self.compiler, "--version"]),
            "python": self.run("python-version", [self.python, "-c",
                "import json,sys,numpy,pybind11; "
                "assert pybind11.__version__ == '3.0.1'; "
                "print(json.dumps({'python':sys.version,'numpy':numpy.__version__,"
                "'pybind11':pybind11.__version__}))"]),
            "gmp_mpfr": self.run("gmp-mpfr-version",
                                  ["pkg-config", "--modversion", "gmp", "mpfr"]),
        }
        version = tuple(int(x) for x in versions["cmake"].splitlines()[0].split()[-1].split(".")[:2])
        if not (3, 21) <= version < (4, 0):
            raise ValueError("CMake >=3.21,<4 is required")
        if versions["gmp_mpfr"].splitlines() != ["6.3.0", "4.2.1"]:
            raise ValueError("frozen Faster dependency versions require GMP 6.3.0 and MPFR 4.2.1")
        self.report["tool_versions"] = versions
        self.report["tool_sha256"] = {
            path: sha256(Path(path)) for path in
            (self.cmake, self.ninja, self.python, self.compiler, self.c_compiler)}
        self.git("libigl-init", self.source, "submodule", "update", "--init", "--depth", "1", "libigl")
        repositories = {
            "core": self.report["repositories_before"]["core"],
            "libigl": self.identity("libigl", self.source / "libigl", LIBIGL_SHA),
            "cgal": self.clone_pinned("cgal", self.source / "libigl/external/cgal",
                "https://github.com/CGAL/cgal.git", CGAL_SHA),
            "eigen": self.clone_pinned("eigen", self.source / "libigl/external/eigen",
                "https://gitlab.com/libeigen/eigen.git", EIGEN_SHA),
            "cherchi": self.clone_pinned("cherchi", self.source / CHERCHI_RELATIVE,
                "https://github.com/gcherchi/InteractiveAndRobustMeshBooleans.git", CHERCHI_SHA),
        }
        if self.git("libigl-status", self.source / "libigl", "status", "--porcelain=v1"):
            raise ValueError("libigl dependency checkout is not clean")
        self.report["repositories_before"] = repositories
        core = self.root / "core"
        cherchi = self.root / "cherchi"
        common = ["-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
                  "-DCMAKE_MAKE_PROGRAM=" + self.ninja,
                  "-DCMAKE_CXX_COMPILER=" + self.compiler,
                  "-DCMAKE_C_COMPILER=" + self.c_compiler,
                  "-DPython_EXECUTABLE=" + self.python]
        self.run("configure-core", [self.cmake, "-S", self.source, "-B", core, *common,
            "-DPython3_EXECUTABLE=" + self.python,
            "-DMAKE_IT_STAND_BUILD_VIEWER=OFF", "-DMAKE_IT_STAND_BUILD_REACHABILITY=OFF",
            "-DMAKE_IT_STAND_BUILD_SPIN_IT_2014=OFF", "-DMAKE_IT_STAND_BUILD_SPIN_IT_FASTER=ON",
            "-DMAKE_IT_STAND_BUILD_EXACT_GEOMETRY_CHECKS=ON", "-DMAKE_IT_STAND_BUILD_PYTHON=ON",
            "-DBUILD_TESTING=OFF", "-DLIBIGL_SKIP_DOWNLOAD=ON",
            "-DCGAL_Boost_USE_STATIC_LIBS=OFF", "-DBoost_USE_STATIC_LIBS=OFF",
            "-DBoost_NO_BOOST_CMAKE=ON"])
        self.run("build-core", [self.cmake, "--build", core,
                                "--target", "_make_it_stand", "--parallel", "1"])
        self.run("configure-cherchi", [self.cmake, "-S", self.source / "bindings/cherchi",
            "-B", cherchi, *common, "-DMAKE_IT_STAND_CHERCHI_RATIONAL_ARITHMETIC=ON"])
        self.run("build-cherchi", [self.cmake, "--build", cherchi,
            "--target", "_cherchi_core_boolean", "_cherchi_rational_moments", "--parallel", "1"])
        self.report["cmake_caches"] = {}
        for name, directory in (("core", core), ("cherchi", cherchi)):
            destination = self.evidence / (name + "-CMakeCache.txt")
            shutil.copyfile(directory / "CMakeCache.txt", destination)
            self.report["cmake_caches"][name] = {
                "file": destination.name, "sha256": sha256(destination)}
        modules = {}
        for name, directory in (("_make_it_stand", core / "python"),
                                ("_cherchi_core_boolean", cherchi / "python"),
                                ("_cherchi_rational_moments", cherchi / "python")):
            matches = list(directory.glob(name + "*.so"))
            if len(matches) != 1:
                raise ValueError("one native ELF required for " + name)
            path = matches[0].resolve(strict=True)
            if path.read_bytes()[:4] != b"\x7fELF":
                raise ValueError("native output is not ELF: " + name)
            modules[name] = {"path": str(path), "sha256": sha256(path),
                             "size_bytes": path.stat().st_size}
        pythonpath = os.pathsep.join(str(p) for p in
                                    (self.source / "python", core / "python", cherchi / "python"))
        probe_env = dict(self.env, PYTHONPATH=pythonpath)
        probe = (
            "import hashlib,importlib,json,pathlib; "
            "expected=json.loads(" + repr(json.dumps(modules)) + "); "
            "loaded={name:importlib.import_module(name) for name in expected}; "
            "assert all(str(pathlib.Path(loaded[n].__file__).resolve())==v['path'] "
            "and hashlib.sha256(pathlib.Path(v['path']).read_bytes()).hexdigest()==v['sha256'] "
            "for n,v in expected.items()); "
            "core=loaded['_make_it_stand']; "
            "required=('ExactMaterialRegion','make_exact_material_region',"
            "'make_exact_material_region_from_rationals','empty_exact_material_region',"
            "'make_exact_interior_difference_region','check_exact_material_partition',"
            "'check_exact_material_subset','relate_exact_material_regions',"
            "'check_exact_boundary_clearance','SpinTriangulationSettings'); "
            "assert all(hasattr(core,n) for n in required); "
            "assert hasattr(loaded['_cherchi_core_boolean'],'boolean'); "
            "arithmetic=loaded['_cherchi_rational_moments']; "
            "assert arithmetic.arithmetic_identity=="
            "'DIV_SURFACE_V1_REYNOLDS_V1_GMP_BINARY64_NEAREST_EVEN_V1'; "
            "assert all(hasattr(arithmetic,n) for n in ('integrate_moments','PreparedBoundary')); "
            "from make_it_stand.verification.spin_problem import SpinArtifactProblem,MeshSnapshot; "
            "from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator; "
            "print(json.dumps({'imports_verified':True,'geometry_calls':0,"
            "'module_files':{n:m.__file__ for n,m in loaded.items()},"
            "'required_core_api':required,'gmp_version':arithmetic.gmp_version}))"
        )
        self.report["import_probe"] = json.loads(self.run("import-only", [self.python, "-c", probe], env=probe_env))
        for name, record in modules.items():
            if sha256(Path(record["path"])) != record["sha256"]:
                raise ValueError("native ELF changed after import: " + name)
        self.report["native_modules"] = modules
        self.report["runtime_environment"] = {"PYTHONPATH": pythonpath,
            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
        final = {}
        for name, identity in repositories.items():
            final[name] = self.identity(name + "-after", Path(identity["path"]), identity["head"])
            if final[name] != identity:
                raise ValueError("source identity changed during build: " + name)
            if name != "core" and self.git(name + "-status-after", Path(identity["path"]),
                                            "status", "--porcelain=v1"):
                raise ValueError("dependency checkout changed during build: " + name)
        self.check_untracked("source-untracked-after")
        if sha256(Path(__file__).resolve(strict=True)) != self.report["builder_script_sha256"]:
            raise ValueError("build orchestrator changed during execution")
        self.report["repositories_after"] = final
        self.report["status"] = "BUILT_AND_IMPORT_VERIFIED_NO_GEOMETRY"

    def finish(self):
        self.report["wall_seconds"] = time.monotonic() - self.started
        self.report["child_process_maxrss_bytes"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024
        self.report["maxrss_scope"] = "Linux maximum resident size of a waited child process; not aggregate host RSS"
        self.report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        for step in self.report["steps"]:
            path = self.evidence / step["log"]
            if path.is_file():
                step["log_sha256"] = sha256(path)
        output = self.evidence / "P20_NATIVE_BUILD_REPORT.json"
        output.write_text(json.dumps(self.report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"status": self.report["status"], "report": str(output),
                          "report_sha256": sha256(output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-checkout", type=Path, required=True)
    parser.add_argument("--build-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--ninja", default="ninja")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--timeout-seconds", type=int, default=3540)
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 3540:
        parser.error("timeout must be 1..3540 seconds, reserving 60 seconds for evidence cleanup")
    build = Build(args)
    try:
        build.execute()
    except BaseException as error:
        build.report["status"] = "FAILED_CLOSED"
        build.report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        build.finish()


if __name__ == "__main__":
    main()
