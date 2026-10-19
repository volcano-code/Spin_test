"""Realistic multi-evaluation journal fixtures; NOT native solver data."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest

from .native_teacher_replay import ReplayRejected, digest
from .terminal_archive_m7 import review_pinned_terminal_archive
from .test_terminal_archive_m7 import make_pinned_archive, _save, C


def build_multistep(tmp_path):
    root, external = make_pinned_archive(tmp_path)
    pins = external['files']
    previous = json.loads((root / 'evaluation-000001.json').read_text())
    terminal = copy.deepcopy(previous)
    # Every saved native evaluation must be pinned, not only the final one.
    initial_c = [0., 0., 0., -1., 0., 0., 0., 0., 0., 0.]
    previous['quadric_coefficients'] = initial_c
    previous['quadric_source_identity'] = digest(dict(
        vertices=previous['quadric_source_vertices'],
        faces=previous['quadric_source_faces'], coefficients=initial_c))
    pins['evaluation-000001.json'] = _save(root, 'evaluation-000001.json', previous)
    pins['evaluation-000002.json'] = _save(root, 'evaluation-000002.json', terminal)

    native = json.loads((root / 'native-result.json').read_text())
    run = native['native_run']
    first = copy.deepcopy(run['events'][1]); first['quadric_coefficients'] = initial_c
    second = copy.deepcopy(run['events'][1]); second['evaluation_index'] = 2
    run['function_evaluations'] = 2
    run['events'] = [run['events'][0], first, second,
                     dict(type='attempt_terminal', reason='converged', restart=0,
                          evaluation_index=2)]
    pins['native-result.json'] = _save(root, 'native-result.json', native)
    result = json.loads((root / 'result.json').read_text())
    result['identity']['native_run'] = copy.deepcopy(run)
    pins['result.json'] = _save(root, 'result.json', result)
    done = json.loads((root / 'complete.json').read_text())
    done['evaluation_count'] = 2
    pins['complete.json'] = _save(root, 'complete.json', done)
    terminal_ref = json.loads((root / 'terminal-material-reference.json').read_text())
    terminal_ref['evaluation_file'] = 'evaluation-000002.json'
    terminal_ref['sha256'] = pins['evaluation-000002.json']
    pins['terminal-material-reference.json'] = _save(root, 'terminal-material-reference.json', terminal_ref)
    comp_ref = json.loads((root / 'terminal-complement-reference.json').read_text())
    comp_ref['retained_reference_sha256'] = pins['terminal-material-reference.json']
    pins['terminal-complement-reference.json'] = _save(root, 'terminal-complement-reference.json', comp_ref)
    saved = [dict(kind='MAP_SAVED', evaluation=i, evaluation_file=f'evaluation-{i:06d}.json',
                  coefficients=initial_c if i==1 else C,
                  geometry_hash=previous['geometry_hash'] if i==1 else terminal['geometry_hash'],
                  sha256=pins[f'evaluation-{i:06d}.json']) for i in (1,2)]
    events = [dict(kind='NEWTON_EVENT', event=e) for e in run['events']]
    events.extend(saved)
    events.append(dict(kind='RUN_TERMINATED', status='CONVERGED', evaluation_count=2))
    pins['events.jsonl'] = _save(root, 'events.jsonl', events)
    return root, external


def test_two_pinned_saved_evaluations_pass_as_numeric_only(tmp_path):
    root,pins=build_multistep(tmp_path)
    result=review_pinned_terminal_archive(root,pins)
    assert result['pinned_saved_evaluation_count']==2
    assert result['mapped_evaluation_count']==2
    assert result['numerical_terminal_record_consistent'] is True
    assert result['training_admissible'] is False


def test_nonterminal_unpinned_or_missing_file_rejected(tmp_path):
    root,pins=build_multistep(tmp_path)
    pins['files'].pop('evaluation-000001.json')
    with pytest.raises(ReplayRejected, match='MISSING_OR_UNPINNED_NEWTON_EVALUATION'):
        review_pinned_terminal_archive(root,pins)


def test_pinned_but_unreferenced_extra_evaluation_rejected(tmp_path):
    root,pins=build_multistep(tmp_path)
    mat=(root/'evaluation-000001.json').read_bytes()
    name='evaluation-000003.json'
    (root/name).write_bytes(mat)
    import hashlib
    pins['files'][name]=hashlib.sha256(mat).hexdigest()
    with pytest.raises(ReplayRejected, match='UNREFERENCED_PINNED_EVALUATION'):
        review_pinned_terminal_archive(root,pins)


def test_saved_map_attachment_mismatch_rejected_even_if_local_pin_rebased(tmp_path):
    root,pins=build_multistep(tmp_path)
    rows=[json.loads(s) for s in (root/'events.jsonl').read_text().splitlines()]
    saved=[x for x in rows if x['kind']=='MAP_SAVED']
    saved[0]['coefficients']=[0.,0.,0.,1.,0.,0.,0.,0.,0.,0.]
    pins['files']['events.jsonl']=_save(root,'events.jsonl',rows)
    with pytest.raises(ReplayRejected, match='NONTERMINAL_EVALUATION_ATTACHMENT_MISMATCH'):
        review_pinned_terminal_archive(root,pins)


def test_missing_second_map_event_rejected(tmp_path):
    root,pins=build_multistep(tmp_path)
    rows=[json.loads(s) for s in (root/'events.jsonl').read_text().splitlines()]
    rows=[x for x in rows if not (x['kind']=='MAP_SAVED' and x['evaluation']==2)]
    pins['files']['events.jsonl']=_save(root,'events.jsonl',rows)
    with pytest.raises(ReplayRejected, match='NONCONTIGUOUS_NEWTON_MAP_CHECKPOINTS'):
        review_pinned_terminal_archive(root,pins)
