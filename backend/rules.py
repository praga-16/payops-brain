"""Demo policies, not network or regulatory dispute rules. Money uses Decimal."""
from datetime import date
from decimal import Decimal


def apply_rules(fields, records, received_date):
    def result(action, code, reason):
        return {'action': action, 'code': code, 'reason': reason}
    if not records:
        return result('ESCALATE', 'UNKNOWN_TXN', 'No ledger record matches the transaction reference.')
    if any(Decimal(str(r['amount'])) != Decimal(str(fields['amount'])) or
           str(r['date']) != str(fields['date']) for r in records):
        return result('ESCALATE', 'EVIDENCE_MISMATCH', 'Notice amount or date conflicts with ledger evidence.')
    age = (date.fromisoformat(str(received_date)) - date.fromisoformat(str(fields['date']))).days
    if age < 0 or age > 90:
        return result('ESCALATE', 'OUTSIDE_WINDOW', 'Transaction falls outside the demo policy window of 0–90 days.')
    statuses = {r['status'] for r in records}
    if 'REFUNDED' in statuses:
        if len(statuses) != 1:
            return result('ESCALATE', 'MIXED_STATUS', 'Mixed refund and debit evidence needs human investigation.')
        return result('NO_ACTION', 'ALREADY_REFUNDED', 'Ledger evidence shows the transaction was already refunded.')
    if statuses == {'FAILED_DEBITED'}:
        return result('REFUND', 'FAILED_DEBITED', 'Ledger evidence shows a failed transaction with a debit.')
    if statuses == {'SETTLED'} and len(records) == 2:
        return result('REFUND', 'DUPLICATE_DEBIT', 'Two settled debit records share the same transaction reference.')
    if statuses == {'SETTLED'} and len(records) == 1:
        return result('NO_ACTION', 'CLEAN', 'A single settled debit matches the notice; no duplicate is evidenced.')
    return result('ESCALATE', 'AMBIGUOUS', 'Ambiguous ledger status or multiplicity requires human investigation.')
