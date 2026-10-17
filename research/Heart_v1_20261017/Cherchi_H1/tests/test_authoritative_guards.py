"""Never replay exact registered eval60 on a substituted proxy input."""
from pathlib import Path
import json,hashlib,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from run_authoritative_eval60_cherchi import authenticate


def reg(tmp_path):
    con=tmp_path/'configuration.json';con.write_text(json.dumps({'request':{},'evaluator':{}}))
    events=tmp_path/'events.jsonl';events.write_text('test event\n')
    registration=tmp_path/'reg.json'
    reg={'configuration_sha256':hashlib.sha256(con.read_bytes()).hexdigest(),
         'events_sha256':hashlib.sha256(events.read_bytes()).hexdigest(),
         'event':{'evaluation_index':60,'reason':'evaluation_exception'}}
    registration.write_text(json.dumps(reg))
    return registration,con,events

def test_match_registrations(tmp_path):
    assert authenticate(*reg(tmp_path))[0]['event']['evaluation_index']==60

def test_missing_events_refuse(tmp_path):
    a,b,c=reg(tmp_path);c.unlink()
    with pytest.raises(FileNotFoundError,match='MISSING_ORIGINAL_EVAL60_EVENTS'):
        authenticate(a,b,c)

def test_tampered_configuration_refuse(tmp_path):
    a,b,c=reg(tmp_path);b.write_text('tampered')
    with pytest.raises(ValueError,match='ORIGINAL_EVAL60_CONFIGURATION_SHA256_MISMATCH'):
        authenticate(a,b,c)

def test_tampered_events_refuse(tmp_path):
    a,b,c=reg(tmp_path);c.write_text('different')
    with pytest.raises(ValueError,match='ORIGINAL_EVAL60_EVENTS_SHA256_MISMATCH'):
        authenticate(a,b,c)

def test_wrong_event_refuse(tmp_path):
    a,b,c=reg(tmp_path);data=json.loads(a.read_text());data['event']['evaluation_index']=59;a.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='WRONG_EVAL60_REGISTRATION'):
        authenticate(a,b,c)
