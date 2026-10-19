"""Load the original W6 M6 Gauss/physical-moment source without changing W6.

Every file is pinned to its Git *blob*, not to a self-reported snapshot hash.
No W6 training labels or model weights are imported and no files are written
into the W6 directory. The W6 branch may subsequently advance; these blobs
must be manually reviewed/pinned before any replacement.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from .m7_cross_framework import UntrustedW6Source, git_blob_sha, load_pinned_w6

W6_M6_SOURCE_COMMIT = "27d51678cf741233c7a2e6c54c78d9a4667bec00"
W6_M6_FILES = {
    "m6_gauss_potential.py": "85d0ead6ee0dec9fc3212750e849310230d7878a",
    "m6_moment_guard.py": "9a9f0ae8cd1066c7e401529541387052faf264af",
}


def load_m9_w6(w6_root: str | Path):
    """Return (m4, m5, m6, guard) from a SHA-verified read-only W6 root."""
    root = Path(w6_root).resolve()
    base = root / "research/NeuralMoments/models/pcraft_ufno"
    # Validate new inputs before importing ANY W6 module. Existing M7 loader
    # checks the old pinned M4/M5 source similarly.
    for filename, checksum in W6_M6_FILES.items():
        path = base / filename
        if not path.is_file() or path.is_symlink():
            raise UntrustedW6Source(f"W6_M6_FILE_MISSING_OR_SYMLINK:{filename}")
        if git_blob_sha(path.read_bytes()) != checksum:
            raise UntrustedW6Source(f"W6_M6_BLOB_SHA_MISMATCH:{filename}")
    m4, m5 = load_pinned_w6(root)
    namespace = "_w5_readonly_pcraft_ufno"
    m6 = importlib.import_module(namespace + ".m6_gauss_potential")
    guard = importlib.import_module(namespace + ".m6_moment_guard")
    return m4, m5, m6, guard
