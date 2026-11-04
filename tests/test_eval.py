import argparse
from concurrent.futures import as_completed
import threading

import httpx
import pytest

from scripts import eval as evaluator


def dataset(variants=('rotated', 'blurred', 'low_contrast'), scenarios=None):
    disputes = [{'id': f'D{i:03}'} for i in range(1, len(variants) + 1)]
    scenarios = scenarios or [f'scenario-{i}' for i in range(len(variants))]
    truths = {d['id']: {'scenario': scenario, 'image_variant': variant, 'expected_action': 'REFUND'}
              for d, scenario, variant in zip(disputes, scenarios, variants)}
    return disputes, truths


def good_result():
    return {'action': 'REFUND', 'verification': {'passed': True},
            'draft': {'claims': [{'ledger_id': 'L1'}]}}


def failed_result(error):
    return {'action': 'ESCALATE', 'verification': {'passed': False}, 'error': error}


def test_prefix_retained_when_it_covers_requirements():
    disputes, truths = dataset(('rotated', 'blurred', 'low_contrast', 'clean'))
    assert evaluator.select_disputes(disputes, truths, 3) == disputes[:3]
    assert evaluator.select_disputes(disputes, truths, 100) == disputes
    assert evaluator.select_disputes(disputes, truths) == disputes


def test_selection_replaces_insufficient_prefix_deterministically():
    disputes, truths = dataset(('clean', 'clean', 'clean', 'rotated', 'blurred', 'low_contrast'))
    selected = evaluator.select_disputes(disputes, truths, 4)
    assert [d['id'] for d in selected] == ['D001', 'D004', 'D005', 'D006']
    assert sum(truths[d['id']]['image_variant'] != 'clean' for d in selected) == 3
    assert len({truths[d['id']]['scenario'] for d in selected}) > 1


@pytest.mark.parametrize('limit', [1, 2])
def test_limit_below_three_rejected(limit):
    disputes, truths = dataset()
    with pytest.raises(ValueError, match='at least 3'):
        evaluator.select_disputes(disputes, truths, limit)


def test_impossible_coverage_rejected():
    disputes, truths = dataset(('clean', 'rotated', 'blurred'))
    with pytest.raises(ValueError, match='3 noisy'):
        evaluator.select_disputes(disputes, truths, 3)
    disputes, truths = dataset(scenarios=['one'] * 3)
    with pytest.raises(ValueError, match='multiple scenarios'):
        evaluator.select_disputes(disputes, truths, 3)


def test_three_noisy_images_of_one_scenario_need_four_slots():
    disputes, truths = dataset(('rotated', 'blurred', 'low_contrast', 'clean'), ['one', 'one', 'one', 'two'])
    with pytest.raises(ValueError, match='use at least 4'):
        evaluator.select_disputes(disputes, truths, 3)
    assert evaluator.select_disputes(disputes, truths, 4) == disputes


@pytest.mark.parametrize('error', ['extract: provider HTTP 429; check access',
                                 'draft: request timed out after 60s'])
def test_retry_backoff_then_success(monkeypatch, error):
    disputes, truths = dataset()
    attempts, delays = [], []
    monkeypatch.setattr(evaluator.time, 'sleep', delays.append)
    monkeypatch.setattr(evaluator.random, 'uniform', lambda *_: 0.1)

    def run(*args, **kwargs):
        attempts.append(1)
        return failed_result(error) if len(attempts) < 3 else good_result()

    row = evaluator.evaluate_one(disputes[0], truths['D001'], [{'id': 'L1'}], run)
    assert row['verified'] and row['valid'] == row['cited'] == 1
    assert len(attempts) == 3 and delays == [1.1, 2.1]


def test_timeout_exceptions_retry_and_exhaustion_is_saved(monkeypatch):
    disputes, truths = dataset()
    attempts, delays = [], []
    monkeypatch.setattr(evaluator.time, 'sleep', delays.append)
    monkeypatch.setattr(evaluator.random, 'uniform', lambda *_: 0)

    def run(*args, **kwargs):
        attempts.append(1)
        raise httpx.ReadTimeout('private provider body')

    row = evaluator.evaluate_one(disputes[0], truths['D001'], [], run)
    assert len(attempts) == 4 and delays == [1, 2, 4]
    assert row['actual'] == 'ESCALATE' and not row['verified']
    assert row['error'] == 'Evaluation request timed out'


@pytest.mark.parametrize('error', ['extract: provider HTTP 401; check access',
                                 'extract: invalid JSON or schema after one retry', 'Amount mismatch for L1.'])
def test_non_transient_failures_are_not_retried(monkeypatch, error):
    disputes, truths = dataset()
    attempts = []
    monkeypatch.setattr(evaluator.time, 'sleep', lambda _: pytest.fail('Unexpected backoff'))

    def run(*args, **kwargs):
        attempts.append(1)
        return failed_result(error)

    row = evaluator.evaluate_one(disputes[0], truths['D001'], [], run)
    assert row['error'] == error and len(attempts) == 1


def test_concurrent_cases_save_each_completion_in_dataset_order(tmp_path, monkeypatch):
    disputes, truths = dataset()
    target = tmp_path / 'eval_results_live.md'
    rendezvous, first_save = threading.Barrier(2), threading.Event()
    saved, active, peak = [], 0, 0
    lock = threading.Lock()
    original_save = evaluator.save_report

    def save(*args):
        value = original_save(*args)
        saved.append(target.read_text(encoding='utf-8'))
        first_save.set()
        return value

    def run(dispute, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            if dispute['id'] in ('D001', 'D002'):
                rendezvous.wait(timeout=5)
            if dispute['id'] == 'D001':
                assert first_save.wait(timeout=5)
            return good_result()
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(evaluator, 'save_report', save)
    rows, interrupted = evaluator.evaluate(disputes, truths, [{'id': 'L1'}], run,
        workers=2, target=target, configs={}, live=True)
    assert peak == 2 and not interrupted
    assert [row['id'] for row in rows] == ['D001', 'D002', 'D003']
    assert len(saved) == 3
    for count, report in enumerate(saved, 1):
        assert report.count('| REFUND | REFUND | True | True |') == count
        assert f'over {count} synthetic notices' in report
    final = saved[-1]
    assert final.index('| D001 |') < final.index('| D002 |') < final.index('| D003 |')
    assert 'Offline extraction' not in final
    assert not list(tmp_path.glob('*.tmp'))


def test_interrupted_run_keeps_completed_report(tmp_path, monkeypatch):
    disputes, truths = dataset()
    release = threading.Event()
    target = tmp_path / 'eval_results_live.md'

    def run(dispute, **kwargs):
        if dispute['id'] != 'D001':
            release.wait(timeout=5)
        return good_result()

    def interrupt_after_one(futures):
        yield next(as_completed(futures))
        raise KeyboardInterrupt

    monkeypatch.setattr(evaluator, 'as_completed', interrupt_after_one)
    try:
        rows, interrupted = evaluator.evaluate(disputes, truths, [{'id': 'L1'}], run,
            workers=2, target=target, configs={}, live=True)
        assert interrupted and len(rows) == 1
        report = target.read_text(encoding='utf-8')
        assert '100.0% (1/1)' in report and '| D001 |' in report and '| D002 |' not in report
    finally:
        release.set()


def test_interrupt_during_first_save_flushes_completed_case(tmp_path, monkeypatch):
    disputes, truths = dataset()
    target = tmp_path / 'eval_results_live.md'
    original_save = evaluator.save_report
    calls = []

    def save(*args):
        calls.append(1)
        if len(calls) == 1:
            raise KeyboardInterrupt
        return original_save(*args)

    monkeypatch.setattr(evaluator, 'save_report', save)
    rows, interrupted = evaluator.evaluate(disputes[:1], truths, [], lambda *a, **kw: good_result(),
        workers=1, target=target, configs={}, live=True)
    assert interrupted and len(rows) == 1
    assert '| D001 |' in target.read_text(encoding='utf-8')


def test_cancellation_prevents_new_provider_calls():
    disputes, truths = dataset()
    stop = threading.Event()
    stop.set()
    row = evaluator.evaluate_one(disputes[0], truths['D001'], [],
                                lambda *a, **kw: pytest.fail('Provider called after cancellation'), stop)
    assert row['error'] == 'Evaluation interrupted' and not row['verified']


def test_mode_specific_caveats_and_report_format():
    disputes, truths = dataset()
    row = evaluator.evaluate_one(disputes[0], truths['D001'], [], lambda *a, **kw: good_result())
    offline, _ = evaluator.render_report([row], {}, False)
    live, _ = evaluator.render_report([row], {}, True)
    assert 'Offline extraction reads ground-truth sidecar fields.' in offline
    assert 'ran on real models' not in offline
    assert 'ran on real models over 1 synthetic notices with synthetic policy labels.' in live
    assert 'do not measure real-world dispute performance' in live
    assert 'Offline' not in live
    for report in (offline, live):
        assert '| Case | Scenario | Image | Expected | Actual | Correct | Verified |' in report
        assert '## Per-step configuration' in report and '## Failures' in report


@pytest.mark.parametrize('value', ['0', '-1'])
def test_non_positive_cli_values_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        evaluator.positive_int(value)


@pytest.mark.parametrize('live', [False, True])
def test_cli_limit_workers_and_output_target(tmp_path, monkeypatch, live):
    from types import SimpleNamespace
    from backend import config, graph
    disputes, truths = dataset(('rotated', 'blurred', 'low_contrast', 'clean'))

    def read_data(name):
        if name == 'disputes.json':
            return disputes
        if name == 'ledger.json':
            return [{'id': 'L1'}]
        return truths[name.split('/')[-1].removesuffix('.json')]

    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'model_config', lambda _: SimpleNamespace(
        public=lambda: {'mode': 'live' if live else 'mock'}))
    monkeypatch.setattr(graph, 'read_data', read_data)
    monkeypatch.setattr(graph, 'run_case', lambda *a, **kw: good_result())
    monkeypatch.setattr(evaluator.sys, 'argv', ['eval.py', '--limit', '3', '--workers', '1'] + (['--live'] if live else []))
    monkeypatch.setenv('PAYOPS_MOCK', 'true')  # Never contact real APIs in this test.
    assert evaluator.main() == 0
    report = (tmp_path / ('eval_results_live.md' if live else 'eval_results.md')).read_text(encoding='utf-8')
    assert '100.0% (3/3)' in report and '| D004 |' not in report
    assert ('ran on real models' in report) is live
