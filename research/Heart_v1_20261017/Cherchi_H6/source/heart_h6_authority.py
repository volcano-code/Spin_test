"""Strict identity gating of the historical, non-public Heart eval60 operands.

An archived V4 surrogate and a recalled ten-vector never substitute for the
full frozen run: both original byte-identical configuration.json and
 events.jsonl are required. No network retrieval, guessing, or CFD/CGAL fallback.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

EXPECTED = {
    'registration': '41ede665d8915bcae4d14ee1fa685e475b539c480dd65e643200bc14f319c2f2',
    'configuration': '071c799c92b522fb3d4de4b9aacf9a9ae8bcae102a49940f33f4037f28a74141',
    'events': '2333a9e3c87d9e6b7d3a73676fe9bd940f6e500c9c20b7ce34867d2475269b70',
    'v4_proxy': 'fa0a7eac8046be48fbfac495c7e6e283ebe7033d6242b64997aa28216b5c92f4',
}

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_frozen_eval60(registration, configuration, events):
    """Return accepted *identity* only; caller still needs production evaluation.

    Never use an older V4 geometry when a required run file is unavailable.
    """
    paths = {
        'registration': Path(registration),
        'configuration': Path(configuration),
        'events': Path(events),
    }
    missing = [name for name,p in paths.items() if not p.is_file()]
    if missing:
        raise ValueError('MISSING_AUTHENTIC_HEART_EVAL60_FILES:' + ','.join(missing))
    for name,p in paths.items():
        if sha256(p) != EXPECTED[name]:
            raise ValueError('AUTHENTIC_HEART_' + name.upper() + '_SHA256_MISMATCH')
    reg = json.loads(paths['registration'].read_text())
    config = json.loads(paths['configuration'].read_text())
    if reg.get('configuration_sha256') != EXPECTED['configuration'] or reg.get('events_sha256') != EXPECTED['events']:
        raise ValueError('REGISTERED_HEART_RUN_BINDING_CHANGED')
    if reg.get('event',{}).get('evaluation_index') != 60:
        raise ValueError('NOT_THE_REGISTERED_EVAL60')
    if 'request' not in config or 'evaluator' not in config:
        raise ValueError('AUTHENTIC_HEART_CONFIG_NOT_A_FORMAL_CHERCHI_RUN')
    # Identity only. The original Newton event ledger and exact request source
    # must still be independently parsed and compared by the native runner.
    return {'scope': 'ORIGINAL_HEART_EVAL60_DIGESTS_VERIFIED_ONLY',
            'configuration_sha256': EXPECTED['configuration'],
            'events_sha256': EXPECTED['events'],
            'registration_sha256': EXPECTED['registration'],
            'normal_solver_completed': False,
            'same_call_cherchi_certified': False}

def verify_v4_proxy(fixture,registration):
    for key,path in [('v4_proxy',fixture),('registration',registration)]:
        if not Path(path).is_file():
            raise ValueError('MISSING_PROXY_SOURCE:' + key)
        if sha256(path)!=EXPECTED[key]:
            raise ValueError('ARCHIVED_PROXY_SHA256_MISMATCH:' + key)
    data=json.loads(Path(fixture).read_text())
    reg=json.loads(Path(registration).read_text())
    if data.get('classification') not in ('RECONSTRUCTED_METHOD_VALIDATION','RECONSTRUCTED_ASSET'):
        # A frozen historical V4 request may use different classification;
        # only hash-authenticated, explicitly proxy-labelled input is allowed.
        if 'V4' not in str(data.get('schema','')).upper() and 'V4' not in str(data.get('revision_reason','')).upper():
            raise ValueError('NOT_EXPLICIT_ARCHIVED_V4_INPUT')
    if reg.get('event',{}).get('evaluation_index')!=60:
        raise ValueError('PROXY_COEFFICIENTS_NOT_REGISTERED_EVAL60')
    return data,reg
