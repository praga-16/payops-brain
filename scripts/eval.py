"""Evaluate synthetic disputes with bounded concurrency and incremental reports."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import random
import re
import sys
import tempfile
import threading
import time

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAX_RETRIES = 3


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def select_disputes(disputes, truths, limit=None):
    """Keep the prefix when possible; otherwise seed coverage and fill in order."""
    if limit is None:
        return list(disputes)
    count = min(limit, len(disputes))
    if count < 3:
        raise ValueError('--limit must allow at least 3 disputes for three noisy images')

    def scenario(dispute):
        return truths[dispute['id']]['scenario']

    def noisy(dispute):
        return truths[dispute['id']]['image_variant'] in {'rotated', 'blurred', 'low_contrast'}

    prefix = disputes[:count]
    if sum(noisy(d) for d in prefix) >= 3 and len({scenario(d) for d in prefix}) >= 2:
        return prefix
    candidates = [d for d in disputes if noisy(d)]
    if len(candidates) < 3:
        raise ValueError('dataset must contain at least 3 noisy images for --limit')
    if len({scenario(d) for d in disputes}) < 2:
        raise ValueError('dataset must contain multiple scenarios for --limit')

    # Prefer different scenarios among the three required noisy images.
    selected, scenarios = [], set()
    for dispute in candidates:
        if scenario(dispute) not in scenarios and len(selected) < 3:
            selected.append(dispute)
            scenarios.add(scenario(dispute))
    for dispute in candidates:
        if len(selected) == 3:
            break
        if dispute not in selected:
            selected.append(dispute)
    if len({scenario(d) for d in selected}) < 2:
        if count < 4:
            raise ValueError('--limit 3 cannot provide both three noisy images and mixed scenarios; use at least 4')
        selected.append(next(d for d in disputes if scenario(d) != scenario(selected[0])))
    for dispute in disputes:
        if len(selected) == count:
            break
        if dispute not in selected:
            selected.append(dispute)
    selected_ids = {d['id'] for d in selected}
    return [d for d in disputes if d['id'] in selected_ids]


def retryable(error):
    # run_case captures provider exceptions in state['error']; match its safe,
    # documented messages rather than retrying unrelated verification failures.
    return bool(re.search(r'\bHTTP 429\b|\btimed? out\b|\btimeout\b', str(error), re.I))


def evaluate_one(dispute, truth, ledger, run_case, stop=None):
    result = None
    for attempt in range(MAX_RETRIES + 1):
        if stop is not None and stop.is_set():
            error = 'Evaluation interrupted'
            break
        try:
            result = run_case(dispute, ledger=ledger)
            error = result.get('error', '')
        except (httpx.TimeoutException, TimeoutError):
            error = 'Evaluation request timed out'
            result = None
        except Exception as exc:
            # Keep the report usable without exposing raw provider payloads/keys.
            error = f'Evaluation raised {type(exc).__name__}'
            result = None
        if not retryable(error) or attempt == MAX_RETRIES:
            break
        delay = 2 ** attempt + random.uniform(0, 0.25)
        if stop is None:
            time.sleep(delay)
        elif stop.wait(delay):
            break
    if result is None:
        result = {'action': 'ESCALATE', 'verification': {'passed': False}, 'error': error}
    claims = result.get('draft', {}).get('claims', [])
    valid_ids = {r['id'] for r in ledger}
    return {'id': dispute['id'], 'scenario': truth['scenario'], 'image': truth['image_variant'],
            'expected': truth['expected_action'], 'actual': result['action'],
            'correct': result['action'] == truth['expected_action'],
            'verified': result['verification']['passed'], 'error': result.get('error', ''),
            'cited': len(claims), 'valid': sum(c['ledger_id'] in valid_ids for c in claims)}


def render_report(rows, configs, live):
    total = len(rows)
    cited = sum(r['cited'] for r in rows)
    valid = sum(r['valid'] for r in rows)
    errors = sum(bool(r['error']) for r in rows)
    verified = sum(r['verified'] for r in rows)
    correct = sum(r['correct'] for r in rows)
    escalated = sum(r['actual'] == 'ESCALATE' for r in rows)
    mode = 'LIVE MODELS' if live else 'OFFLINE FIXTURES'
    citation_rate = f'{valid / cited:.1%} ({valid}/{cited})' if cited else 'N/A (no citations)'
    caveat = ([f'Extraction and drafting ran on real models over {total} synthetic notices with synthetic policy labels.',
               'These numbers do not measure real-world dispute performance.'] if live else
              ['Offline extraction reads ground-truth sidecar fields. Offline drafts are deterministic fixtures.',
               'These numbers test policies, matching and verification; they do not measure OCR, model',
               'redaction quality or real-world dispute performance. Labels are synthetic demo policy labels.'])
    lines = ['# Evaluation results', '', f'Mode: **{mode}**', '', *caveat, '',
             f'- Action accuracy: **{correct / total if total else 0:.1%} ({correct}/{total})**',
             f'- Citation-validity rate (existing ledger IDs / all cited IDs): **{citation_rate}**',
             f'- Full evidence-verifier pass rate: **{verified / total if total else 0:.1%} ({verified}/{total})**',
             f'- Recommended escalations: **{escalated}/{total}**',
             f'- Cases requiring human approval or rejection: **{total}/{total}**',
             f'- Agent errors: **{errors}**', '', '## Per-step configuration', '',
             '```json', json.dumps(configs, indent=2), '```', '',
             '## Per-case results', '', '| Case | Scenario | Image | Expected | Actual | Correct | Verified |',
             '|---|---|---|---|---|---|---|']
    lines += [f"| {r['id']} | {r['scenario']} | {r['image']} | {r['expected']} | {r['actual']} | {r['correct']} | {r['verified']} |" for r in rows]
    lines += ['', '## Failures', '']
    failures = [r for r in rows if not r['correct'] or not r['verified'] or r['error']]
    lines += [f"- {r['id']}: expected {r['expected']}, got {r['actual']}; {r['error'] or 'verification failed'}" for r in failures] or ['None in this run.']
    lines += ['', 'The separate adversarial verifier tests inject nonexistent, wrong-transaction, duplicate,',
              'wrong-amount, wrong-date and wrong-status citations. They are not included in the',
              'clean-fixture citation-validity denominator above.', '']
    return '\n'.join(lines), failures


def save_report(target, rows, configs, live):
    """Atomic replacement prevents interruption from leaving a truncated report."""
    report, failures = render_report(rows, configs, live)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix=target.name + '.', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(report)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return report, failures


def evaluate(disputes, truths, ledger, run_case, *, workers, target, configs, live):
    rows_by_id = {}
    pool = ThreadPoolExecutor(max_workers=workers)
    futures = {}
    interrupted = False
    stop = threading.Event()

    def record(future):
        dispute = futures[future]
        rows_by_id[dispute['id']] = future.result()
        rows = [rows_by_id[d['id']] for d in disputes if d['id'] in rows_by_id]
        save_report(target, rows, configs, live)
        print(f"Completed {len(rows)}/{len(disputes)}: {dispute['id']}", flush=True)

    try:
        for dispute in disputes:
            futures[pool.submit(evaluate_one, dispute, truths[dispute['id']], ledger, run_case, stop)] = dispute
        for future in as_completed(futures):
            record(future)
    except KeyboardInterrupt:
        interrupted = True
        stop.set()
        # Drain already-finished cases before cancelling queued work. Running HTTP
        # calls cannot be killed by Python threads; their request timeouts still apply.
        for future in futures:
            if future.done() and not future.cancelled() and futures[future]['id'] not in rows_by_id:
                record(future)
        rows = [rows_by_id[d['id']] for d in disputes if d['id'] in rows_by_id]
        save_report(target, rows, configs, live)
        print(f'Interrupted: saved {len(rows_by_id)}/{len(disputes)} completed cases to {target.name}',
              file=sys.stderr, flush=True)
    finally:
        pool.shutdown(wait=not interrupted, cancel_futures=True)
    rows = [rows_by_id[d['id']] for d in disputes if d['id'] in rows_by_id]
    return rows, interrupted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Make paid provider calls; requires every graph model key')
    parser.add_argument('--limit', type=positive_int,
                        help='Run up to N cases, preferring the prefix while ensuring mixed scenarios and 3 noisy images (N >= 3)')
    parser.add_argument('--workers', type=positive_int, default=4, help='Concurrent disputes (default: 4)')
    args = parser.parse_args()
    if not args.live:
        os.environ['PAYOPS_MOCK'] = 'true'
    from backend.graph import read_data, run_case
    from backend.config import ROOT, model_config
    configs = {s: model_config(s).public() for s in ('extract', 'redact', 'draft')}
    if args.live and any(cfg['mode'] == 'mock' for cfg in configs.values()):
        parser.error('--live requires extract, redact and draft keys, and PAYOPS_MOCK must not be true')
    disputes = read_data('disputes.json')
    truths = {d['id']: read_data(f"disputes/{d['id']}.json") for d in disputes}
    try:
        disputes = select_disputes(disputes, truths, args.limit)
    except ValueError as exc:
        parser.error(str(exc))
    target = ROOT / ('eval_results_live.md' if args.live else 'eval_results.md')
    rows, interrupted = evaluate(disputes, truths, read_data('ledger.json'), run_case,
        workers=args.workers, target=target, configs=configs, live=args.live)
    if interrupted:
        return 130
    report, failures = render_report(rows, configs, args.live)
    print('\n'.join(report.splitlines()[:18]))
    print(f'Saved {target.name}')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
