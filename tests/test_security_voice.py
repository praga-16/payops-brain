import base64
import json
import logging
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.simulator import seed
from backend.security import has_pan,mask_text,scan_database
from backend.control_tower import run_agents
from backend.sarvam_voice import transcribe,synthesize
from tests.test_api import wav_bytes


def test_database_logs_and_api_have_no_card_like_numbers(tmp_path,monkeypatch,caplog):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(16,91,p)
    with caplog.at_level(logging.INFO):run_agents(p)
    assert not scan_database(p)['card_like_findings']
    assert not has_pan(caplog.text)
    from backend.security import install_log_filters
    install_log_filters()
    with caplog.at_level(logging.INFO):
        logging.getLogger('payops.control_tower').info('Synthetic rejected card: %s','0000 0000 0000 0001')
    assert not has_pan(caplog.text)
    from backend.main import app
    with TestClient(app) as c:
        for endpoint in ('/api/transactions','/api/review-queue','/api/audit','/api/bin-intelligence','/api/security/status'):
            r=c.get(endpoint);assert r.status_code==200
            assert not has_pan(json.dumps(r.json()))
        r=c.post('/disputes/D001/run',json={'note':''})
        assert r.status_code==200 and not has_pan(json.dumps(r.json()))
        for value in ('0000000000000001','0000 0000 0000 0001','0000-0000-0000-0001'):
            r=c.post('/api/merchant-assistant/chat',json={'merchant_id':'SYN-M001','question':value})
            assert r.status_code==422 and value not in r.text
    assert mask_text('0000 0000 0000 0001')=='**** **** **** 0001'
    assert not has_pan('0.12345678901234567')
    assert not has_pan('abc123456789012345def')


@pytest.mark.parametrize('language,code',[('en','en-IN'),('hi','hi-IN'),('ta','ta-IN')])
def test_sarvam_speech_contracts_mocked(monkeypatch,language,code):
    monkeypatch.setenv('PAYOPS_SARVAM_VOICE','true');monkeypatch.setenv('PAYOPS_MOCK','false');monkeypatch.setenv('SARVAM_API_KEY','test-never-real')
    calls=[]
    def post(self,url,**kwargs):
        calls.append((url,kwargs))
        if url.endswith('/speech-to-text'):return httpx.Response(200,json={'transcript':'Synthetic settlement question','language_code':code})
        return httpx.Response(200,json={'audios':[base64.b64encode(wav_bytes()).decode()]})
    monkeypatch.setattr(httpx.Client,'post',post)
    assert transcribe(wav_bytes())['language']==language
    assert synthesize('Synthetic ledger facts',language)['audio_base64']
    assert calls[0][1]['data']['language_code']=='unknown'
    assert calls[0][1]['files']['file'][0]=='synthetic.wav'
    assert calls[1][1]['json']['language_code']==code
    assert calls[0][1]['headers']=={'api-subscription-key':'test-never-real'}


def test_voice_flag_disabled_and_failure(tmp_path,monkeypatch):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(16,92,p)
    from backend.main import app
    with TestClient(app) as c:
        assert not c.get('/api/merchant-assistant/voice/status').json()['enabled']
        assert c.post('/api/merchant-assistant/voice/transcribe',files={'audio':('s.wav',wav_bytes(),'audio/wav')}).status_code==503
        monkeypatch.setenv('PAYOPS_SARVAM_VOICE','true');monkeypatch.setenv('PAYOPS_MOCK','false');monkeypatch.setenv('SARVAM_API_KEY','test-only')
        monkeypatch.setattr(httpx.Client,'post',lambda *a,**k:httpx.Response(429,text='private provider error'))
        from backend.providers.base import ProviderError
        with pytest.raises(ProviderError,match='HTTP 429'):synthesize('Synthetic text','en')


def test_enabled_voice_api_still_uses_fact_gate(tmp_path,monkeypatch):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(16,93,p)
    monkeypatch.setenv('PAYOPS_SARVAM_VOICE','true');monkeypatch.setenv('PAYOPS_MOCK','false');monkeypatch.setenv('SARVAM_API_KEY','test-only');monkeypatch.setenv('LLM_PROVIDER','local')
    import backend.sarvam_voice as module
    monkeypatch.setattr(module,'send',lambda endpoint,**kw:{'transcript':'Why is settlement short?','language_code':'en-IN'} if endpoint=='/speech-to-text' else {'audios':[base64.b64encode(wav_bytes()).decode()]})
    from backend.main import app
    with TestClient(app) as c:
        assert c.post('/api/merchant-assistant/voice/transcribe',files={'audio':('s.wav',wav_bytes(),'audio/wav')}).json()['language']=='en'
        r=c.post('/api/merchant-assistant/voice/speak',json={'merchant_id':'SYN-M001','question':'Why is settlement short?','language':'en'})
        assert r.status_code==200 and r.json()['answer']['grounded'] and r.json()['audio_base64']
