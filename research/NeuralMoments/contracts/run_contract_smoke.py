"""Run exact committed W0 pytest on a checkout of the W0 branch.

No full native solver is launched. Writes a local report; do not interpret
success as Cherchi geometry or Newton terminal certification.
"""
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[3]
    command = [sys.executable, "-m", "pytest", "-q",
               "research/NeuralMoments/contracts"]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    output = {
        "schema": "W0-committed-branch-test-execution-v1",
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "native_cherchi_checked": False,
        "production_Eigen_compiled": False,
        "material_certification": False
    }
    destination = Path.cwd() / "w0_contract_test_execution.json"
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("Evidence:", destination)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
