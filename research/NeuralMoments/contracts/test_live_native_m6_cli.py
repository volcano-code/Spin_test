"""CLI resource veto and no-overwrite policy; never executes a Cherchi job."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from . import live_native_m6_cli as cli
from .native_teacher_replay import ReplayRejected


def small():return dict(physical_memory_gib=5.8,swap_kib=0)


def test_real_container_preflight_blocks_native_without_importing_factory(tmp_path):
    output=tmp_path/'native_block.json'
    with patch.object(cli,'linux_resources',return_value=small()), \
         patch.object(cli,'_run_worker',side_effect=AssertionError('MUST_NOT_RUN')):
        code=cli.main(['--factory','fake:factory','--pins','not_created.json',
                       '--output',str(output)])
    assert code==3
    record=json.loads(output.read_text())
    assert record['status']=='BLOCKED_INSUFFICIENT_PHYSICAL_RAM'
    assert record['training_admissible'] is False
    assert record['native_full_partition_certified'] is False


def test_no_overwrite_existing_failure_report(tmp_path):
    dest=tmp_path/'keep.json'
    dest.write_text('PRESERVE_FAILED_HISTORICAL_EVIDENCE')
    assert cli.main(['--factory','fake:factory','--pins','none',
                     '--output',str(dest)])==4
    assert dest.read_text()=='PRESERVE_FAILED_HISTORICAL_EVIDENCE'


def test_report_written_exclusively(tmp_path):
    p=tmp_path/'evidence.json';record={'status':'BLOCKED','training_admissible':False}
    cli._emit(str(p),record)
    assert json.loads(p.read_text())==record
    with pytest.raises(ReplayRejected,match='NO_OVERWRITE'):
        cli._emit(str(p),record)


@pytest.mark.parametrize('invalid',['bad','justmodule:','bad.module!:name','a:b-b'])
def test_untrusted_factory_string_rejected(invalid):
    with pytest.raises(ReplayRejected): cli._trusted_factory(invalid)


def test_run_worker_requires_precommitted_pins(tmp_path):
    bad=tmp_path/'pins.json';bad.write_text('{}')
    args=type('Args',(),{'factory':'not_installed:prepare','pins':str(bad)})()
    with pytest.raises(ReplayRejected,match='PIN_SET'):
        cli._run_worker(args)


def test_swap_rejected_before_import(tmp_path):
    out=tmp_path/'swap.json'
    with patch.object(cli,'linux_resources',return_value={'physical_memory_gib':24.,'swap_kib':1024}):
        code=cli.main(['--factory','never:touch','--pins','missing','--output',str(out)])
    assert code==3
    assert json.loads(out.read_text())['status']=='BLOCKED_NONZERO_SWAP'
