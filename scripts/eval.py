"""Evaluate all fixtures. Default is explicitly OFFLINE, not a vision benchmark."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Make paid provider calls; requires every graph model key')
    args = parser.parse_args()
    if not args.live:
        os.environ['PAYOPS_MOCK'] = 'true'
    from backend.graph import read_data, run_case
    from backend.config import ROOT, model_config
    configs = {s: model_config(s).public() for s in ('extract', 'redact', 'draft')}
    if args.live and any(cfg['mode'] == 'mock' for cfg in configs.values()):
        parser.error('--live requires extract, redact and draft keys, and PAYOPS_MOCK must not be true')
    ledger = read_data('ledger.json')
    valid_ids = {r['id'] for r in ledger}
    rows, cited, valid, errors, verified = [], 0, 0, 0, 0
    for dispute in read_data('disputes.json'):
        truth = read_data(f"disputes/{dispute['id']}.json")
        result = run_case(dispute, ledger=ledger)
        claims = result.get('draft', {}).get('claims', [])
        cited += len(claims)
        valid += sum(c['ledger_id'] in valid_ids for c in claims)
        errors += bool(result.get('error'))
        verified += result['verification']['passed']
        rows.append({'id': dispute['id'], 'scenario': truth['scenario'], 'image': truth['image_variant'],
                     'expected': truth['expected_action'], 'actual': result['action'],
                     'correct': result['action'] == truth['expected_action'],
                     'verified': result['verification']['passed'], 'error': result.get('error', '')})
    total = len(rows)
    correct = sum(r['correct'] for r in rows)
    escalated = sum(r['actual'] == 'ESCALATE' for r in rows)
    mode = 'LIVE MODELS' if args.live else 'OFFLINE FIXTURES'
    citation_rate = f'{valid / cited:.1%} ({valid}/{cited})' if cited else 'N/A (no citations)'
    lines = ['# Evaluation results', '', f'Mode: **{mode}**', '',
             'Offline extraction reads ground-truth sidecar fields. Offline drafts are deterministic fixtures.',
             'These numbers test policies, matching and verification; they do not measure OCR, model',
             'redaction quality or real-world dispute performance. Labels are synthetic demo policy labels.', '',
             f'- Action accuracy: **{correct / total:.1%} ({correct}/{total})**',
             f'- Citation-validity rate (existing ledger IDs / all cited IDs): **{citation_rate}**',
             f'- Full evidence-verifier pass rate: **{verified / total:.1%} ({verified}/{total})**',
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
    target = ROOT / ('eval_results_live.md' if args.live else 'eval_results.md')
    target.write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines[:18]))
    print(f'Saved {target.name}')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
