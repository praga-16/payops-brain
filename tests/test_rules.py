from copy import deepcopy
import pytest
from backend.graph import read_data
from backend.rules import apply_rules


@pytest.mark.parametrize('did,expected', [('D001','REFUND'),('D002','NO_ACTION'),('D003','ESCALATE'),
                                        ('D004','ESCALATE'),('D005','REFUND'),('D006','ESCALATE'),('D007','NO_ACTION')])
def test_scenarios(did, expected):
    fields = read_data(f'disputes/{did}.json')['fields']
    ledger = [r for r in read_data('ledger.json') if r['transaction_id'] == fields['transaction_id']]
    assert apply_rules(fields, ledger, '2026-11-04')['action'] == expected


@pytest.mark.parametrize('when,expected', [('2026-08-06','NO_ACTION'),('2026-08-05','ESCALATE'),('2026-11-05','ESCALATE')])
def test_window_boundary(when, expected):
    fields = {'date': when, 'amount': '0.30'}
    rows = [{'date': when, 'amount': '0.30', 'status':'SETTLED'}]
    assert apply_rules(fields, rows, '2026-11-04')['action'] == expected


def test_date_and_amount_conflicts():
    fields = {'date':'2026-11-01','amount':'1287.00'}
    rows = [{'date':'2026-11-02','amount':'1287','status':'SETTLED'}]
    assert apply_rules(fields, rows, '2026-11-04')['code'] == 'EVIDENCE_MISMATCH'
    rows[0].update(date='2026-11-01',amount='1287.01')
    assert apply_rules(fields, rows, '2026-11-04')['code'] == 'EVIDENCE_MISMATCH'


def test_mixed_status_and_three_debits_escalate():
    fields = read_data('disputes/D001.json')['fields']
    rows = deepcopy(read_data('ledger.json')[:2])
    rows[1]['status'] = 'REFUNDED'
    assert apply_rules(fields, rows, '2026-11-04')['action'] == 'ESCALATE'
    rows[1]['status'] = 'SETTLED'
    rows.append({**rows[0], 'id':'L-extra'})
    assert apply_rules(fields, rows, '2026-11-04')['action'] == 'ESCALATE'
