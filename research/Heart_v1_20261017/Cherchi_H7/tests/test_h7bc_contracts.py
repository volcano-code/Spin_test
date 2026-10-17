"""H7b/H7c pure contract tests: no native replay is implied."""
import json
import sys
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"source"))
from summarize_stage_profile import summarize
from verify_replayed_packets import verify_one_archive, verify_report

def test_profile_summary_two_backends():
    row=lambda s:dict(wall_seconds=s,cpu_seconds=s/2,stages_seconds={"boolean":s/4},
        unattributed_seconds=s*3/4,process_peak_rss_kib=1024)
    doc=dict(schema="heart-h7-stage-profile-v1",scope="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60",
        formal_heart_qualified=False,
        timings={"python":[row(8),row(9),row(10)],"native":[row(2),row(3),row(4)]},
        backend_parity=dict(geometry_hash_equal=True,backend_equal=True,
            moment_max_abs_delta=0.,jacobian_max_abs_delta=0.))
    out=summarize(doc)
    assert out["matched_environment_speed_ratio_python_over_native"]==3
    assert out["arithmetic_backends"]["python"]["wall_median_seconds"]==9
    assert out["formal_native_heart_performance_qualified"] is False

def test_refuse_parity_failure():
    doc=dict(schema="heart-h7-stage-profile-v1",scope="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60",
        formal_heart_qualified=False,timings={
          k:[dict(wall_seconds=2,cpu_seconds=1,stages_seconds={},unattributed_seconds=2,
                  process_peak_rss_kib=1)] for k in ("python","native")},
        backend_parity=dict(geometry_hash_equal=False,backend_equal=True,
            moment_max_abs_delta=0.,jacobian_max_abs_delta=0.))
    with pytest.raises(ValueError,match="MISMATCH"):
        summarize(doc)

def test_no_fabricated_native_or_formal_results():
    with pytest.raises(ValueError,match="FORMAL"):
        summarize(dict(schema="heart-h7-stage-profile-v1",scope="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60",
                       formal_heart_qualified=True,timings={}))
    with pytest.raises(ValueError,match="WALL"):
        summarize(dict(schema="heart-h7-stage-profile-v1",scope="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60",
                       formal_heart_qualified=False,timings={"python":[dict(wall_seconds=0)]}))

def test_replay_archive_verification_requires_actual_archive(tmp_path):
    with pytest.raises(ValueError,match="SHA256_MISMATCH"):
        verify_one_archive(tmp_path/"never-created.gz","0"*64)
    report=tmp_path/"fake-report.json"
    report.write_text(json.dumps(dict(schema="heart-h7b-25point-real-cherchi-proxy-replay-v1",
        scope="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60",original_eval60_verified=True)))
    features=tmp_path/"features.json";features.write_text("{}")
    with pytest.raises(ValueError,match="FORBIDDEN_FORMAL"):
        verify_report(report,features)
