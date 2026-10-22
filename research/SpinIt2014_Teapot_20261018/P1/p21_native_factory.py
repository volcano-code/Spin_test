"""P21 formal-M6 factory: unchanged P20 preparation with passive stage capture.

Use the immutable P20 launcher and genuine pinned W0 M6 audit.  This factory
does not evaluate the returned object, does not subclass or patch its methods,
and does not reconstruct either Cherchi Boolean.  Its new capture directory
must be supplied as W4_P21_CAPTURE_DIRECTORY and must not already exist.
"""
from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
import sys

from p21_same_call_capture import (
    ADMISSION, CAPTURE_ENVIRONMENT_VARIABLE, CaptureRejected, CaptureSession,
    source_file_record,
)


def prepare_one():
    directory = os.environ.get(CAPTURE_ENVIRONMENT_VARIABLE)
    if not directory:
        raise CaptureRejected('P21_CAPTURE_DIRECTORY_ENVIRONMENT_REQUIRED')
    session = CaptureSession(directory)
    session.factory_event('begin', purpose='FORMAL_M6_FACTORY_PREPARATION_ONLY')
    try:
        import p20_m6_launch
        session.observe_preparation({'event': 'start', 'stage': 'formal_resource_preflight'})
        resources = p20_m6_launch.linux_resources()
        state = p20_m6_launch.resource_admission(resources)
        session.observe_preparation({'event': 'completed', 'stage': 'formal_resource_preflight',
                                     'resource_observation': resources, 'resource_admission': state})
        if state != 'ADMITTED_RESOURCE_POLICY_ONLY':
            raise CaptureRejected('P21_FACTORY_RESOURCE_REFUSAL:' + state)
        import p20_native_factory
        bundle = p20_native_factory.prepare_context(observer=session.observe_preparation)
        from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
        evaluator, problem = bundle['evaluator'], bundle['problem']
        if type(evaluator) is not InProcessCherchiEvaluator:
            raise CaptureRejected('P21_GENUINE_INPROCESS_EVALUATOR_REQUIRED')
        if (evaluator.call_counts != {'source': 0, 'boolean': 0, 'integration': 0, 'derivative': 0}
                or evaluator._materials or evaluator.stage_observer is not None):
            raise CaptureRejected('P21_FRESH_UNOBSERVED_EVALUATOR_REQUIRED')
        pins = p20_native_factory.observed_pins(bundle)
        adapter = sys.modules[InProcessCherchiEvaluator.__module__]
        producerfiles = {
            'factory': source_file_record(Path(__file__).absolute()),
            'capture': source_file_record(Path(__file__).with_name('p21_same_call_capture.py').absolute()),
            'p20_factory': source_file_record(Path(p20_native_factory.__file__).absolute()),
            'p20_launcher': source_file_record(Path(p20_m6_launch.__file__).absolute()),
            'adapter': source_file_record(Path(adapter.__file__).absolute()),
            'native': source_file_record(Path(evaluator.native.__file__).absolute()),
            'bridge': source_file_record(Path(evaluator.bridge.__file__).absolute()),
        }
        if evaluator.arithmetic is not None:
            producerfiles['arithmetic'] = source_file_record(Path(evaluator.arithmetic.__file__).absolute())
        context = {
            'c': list(bundle['coefficients']),
            'pins': pins,
            'normalization': problem.normalization,
            'request': asdict(evaluator.request),
            'fixed': [float(value) for value in evaluator.fixed],
            'problem_identity': problem.identity,
            'problem_input_digest': problem.input_digest,
            'frame': bundle['frame'].report(),
            'input_identity': bundle['input_identity'],
            'producerfiles': producerfiles,
            'evaluator_settings': bundle['evaluator_settings'],
            'solver_settings': bundle['solver_settings'],
            'evaluator_policy': bundle['config']['evaluator_policy'],
            'p20_request_sha256': p20_native_factory.REQUEST_SHA256,
            'runtime_python_git_blobs': bundle['runtime_python_git_blobs'],
            'factory_preparation_seconds': bundle['timings'],
            'factory_resource_observation': resources,
            'factory_fresh_evaluator_counts': dict(evaluator.call_counts),
            'native_fixed_shell_preparation_integration_executed': True,
            'factory_preparation_does_not_execute_formal_source_or_boolean': True,
            'admission': dict(ADMISSION),
            'scope': 'PREPARED_GENUINE_EVALUATOR_BEFORE_THE_UNCHANGED_W0_M6_AUDIT',
            'context_phase': 'FACTORY_PREPARATION_COMPLETE_BEFORE_FORMAL_AUDIT_INVOCATION',
        }
        session.bind_context(context)
        session.attach_counter_provider(lambda: dict(evaluator.call_counts))
        evaluator.stage_observer = session
        session.mark_factory_ready()
        return evaluator, problem, bundle['coefficients']
    except BaseException as error:
        session.factory_event('failed', error_type=type(error).__module__ + '.' + type(error).__qualname__,
                              error=str(error))
        raise
