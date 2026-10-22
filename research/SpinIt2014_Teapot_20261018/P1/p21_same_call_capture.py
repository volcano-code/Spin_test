"""Durable observation of the unchanged Cherchi evaluator's existing stages.

This module never evaluates geometry by itself.  The evaluator calls the
observer with its original operation; that operation is executed exactly once
and its original return object is passed back unchanged.  Captured bytes make
an actual M6 run replayable, but cannot independently establish native origin,
a full material partition, or any scientific/owner/training admission.

Only this new run's manifest is atomically refreshed.  Context and stage
artifacts are exclusive files; events are an fsynced append-only JSONL stream.
Opaque native objects, including PreparedBoundary, are never serialized or
represented with repr().
"""
from __future__ import annotations

from collections import Counter
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import threading
import time
import uuid


MANIFEST_SCHEMA = 'W4_P21_SAME_CALL_CAPTURE_MANIFEST_V1'
EVENT_SCHEMA = 'W4_P21_STAGE_EVENT_V1'
CONTEXT_SCHEMA = 'W4_P21_SAME_CALL_CONTEXT_V1'
CAPTURE_ENVIRONMENT_VARIABLE = 'W4_P21_CAPTURE_DIRECTORY'
STAGE_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,95}\Z')
ADMISSION = {
    'W0_owner_admitted': False,
    'W2_teacher_training_allowed': False,
    'derivative_neighborhood_certified': False,
    'Faster_optimization_executed': False,
    'physical_validation_passed': False,
    'MuJoCo_optimized_before_after_executed': False,
    'original_author_CAD': False,
}
JSON_STAGES = {
    'source': 'source_result',
    'boolean': 'boolean_packet',
    'intersection_motion': 'intersection_motion',
    'physical_source_boundary': 'physical_source_boundary',
}
ARRAY_STAGES = {
    'derivative': ('derivative_f64le', (10, 10)),
    'integration': ('integration_f64le', (10,)),
}


class CaptureRejected(ValueError):
    """The capture target, payload or observer protocol is invalid."""


def _need(condition, reason):
    if not condition:
        raise CaptureRejected(reason)


def _qualified_type(value):
    cls = type(value)
    return cls.__module__ + '.' + cls.__qualname__


def _safe_absolute_path(value):
    path = Path(os.fspath(value))
    _need(path.is_absolute(), 'P21_ABSOLUTE_CAPTURE_PATH_REQUIRED')
    _need('..' not in path.parts, 'P21_CAPTURE_PATH_TRAVERSAL')
    for item in (path, *path.parents):
        _need(not item.is_symlink(), 'P21_CAPTURE_SYMLINK_PATH:' + str(item))
    return path


def _json_ready(value):
    """Convert known numerical containers without accepting arbitrary objects."""
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        _need(math.isfinite(value), 'P21_NONFINITE_CAPTURE_VALUE')
        return value
    if type(value) in (list, tuple):
        return [_json_ready(item) for item in value]
    if type(value) is dict:
        _need(all(type(key) is str for key in value), 'P21_STRING_JSON_KEYS_REQUIRED')
        return {key: _json_ready(item) for key, item in value.items()}
    # Importing numpy performs no project-native or geometry work.  Do not
    # invoke a generic tolist/item/array/repr protocol on untrusted objects.
    import numpy as np
    if isinstance(value, np.ndarray):
        _need(value.dtype.kind in ('b', 'i', 'u', 'f'), 'P21_UNSUPPORTED_NUMPY_DTYPE')
        return _json_ready(value.tolist())
    if isinstance(value, np.generic):
        _need(value.dtype.kind in ('b', 'i', 'u', 'f'), 'P21_UNSUPPORTED_NUMPY_SCALAR')
        return _json_ready(value.item())
    raise CaptureRejected('P21_UNSUPPORTED_JSON_CAPTURE_TYPE:' + _qualified_type(value))


def _json_bytes(value):
    return (json.dumps(_json_ready(value), sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def _strict_json(data):
    def pairs(rows):
        out = {}
        for key, value in rows:
            _need(key not in out, 'P21_DUPLICATE_MATERIAL_JSON_KEY:' + key)
            out[key] = value
        return out
    def nonfinite(token):
        raise CaptureRejected('P21_NONFINITE_MATERIAL_JSON:' + token)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def source_file_record(path):
    path = _safe_absolute_path(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        _need(stat.S_ISREG(before.st_mode), 'P21_REGULAR_PRODUCER_FILE_REQUIRED')
        data = stream.read()
        after = os.fstat(stream.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    _need(identity(before) == identity(after) == identity(path.stat()),
          'P21_PRODUCER_FILE_CHANGED_DURING_READ')
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


class CaptureSession:
    """Single-worker, same-return-object stage observer for one new run."""

    def __init__(self, directory, context=None):
        self.directory = _safe_absolute_path(directory)
        _need(self.directory.parent.is_dir(), 'P21_CAPTURE_PARENT_DIRECTORY_REQUIRED')
        _need(not self.directory.exists(), 'P21_CAPTURE_DIRECTORY_ALREADY_EXISTS')
        self.directory.mkdir(mode=0o700)
        _fsync_directory(self.directory.parent)
        self._directory_identity = (self.directory.stat().st_dev, self.directory.stat().st_ino)
        self._pid = os.getpid()
        self._thread = threading.get_ident()
        self._sequence = 0
        self._call_index = 0
        self._attempts = Counter()
        self._completed = Counter()
        self._counter_provider = None
        self._active = False
        self._context = None
        self._event_bytes = 0
        self._event_hash = hashlib.sha256()
        self._started = time.monotonic()
        self._events_path = self.directory / 'events.jsonl'
        self._new_file('events.jsonl', b'', 'events')
        self._manifest = {
            'schema': MANIFEST_SCHEMA,
            'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'writer_pid': self._pid,
            'state': 'factory_preparing',
            'context': None,
            'events': self._events_record(),
            'event_count': 0,
            'operation_attempt_counts': {},
            'completed_stage_counts': {},
            'counter_semantics': 'Evaluator counters count attempted stages; only completed events prove an operation returned.',
            'codefiles': {'capture_module': source_file_record(Path(__file__).absolute())},
            'admission': dict(ADMISSION),
            'formal_M6_outcome_authority': 'UNCHANGED_P20_LAUNCHER_AND_PINNED_W0_AUDIT_ONLY',
            'captures_are_not_independent_native_origin_or_M6_proof': True,
            'scope': 'PASSIVE_SAME_CALL_CAPTURE_ONLY',
        }
        self._write_manifest(initial=True)
        if context is not None:
            self.bind_context(context)

    def _check_owner(self):
        _need(os.getpid() == self._pid and threading.get_ident() == self._thread,
              'P21_CAPTURE_SINGLE_PROCESS_THREAD_REQUIRED')
        _safe_absolute_path(self.directory)
        current = self.directory.stat()
        _need(stat.S_ISDIR(current.st_mode) and
              (current.st_dev, current.st_ino) == self._directory_identity,
              'P21_CAPTURE_DIRECTORY_IDENTITY_CHANGED')

    def _new_file(self, name, data, role, **extra):
        self._check_owner()
        _need(type(name) is str and Path(name).name == name and name not in ('.', '..'),
              'P21_CAPTURE_ARTIFACT_BASENAME_REQUIRED')
        _need(type(data) is bytes, 'P21_CAPTURE_BYTES_REQUIRED')
        path = self.directory / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(self.directory)
        return {'role': role, 'path': name, 'sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data), **extra}

    def _events_record(self):
        return {'role': 'events', 'path': 'events.jsonl',
                'sha256': self._event_hash.hexdigest(), 'bytes': self._event_bytes}

    def _write_manifest(self, *, initial=False):
        self._manifest.update(events=self._events_record(), event_count=self._sequence,
                              operation_attempt_counts=dict(self._attempts),
                              completed_stage_counts=dict(self._completed))
        payload = _json_bytes(self._manifest)
        if initial:
            self._new_file('manifest.json', payload, 'capture_manifest')
            return
        self._check_owner()
        manifest_path = self.directory / 'manifest.json'
        _need(not manifest_path.is_symlink() and manifest_path.is_file(),
              'P21_CAPTURE_MANIFEST_IDENTITY_INVALID')
        temporary = '.manifest-' + uuid.uuid4().hex + '.tmp'
        self._new_file(temporary, payload, 'temporary_manifest')
        os.replace(self.directory / temporary, manifest_path)
        _fsync_directory(self.directory)

    def _event(self, *, phase, stage, event, **details):
        self._check_owner()
        self._sequence += 1
        row = {'schema': EVENT_SCHEMA, 'seq': self._sequence,
               'phase': phase, 'stage': stage, 'event': event,
               'capture_elapsed_seconds': time.monotonic() - self._started,
               **details}
        data = _json_bytes(row)
        descriptor = os.open(self._events_path, os.O_WRONLY | os.O_APPEND |
                             getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'ab') as stream:
            observed = os.fstat(stream.fileno())
            _need(stat.S_ISREG(observed.st_mode) and observed.st_size == self._event_bytes,
                  'P21_EVENT_STREAM_CHANGED')
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        self._event_hash.update(data)
        self._event_bytes += len(data)
        self._write_manifest()
        return row

    def factory_event(self, event, **details):
        _need(event in ('begin', 'completed', 'failed'), 'P21_FACTORY_EVENT_INVALID')
        if event == 'failed':
            self._manifest['state'] = 'factory_failed'
        return self._event(phase='factory', stage='prepare_one', event=event, **details)

    def observe_preparation(self, row):
        """P20 factory's existing progress callback; no wrapped operations."""
        _need(type(row) is dict and row.get('event') in ('start', 'completed', 'failed'),
              'P21_PREPARATION_EVENT_INVALID')
        stage = row.get('stage')
        _need(type(stage) is str and STAGE_NAME.fullmatch(stage), 'P21_PREPARATION_STAGE_INVALID')
        details = {key: value for key, value in row.items() if key not in ('event', 'stage')}
        return self._event(phase='factory_preparation', stage=stage,
                           event='begin' if row['event'] == 'start' else row['event'], **details)

    def bind_context(self, context):
        self._check_owner()
        _need(self._context is None, 'P21_CONTEXT_ALREADY_BOUND')
        _need(type(context) is dict, 'P21_CONTEXT_OBJECT_REQUIRED')
        if 'schema' in context:
            _need(context['schema'] == CONTEXT_SCHEMA, 'P21_CONTEXT_SCHEMA_INVALID')
        complete = {'schema': CONTEXT_SCHEMA, **context}
        payload = _json_bytes(complete)
        self._context = self._new_file('context.json', payload, 'context')
        self._manifest['context'] = dict(self._context)
        self._write_manifest()
        return dict(self._context)

    def attach_counter_provider(self, provider):
        _need(callable(provider) and self._counter_provider is None,
              'P21_SINGLE_COUNTER_PROVIDER_REQUIRED')
        self._counter_provider = provider

    def _counts(self):
        if self._counter_provider is None:
            return None
        result = self._counter_provider()
        _need(type(result) is dict and all(type(k) is str and type(v) is int and v >= 0
                                         for k, v in result.items()),
              'P21_INVALID_EVALUATOR_ATTEMPT_COUNTERS')
        return dict(result)

    def mark_factory_ready(self):
        _need(self._context is not None, 'P21_READY_FACTORY_REQUIRES_CONTEXT')
        self._manifest['state'] = 'factory_ready'
        self.factory_event('completed', evaluator_attempt_counts=self._counts(),
                           formal_source_or_boolean_started=False)

    def _capture_result(self, stage, prefix, result):
        if stage in JSON_STAGES:
            return [self._new_file(prefix + '.json', _json_bytes(result), JSON_STAGES[stage],
                                   encoding='json', result_type=_qualified_type(result))]
        if stage in ARRAY_STAGES:
            import numpy as np
            role, shape = ARRAY_STAGES[stage]
            _need(isinstance(result, np.ndarray) and result.dtype.kind == 'f' and
                  result.dtype.itemsize == 8 and result.shape == shape,
                  'P21_ACTUAL_BINARY64_ARRAY_SHAPE_REQUIRED:' + stage)
            _need(bool(np.isfinite(result).all()), 'P21_NONFINITE_STAGE_ARRAY:' + stage)
            # Iterating exact binary64 scalars followed by struct.pack preserves
            # all finite bits, including negative zero, across byte order/layout.
            data = struct.pack('<' + 'd' * result.size,
                               *(float(x) for x in result.flat))
            return [self._new_file(prefix + '.f64le', data, role,
                                   encoding='IEEE754_BINARY64_LITTLE_ENDIAN',
                                   shape=list(shape), order='C', dtype='<f8')]
        if stage == 'material_attachment_serialization':
            _need(type(result) is str, 'P21_EXACT_MATERIAL_SERIALIZATION_STRING_REQUIRED')
            parsed = _strict_json(result)
            _need(type(parsed) is dict, 'P21_SERIALIZED_MATERIAL_OBJECT_REQUIRED')
            _json_ready(parsed)  # Reject overflowing JSON exponents as well as NaN tokens.
            return [self._new_file(prefix + '.json', result.encode('utf-8'), 'retained_material',
                                   encoding='EXACT_EVALUATOR_UTF8_JSON_BYTES',
                                   result_type='builtins.str')]
        # Recording the concrete type is safe for PreparedBoundary and other
        # opaque native objects.  Do not inspect, repr, copy or serialize them.
        return []

    def __call__(self, stage, operation):
        self._check_owner()
        _need(type(stage) is str and STAGE_NAME.fullmatch(stage), 'P21_INVALID_STAGE_NAME')
        _need(callable(operation), 'P21_STAGE_OPERATION_REQUIRED')
        _need(self._context is not None, 'P21_NATIVE_STAGE_REQUIRES_BOUND_CONTEXT')
        _need(not self._active, 'P21_REENTRANT_STAGE_OBSERVER_NOT_ALLOWED')
        self._active = True
        self._call_index += 1
        self._attempts[stage] += 1
        ordinal, call_index = self._attempts[stage], self._call_index
        common = {'ordinal': ordinal, 'call_index': call_index}
        self._manifest['state'] = 'capturing'
        try:
            self._event(phase='native_stage', stage=stage, event='begin',
                        evaluator_attempt_counts=self._counts(), **common)
            started = time.monotonic()
            try:
                result = operation()  # The sole invocation of the original operation.
            except BaseException as error:
                self._manifest['state'] = 'stage_failed'
                self._event(phase='native_stage', stage=stage, event='failed',
                            operation_returned=False, elapsed_seconds=time.monotonic() - started,
                            error_type=_qualified_type(error), error=str(error),
                            evaluator_attempt_counts=self._counts(), artifacts=[], **common)
                raise
            elapsed = time.monotonic() - started
            prefix = f'{call_index:06d}-{stage}-{ordinal:03d}'
            try:
                artifacts = self._capture_result(stage, prefix, result)
            except BaseException as error:
                self._manifest['state'] = 'capture_failed'
                self._event(phase='native_stage', stage=stage, event='failed',
                            operation_returned=True, elapsed_seconds=elapsed,
                            error_type=_qualified_type(error), error=str(error),
                            evaluator_attempt_counts=self._counts(), artifacts=[], **common)
                raise
            self._completed[stage] += 1
            self._event(phase='native_stage', stage=stage, event='completed',
                        operation_returned=True, elapsed_seconds=elapsed,
                        result_type=_qualified_type(result), artifacts=artifacts,
                        evaluator_attempt_counts=self._counts(), **common)
            return result
        finally:
            self._active = False
