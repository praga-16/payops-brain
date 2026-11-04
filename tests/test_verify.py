from copy import deepcopy
import pytest
from backend.graph import read_data, run_case
from backend.verify import verify_draft, render_reply


@pytest.fixture
def result():
    return run_case(read_data('disputes.json')[0])


def test_good_draft(result):
    assert result['verification']['passed']
    assert '[L001A]' in result['reply']


@pytest.mark.parametrize('key,value,reason', [('ledger_id','FAKE-ID','Unknown ledger'),
    ('ledger_id','L002A','different transaction'),('amount','1.00','Amount mismatch'),
    ('date','2026-11-02','Date mismatch'),('status','REFUNDED','Status mismatch')])
def test_tampered_claims(result,key,value,reason):
    draft = deepcopy(result['draft'])
    draft['claims'][0][key] = value
    checked = verify_draft(draft, read_data('ledger.json'), result['matched'], result['rule'])
    assert not checked['passed']
    assert any(reason in message for message in checked['errors'])
    assert 'withheld' in render_reply(draft,result['rule'],checked)


@pytest.mark.parametrize('attack', ['missing','duplicate','action','free_text','empty'])
def test_unsupported_drafts(result,attack):
    draft = deepcopy(result['draft'])
    if attack == 'missing': draft['claims'].pop()
    if attack == 'duplicate': draft['claims'][1] = draft['claims'][0]
    if attack == 'action': draft['action'] = 'NO_ACTION'
    if attack == 'free_text': draft['reply'] = 'The customer was refunded INR 999.'
    if attack == 'empty': draft = {}
    assert not verify_draft(draft,read_data('ledger.json'),result['matched'],result['rule'])['passed']


def test_graph_forces_escalation_on_bad_draft(monkeypatch):
    import backend.graph as module
    original = module.call_json
    def tamper(step,*args,**kwargs):
        output=original(step,*args,**kwargs)
        if step=='draft': output['claims'][0]['amount']='1.00'
        return output
    monkeypatch.setattr(module,'call_json',tamper)
    result = module.run_case(read_data('disputes.json')[0])
    assert result['action']=='ESCALATE'
    assert not result['verification']['passed']
    assert result['trace'][-1]['status']=='failed'


def test_graph_failure_is_escalation(monkeypatch):
    import backend.graph as module
    from backend.meta_client import ModelError
    def fail(*a,**kw): raise ModelError('extract: provider HTTP 401; check configuration')
    monkeypatch.setattr(module,'call_json',fail)
    result=module.run_case(read_data('disputes.json')[0])
    assert result['action']=='ESCALATE' and not result['verification']['passed']
    assert result['trace'][0]['status']=='failed'
    assert all(t['status']=='skipped' for t in result['trace'][1:])
