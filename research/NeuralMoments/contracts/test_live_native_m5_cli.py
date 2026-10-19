"""Resource preflight, lock and no-native guarantee for W0 M5 worker."""
from __future__ import annotations

import json
import pytest

from .live_native_m5_cli import main, _locked_factory
from .native_teacher_replay import ReplayRejected


def test_actual_low_ram_host_never_imports_trusted_factory(tmp_path):
    from .live_native_teacher_cli import linux_resources, admissible
    if admissible(linux_resources())!='BLOCKED_INSUFFICIENT_PHYSICAL_RAM':
        pytest.skip('requires the actual observed low-RAM sandbox')
    output=tmp_path/'result.json'
    code=main(['--factory','nonexistent_fake_native:prepare_one',
               '--pins',str(tmp_path/'no_pins.json'),'--output',str(output)])
    r=json.loads(output.read_text())
    assert code==3 and r['status']=='BLOCKED_INSUFFICIENT_PHYSICAL_RAM'
    assert r['training_admissible'] is False
    assert not r['full_material_partition_certified']


def test_bad_factory_selector_rejected_without_import(tmp_path):
    from types import SimpleNamespace
    with pytest.raises(ReplayRejected,match='TRUSTED_FACTORY_MODULE_FUNCTION'):
        _locked_factory(SimpleNamespace(factory='not-valid-pair',pins=tmp_path/'not_there.json'))


def test_invalid_factory_function_rejected(tmp_path):
    from types import SimpleNamespace
    with pytest.raises(ReplayRejected,match='TRUSTED_FACTORY_MODULE_FUNCTION'):
        _locked_factory(SimpleNamespace(factory='os:bad-name',pins=tmp_path/'not_there.json'))
