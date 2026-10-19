"""M7 installed-production KKT path: fail-closed interface tests, no real native."""
from pathlib import Path
import hashlib
import types
import pytest
from .native_teacher_replay import ReplayRejected
from .live_original_objective_m7 import _source, recheck_archived_original_objective
from .test_terminal_archive_m7 import make_pinned_archive
from .terminal_archive_m7 import review_pinned_terminal_archive


def test_production_physics_module_missing_is_explicit(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    reviewed=review_pinned_terminal_archive(root,pins)
    with pytest.raises(ReplayRejected,match='SOURCE_UNAVAILABLE'):
        recheck_archived_original_objective(root,reviewed,
            expected_faster_material_sha256='f'*64,
            expected_objective_contract_sha256='a'*64)


@pytest.mark.parametrize('bad', [None,'bad','A'*64,'a'*63,3,True])
def test_source_sha_must_be_externally_frozen(tmp_path,bad):
    with pytest.raises(ReplayRejected,match='EXTERNAL_ORIGINAL_PHYSICS_SOURCE_PIN_REQUIRED'):
        _source('make_it_stand.verification.faster_material',bad)


def test_independent_source_sha_mismatch_veto(monkeypatch,tmp_path):
    from . import live_original_objective_m7 as stage
    f=tmp_path/'source.py';f.write_text('self-contained-frozen-source')
    monkeypatch.setattr(stage.importlib,'import_module',
                        lambda name:types.SimpleNamespace(__file__=str(f)))
    with pytest.raises(ReplayRejected,match='MODULE_SHA_MISMATCH'):
        _source('make_it_stand.verification.faster_material','a'*64)


def test_correctly_pinned_source_gate_is_only_a_source_observation(monkeypatch,tmp_path):
    from . import live_original_objective_m7 as stage
    f=tmp_path/'source.py';f.write_text('self-contained-frozen-source')
    monkeypatch.setattr(stage.importlib,'import_module',
                        lambda name:types.SimpleNamespace(__file__=str(f)))
    obj=_source('make_it_stand.verification.faster_material',
                hashlib.sha256(f.read_bytes()).hexdigest())
    assert obj.__file__==str(f)
    # This is an isolated source-identity mock, not original physical KKT truth.


def test_pure_evidence_cannot_replace_terminal_record(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    with pytest.raises(ReplayRejected,match='PINNED_TERMINAL_ARCHIVE_FIRST'):
        recheck_archived_original_objective(root,{'schema':'fake'},
            expected_faster_material_sha256='a'*64,
            expected_objective_contract_sha256='b'*64)
