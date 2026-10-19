"""Resource and serialization tests; they do not run native Cherchi."""
import json
from pathlib import Path
import subprocess
import sys
import pytest

from .live_native_teacher_cli import admissible, linux_resources
from .native_teacher_replay import ReplayRejected


def test_host_admission_under_charter_ram():
    r=linux_resources('MemTotal: 6090680 kB\nSwapTotal: 0 kB\n')
    assert admissible(r)=='BLOCKED_INSUFFICIENT_PHYSICAL_RAM'


def test_charter_nominal_host_can_pass_resource_only():
    r=linux_resources('MemTotal: 24576000 kB\nSwapTotal: 0 kB\n')
    assert admissible(r)=='ADMITTED_RESOURCE_POLICY_ONLY'


def test_swapped_host_is_blocked():
    r=linux_resources('MemTotal: 30000000 kB\nSwapTotal: 1024 kB\n')
    assert admissible(r)=='BLOCKED_NONZERO_SWAP'


def test_malformed_resource_reports_rejected():
    with pytest.raises(ReplayRejected,match='HOST_RESOURCE'):
        linux_resources('MemTotal: 25000000 kB')


def test_actual_host_no_native_execution_and_report(tmp_path):
    # The current isolated environment is <20GiB and missing native .so;
    # a report must show that no teacher call was made.
    from .live_native_teacher_cli import main
    if admissible(linux_resources())!='BLOCKED_INSUFFICIENT_PHYSICAL_RAM':
        pytest.skip('host capacity changed: would require configured real fixture')
    pins=tmp_path/'pins.json';pins.write_text('{}',encoding='utf8')
    report=tmp_path/'audit.json'
    code=main(['--factory','no_such_native_factory:produce','--pins',str(pins),
               '--output',str(report)])
    assert code==3
    record=json.loads(report.read_text())
    assert record['status']=='BLOCKED_INSUFFICIENT_PHYSICAL_RAM'
    assert record['training_admissible'] is False
    assert record['true_cherchi_material_certified'] is False
