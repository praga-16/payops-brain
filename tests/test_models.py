import json
import httpx
import pytest
from backend.config import model_config
from backend.meta_client import call_json, parse_json, request_body, ModelError
from backend.schemas import Extraction
from backend.graph import read_data
from backend.redact import redact_context
from backend.voice import transcribe, validate_wav
from tests.test_api import wav_bytes


@pytest.mark.parametrize('text', ['{"a":1}', '```json\n{"a":1}\n```', 'Here is JSON: {"a":1} done'])
def test_json_parsing(text):
    assert parse_json(text)=={'a':1}


@pytest.mark.parametrize('text', ['not JSON', '{"a":1} {"b":2}', '[1,2]'])
def test_invalid_or_ambiguous_json(text):
    with pytest.raises(ValueError): parse_json(text)


def configure_live(monkeypatch):
    monkeypatch.setenv('PAYOPS_MOCK','false')
    monkeypatch.setenv('EXTRACT_API_KEY','test-key-never-real')
    monkeypatch.setenv('EXTRACT_PROTOCOL','responses')
    monkeypatch.setenv('EXTRACT_BASE_URL','https://example.invalid/v1')


def test_responses_and_chat_image_shapes():
    from dataclasses import replace
    from backend.config import ROOT
    cfg=model_config('extract')
    path,body=request_body(replace(cfg,protocol='responses'),'Read this',ROOT/'data/disputes/D001.png')
    assert path=='/responses' and body['store'] is False
    assert body['input'][0]['content'][1]['image_url'].startswith('data:image/png;base64,')
    path,body=request_body(replace(cfg,protocol='chat'),'Read this',ROOT/'data/disputes/D001.png')
    assert path=='/chat/completions'
    assert body['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')


def test_invalid_json_retries_once(monkeypatch):
    configure_live(monkeypatch)
    calls=[]
    def response(self,url,**kwargs):
        calls.append(kwargs)
        value='invalid' if len(calls)==1 else '{"ok":true}'
        return httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':value}]}]})
    monkeypatch.setattr(httpx.Client,'post',response)
    assert call_json('extract','Return ok')=={'ok':True}
    assert len(calls)==2
    assert calls[0]['headers']['Authorization']=='Bearer test-key-never-real'


def test_invalid_schema_retries_then_fails(monkeypatch):
    configure_live(monkeypatch)
    calls=[]
    def response(*args,**kwargs):
        calls.append(1)
        return httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':'{}'}]}]})
    monkeypatch.setattr(httpx.Client,'post',response)
    with pytest.raises(ModelError,match='after one retry'):call_json('extract','Extract',schema=Extraction)
    assert len(calls)==2


@pytest.mark.parametrize('kind',['http','timeout','connection'])
def test_readable_provider_errors_no_mock_fallback(monkeypatch,kind):
    configure_live(monkeypatch)
    def response(*args,**kwargs):
        if kind=='http': return httpx.Response(401,text='secret private provider response')
        if kind=='timeout': raise httpx.ReadTimeout('secret')
        raise httpx.ConnectError('secret')
    monkeypatch.setattr(httpx.Client,'post',response)
    with pytest.raises(ModelError) as exc:call_json('extract','Extract',fixture={'ok':True})
    assert 'secret' not in str(exc.value)


def test_config_fallback_and_baseten(monkeypatch):
    for key in ('REDACT_MODEL','REDACT_BASE_URL','REDACT_API_KEY','REDACT_PROTOCOL'):
        monkeypatch.delenv(key,raising=False)
    monkeypatch.setenv('BASETEN_BASE_URL','https://example.invalid/v1')
    monkeypatch.setenv('BASETEN_API_KEY','fake-baseten-key')
    cfg=model_config('redact')
    assert cfg.protocol=='chat' and cfg.model=='meta-models/muse-spark-open-1026'
    assert cfg.api_key=='fake-baseten-key'
    assert 'api_key' not in cfg.public()
    monkeypatch.setenv('REDACT_MODEL','explicit-model')
    assert model_config('redact').model=='explicit-model'


def test_pii_not_in_draft_context(monkeypatch):
    fields=read_data('disputes/D001.json')['fields']
    note=' '.join(fields[key] for key in ('customer_name','phone','card','upi_id'))
    redacted,detail=redact_context(fields,note)
    serialized=json.dumps(redacted)
    assert all(fields[key] not in serialized for key in ('customer_name','phone','card','upi_id'))
    assert set(redacted)=={'reason','ops_note'}
    assert detail['original']['customer_name']==fields['customer_name']


def test_voice_multipart_contract(monkeypatch):
    monkeypatch.setenv('PAYOPS_MOCK','false')
    monkeypatch.setenv('VOICE_API_KEY','test-voice-key')
    monkeypatch.setenv('VOICE_BASE_URL','https://example.invalid/v1')
    calls=[]
    def response(self,url,**kwargs):
        calls.append((url,kwargs))
        return httpx.Response(200,json={'transcript':'Review this synthetic case.'})
    monkeypatch.setattr(httpx.Client,'post',response)
    result=transcribe(wav_bytes())
    assert result['mode']=='live'  # HTTP transport is stubbed; no external API call.
    url,request=calls[0]
    assert url.endswith('/v1/asr/transcribe')
    metadata=request['files']['request']
    assert metadata[0] is None and metadata[2]=='application/json'
    assert json.loads(metadata[1])=={'mode':'PUSH_TO_TALK','model':'muse-voice-transcribe-1.0','audioEncoding':'WAV'}
    assert request['files']['audio'][1]==wav_bytes()


def test_wav_validation():
    assert validate_wav(wav_bytes())==0.1
    with pytest.raises(ValueError): validate_wav(b'not wav')
