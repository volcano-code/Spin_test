from pathlib import Path
import pytest
from source.restore_v4_proxy import restore


def test_full_archived_proxy_round_trip(tmp_path):
    path=tmp_path/'frozen.json'
    result=restore(path)
    assert path.stat().st_size==931258
    assert result['sha256']=='fa0a7eac8046be48fbfac495c7e6e283ebe7033d6242b64997aa28216b5c92f4'
    assert 'NOT_ORIGINAL_EVAL60' in result['classification']


def test_refuse_to_replace_existing_input(tmp_path):
    path=tmp_path/'frozen.json';restore(path)
    with pytest.raises(ValueError,match='FRESH_OUTPUT'):
        restore(path)


def test_corrupted_archive_fails_closed(tmp_path):
    corrupted=tmp_path/'archive.b64'
    corrupted.write_text('AAAA\n')
    with pytest.raises(Exception):restore(tmp_path/'frozen.json',corrupted)
    assert not (tmp_path/'frozen.json').exists()
