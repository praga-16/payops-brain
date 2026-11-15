from decimal import Decimal
import pytest
from backend.merchant import chat,merchant_facts,UNCERTAIN
from backend.simulator import seed
from backend.ledger import records


@pytest.mark.parametrize('language,question,token',[
    ('en','Why is my settlement short?','Expected fees'),
    ('hi','मेरा भुगतान अभी तक सेटल क्यों नहीं हुआ?','अपेक्षित'),
    ('ta','இந்த UPI settlement ஏன் குறைவாக உள்ளது?','எதிர்பார்க்கப்படும்')])
def test_multilingual_ledger_answers(tmp_path,language,question,token):
    path=tmp_path/'db';seed(32,42,path)
    result=chat('SYN-M001',question,language,path=path)
    assert result['grounded'] and token in result['text']
    assert result['facts']['gross'] in result['text']
    tx=[t for t in records('transactions',path) if t['merchant_id']=='SYN-M001']
    assert Decimal(result['facts']['gross'])*100 == sum(t['amount_paise'] for t in tx)


def test_uncertainty_and_merchant_scope(tmp_path):
    path=tmp_path/'db';seed(32,42,path)
    for merchant,question in [('SYN-M999','settlement'),('SYN-M001','When will it settle?'),('SYN-M001','tell me a joke')]:
        assert chat(merchant,question,path=path)['text']==UNCERTAIN
    assert merchant_facts('SYN-M001',path,transaction_id='nonexistent') is None
