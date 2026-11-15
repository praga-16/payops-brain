from datetime import datetime, timezone
import json

import httpx
import pytest
from backend.providers.factory import explain, get_provider
from backend.providers.sarvam_provider import SarvamProvider
from backend.dispute_intelligence import analyze, checklist_score
from backend.simulator import seed
from backend.review import persist


def configure(monkeypatch):
    monkeypatch.setenv('PAYOPS_MOCK','false')
    monkeypatch.setenv('LLM_PROVIDER','sarvam')
    monkeypatch.setenv('SARVAM_API_KEY','test-key-not-real')


def test_sarvam_contract(monkeypatch):
    configure(monkeypatch)
    calls=[]
    def post(self,url,**kw):
        calls.append((url,kw))
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'sentences':['INR 12.00 settled.']})}}]})
    monkeypatch.setattr(httpx.Client,'post',post)
    result=explain(['INR 12.00 settled.'],facts={'amount':'12.00'},language='hi')
    assert result['mode']=='live' and result['grounded']
    url,kw=calls[0]
    assert url=='https://api.sarvam.ai/v1/chat/completions'
    assert kw['headers']=={'api-subscription-key':'test-key-not-real'}
    assert kw['json']['model']=='sarvam-105b'
    assert kw['json']['reasoning_effort']=='low'
    assert kw['json']['response_format']=={'type':'json_object'}
    assert 'test-key-not-real' not in json.dumps(result)


@pytest.mark.parametrize('kind',['429','401','timeout','invalid','invented','null'])
def test_provider_failure_or_hallucination_falls_back(monkeypatch,kind):
    configure(monkeypatch)
    def post(*args,**kw):
        if kind.isdigit():return httpx.Response(int(kind),text='SECRET')
        if kind=='timeout':raise httpx.ReadTimeout('SECRET')
        content={'invalid':'garbage','invented':'{"sentences":["INR 999999 refunded."]}','null':None}[kind]
        return httpx.Response(200,json={'choices':[{'message':{'content':content}}]})
    monkeypatch.setattr(httpx.Client,'post',post)
    result=explain(['INR 12.00 settled.'],facts={})
    assert result['mode']=='local' and result['fallback_reason']
    assert result['text']=='INR 12.00 settled.'
    assert 'SECRET' not in json.dumps(result)


def test_missing_key_and_mock_never_call(monkeypatch):
    monkeypatch.setattr(httpx.Client,'post',lambda *a,**k:pytest.fail('Unexpected network'))
    assert get_provider().name=='local'
    assert explain(['A'],facts={})['text']=='A'


def test_dispute_evidence_and_deadline(tmp_path):
    path=tmp_path/'ledger.db';seed(160,42,path)
    results=analyze(path,now=datetime(2026,11,15,tzinfo=timezone.utc))
    assert results and all(r['reason_code']=='UPI_UNAUTHORIZED' for r in results)
    assert any(r['decision']['confidence']==pytest.approx(.82) for r in results)
    assert all(0<=r['win_probability']<=1 for r in results)
    assert all(r['draft']['grounded'] for r in results)
    assert persist(results,path)==len(results)
    expired=analyze(path,now=datetime(2027,1,1,tzinfo=timezone.utc))
    assert all(r['overdue'] and r['decision']['action']=='ACCEPT' for r in expired)
    assert checklist_score({})==0


def test_meta_null_response_escalates_safely(monkeypatch):
    from backend.meta_client import call_json,ModelError
    monkeypatch.setenv('PAYOPS_MOCK','false')
    monkeypatch.setenv('DRAFT_API_KEY','fake-key')
    monkeypatch.setenv('DRAFT_PROTOCOL','chat')
    monkeypatch.setattr(httpx.Client,'post',lambda *a,**k:httpx.Response(200,json={'choices':[{'message':{'content':None}}]}))
    with pytest.raises(ModelError,match='invalid JSON'):
        call_json('draft','Return JSON')
