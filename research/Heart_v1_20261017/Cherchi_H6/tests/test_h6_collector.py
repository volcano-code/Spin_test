from pathlib import Path
import pytest
from source.collect_original_eval60 import collect

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/'input/registered-eval60-coefficients.json'

def test_missing_authentic_run_cannot_be_collected(tmp_path):
    output=tmp_path/'would_be_frozen.zip'
    with pytest.raises(ValueError,match='MISSING_AUTHENTIC_HEART_EVAL60_FILES'):
        collect(tmp_path/'nonexistent_original_run',REG,output)
    assert not output.exists()


def test_proxy_config_is_not_valid_original_run(tmp_path):
    from source.restore_v4_proxy import restore
    src=tmp_path/'non_original';src.mkdir()
    restore(src/'configuration.json')
    (src/'events.jsonl').write_text('{}\n')
    with pytest.raises(ValueError,match='AUTHENTIC_HEART_CONFIGURATION_SHA256_MISMATCH'):
        collect(src,REG,tmp_path/'out.zip')
    assert not (tmp_path/'out.zip').exists()
