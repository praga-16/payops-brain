"""Verify structured draft claims; render prose only from validated evidence.

There is deliberately no model-written free-text channel around this check.
"""
from decimal import Decimal
from backend.schemas import Draft


def verify_draft(draft, ledger, matched, rule):
    errors = []
    try:
        draft = Draft.model_validate(draft).model_dump(mode='json')
    except ValueError:
        return {'passed': False, 'errors': ['Draft does not match the required claim schema.'], 'checked': 0}
    by_id = {r['id']: r for r in ledger}
    allowed = {r['id'] for r in matched}
    cited = [c['ledger_id'] for c in draft['claims']]
    if len(cited) != len(set(cited)):
        errors.append('Duplicate ledger citations are not permitted.')
    if set(cited) != allowed:
        errors.append('Draft must cite exactly the matched ledger evidence.')
    if draft['action'] != rule['action']:
        errors.append('Draft action conflicts with the deterministic policy result.')
    for claim in draft['claims']:
        row = by_id.get(claim['ledger_id'])
        if row is None:
            errors.append(f"Unknown ledger citation: {claim['ledger_id']}.")
            continue
        if row['id'] not in allowed:
            errors.append(f"Citation {row['id']} belongs to a different transaction.")
        if Decimal(str(row['amount'])) != Decimal(str(claim['amount'])):
            errors.append(f"Amount mismatch for {row['id']}.")
        if str(row['date']) != str(claim['date']):
            errors.append(f"Date mismatch for {row['id']}.")
        if row['status'] != claim['status']:
            errors.append(f"Status mismatch for {row['id']}.")
    return {'passed': not errors, 'errors': errors, 'checked': len(cited)}


def render_reply(draft, rule, verification):
    if not verification['passed']:
        return 'Escalated for human investigation. Draft withheld because evidence verification failed.'
    claims = Draft.model_validate(draft).model_dump(mode='json')['claims']
    lines = [f"Proposed action: {draft['action']}. {rule['reason']}"]
    for c in claims:
        lines.append(f"Ledger [{c['ledger_id']}]: INR {Decimal(c['amount']):,.2f} on {c['date']}; status {c['status']}.")
    lines.append('Pending human review. No payment action has been executed.')
    return '\n'.join(lines)
