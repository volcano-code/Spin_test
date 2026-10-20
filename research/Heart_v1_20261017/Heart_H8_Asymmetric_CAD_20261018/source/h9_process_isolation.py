"""W3 child process isolation for expensive native/CMake subprocess trees.

On Linux, `start_new_session` puts the child and conventional descendants in
an isolated process group. Cleanup runs on success, failure, and timeout.
Never treat a timeout as a success. This module does not authenticate a native
Cherchi result or relax the research window's 60-minute / no-swap limits.
"""
from __future__ import annotations

import os
import signal
import subprocess


def run_process_group(argv, *, timeout, cwd=None, env=None, stdout=None,
                      stderr=None, preexec_fn=None):
    """Run argv without a shell; reap/kill its process group on every exit.

    Returns exit code. Raises subprocess.TimeoutExpired (and always attempts
    cleanup) if the child exceeds `timeout`. Unix/Linux-only by design.
    """
    if not isinstance(argv, (list, tuple)) or not argv or not all(
        isinstance(x, (str, os.PathLike)) and str(x) for x in argv
    ):
        raise ValueError('INVALID_NATIVE_SUBPROCESS_ARGV')
    if not isinstance(timeout, (int, float)) or not (0 < timeout <= 3600):
        raise ValueError('INVALID_OR_OVERLONG_NATIVE_SUBPROCESS_TIMEOUT')
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                            preexec_fn=preexec_fn, start_new_session=True,
                            shell=False)
    try:
        return proc.wait(timeout=timeout)
    finally:
        # Even if the leader exits, never leave detached compiler children
        # running in the same process group. start_new_session guarantees this
        # is not the ChatGPT/current shell's process group.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # The leader should already be gone after group SIGKILL. Never
            # invent a successful exit if the OS cannot reap it promptly.
            raise RuntimeError('W3_CHILD_PROCESS_NOT_REAPED_AFTER_KILL')
