import io
import wave
from backend.graph import read_data


def wav_bytes():
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000)
        wav.writeframes(b'\0\0'*2400)
    return buffer.getvalue()


def test_queue_and_notices(client):
    assert client.get('/health').json()['models']['extract']['mode']=='mock'
    assert len(client.get('/disputes').json())==30
    assert client.get('/notices/D001.png').headers['content-type']=='image/png'
    assert client.get('/notices/D001.json').status_code==404
    assert client.get('/disputes/missing').status_code==404


def test_review_requires_run_and_latest_id(client):
    body={'decision':'APPROVE','run_id':'none'}
    assert client.post('/disputes/D001/decision',json=body).status_code==409
    old=client.post('/disputes/D001/run',json={'note':''}).json()
    new=client.post('/disputes/D001/run',json={'note':''}).json()
    assert old['run_id']!=new['run_id']
    assert client.post('/disputes/D001/decision',json={**body,'run_id':old['run_id']}).status_code==409
    decision=client.post('/disputes/D001/decision',json={**body,'run_id':new['run_id']})
    assert decision.status_code==200 and not decision.json()['event']['payment_executed']
    assert client.post('/disputes/D001/decision',json={**body,'run_id':new['run_id']}).status_code==409
    assert client.post('/disputes/D001/run',json={'note':''}).status_code==409


def test_reject_and_validation(client):
    result=client.post('/disputes/D002/run',json={'note':''}).json()
    assert client.post('/disputes/D002/decision',json={'decision':'REJECT','run_id':result['run_id']}).json()['status']=='REJECTED'
    assert client.post('/disputes/D003/run',json={'note':'x'*2001}).status_code==422
    assert client.post('/disputes/D003/decision',json={'decision':'PAY','run_id':'x'}).status_code==422


def test_voice_and_demo(client):
    invalid=client.post('/disputes/D001/voice',files={'audio':('note.wav',b'bad','audio/wav')})
    assert invalid.status_code==422
    voice=client.post('/disputes/D001/voice',files={'audio':('note.wav',wav_bytes(),'audio/wav')})
    assert voice.status_code==200 and voice.json()['mode']=='mock'
    assert client.post('/disputes/D001/verify-demo').status_code==409
    result=client.post('/disputes/D001/run',json={}).json()
    assert result['trace'][0]['step']=='voice'
    assert result['note']==voice.json()['transcript']
    demo=client.post('/disputes/D001/verify-demo').json()
    assert not demo['verification']['passed'] and demo['action']=='ESCALATE'
    assert client.get('/disputes/D001').json()['result']==result


def test_all_cases_match_ground_truth(client):
    for case in client.get('/disputes').json():
        result=client.post(f"/disputes/{case['id']}/run",json={'note':''})
        assert result.status_code==200
        assert result.json()['action']==read_data(f"disputes/{case['id']}.json")['expected_action']
        assert result.json()['verification']['passed']


def test_cors(client):
    response=client.options('/disputes',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET'})
    assert response.headers['access-control-allow-origin']=='http://localhost:5173'
