"""Multilingual explanations of Python-computed merchant ledger facts."""
from __future__ import annotations

from backend.ledger import records, money
from backend.providers.factory import explain

UNCERTAIN="I'm not sure, routing to an analyst."


def merchant_facts(merchant_id: str, path=None, transaction_id: str | None = None) -> dict | None:
    transactions=[r for r in records('transactions',path) if r['merchant_id']==merchant_id and
                  (transaction_id is None or r['id']==transaction_id)]
    if not transactions:
        return None
    from backend.reconciliation import match
    settlements=records('settlements',path)
    matched=[(tx,match(tx,settlements)[0]) for tx in transactions]
    ids={r['id'] for r in transactions}
    dispute_count=sum(r['transaction_id'] in ids and r['status']=='OPEN' for r in records('disputes',path))
    gross=sum(t['amount_paise'] for t in transactions)
    fee=sum(t['fee_paise'] for t in transactions)
    net=sum(s['amount_paise'] for _,rows in matched for s in rows)
    return {'merchant_id':merchant_id,'transaction_count':len(transactions),'gross':money(gross),
            'expected_fees':money(fee),'expected_net':money(gross-fee),'observed_net':money(net),
            'missing_count':sum(not rows for _,rows in matched),
            'short_count':sum(bool(rows) and sum(s['amount_paise'] for s in rows)<t['amount_paise']-t['fee_paise'] for t,rows in matched),
            'duplicate_count':sum(len(rows)>1 for _,rows in matched),'open_disputes':dispute_count,
            'evidence':[r['id'] for r in transactions]}


def chat(merchant_id: str, question: str, language: str = 'en', *, transaction_id: str | None = None, path=None) -> dict:
    if language not in {'en','hi','ta'}:
        raise ValueError('Supported languages: en, hi, ta')
    facts=merchant_facts(merchant_id,path,transaction_id)
    question=question.lower()
    supported=any(token in question for token in ('settle','payment','disput','upi','short','reconcil',
                                                  'भुगतान','सेटल','विवाद','குறை','தீர்வு','பணம்','செட்டில்'))
    unknown_time=any(token in question for token in ('when','कब','எப்போது'))
    if facts is None or not supported or unknown_time:
        return {'text':UNCERTAIN,'confidence':.2,'routed_to_analyst':True,'provider':'local',
                'mode':'local','grounded':True,'facts':facts,'limitation':'No supported ledger evidence or completion-time prediction.'}
    if language=='hi':
        sentences=[f"सिंथेटिक व्यापारी {merchant_id}: {facts['transaction_count']} भुगतान, कुल INR {facts['gross']}।",
                   f"अपेक्षित शुल्क INR {facts['expected_fees']}; अपेक्षित शुद्ध निपटान INR {facts['expected_net']}; दर्ज निपटान INR {facts['observed_net']}।",
                   f"लापता निपटान: {facts['missing_count']}; कम निपटान: {facts['short_count']}; दोहरे निपटान: {facts['duplicate_count']}; खुले विवाद: {facts['open_disputes']}।",
                   'अंतर और विवादों की विश्लेषक समीक्षा आवश्यक है। कोई वास्तविक भुगतान नहीं किया गया।']
    elif language=='ta':
        sentences=[f"செயற்கை வணிகர் {merchant_id}: {facts['transaction_count']} பரிவர்த்தனைகள், மொத்தம் INR {facts['gross']}.",
                   f"எதிர்பார்க்கப்படும் கட்டணம் INR {facts['expected_fees']}; நிகரத் தீர்வு INR {facts['expected_net']}; பதிவான தீர்வு INR {facts['observed_net']}.",
                   f"விடுபட்ட தீர்வுகள்: {facts['missing_count']}; குறைவான தீர்வுகள்: {facts['short_count']}; இரட்டைத் தீர்வுகள்: {facts['duplicate_count']}; திறந்த சர்ச்சைகள்: {facts['open_disputes']}.",
                   'வேறுபாடுகளுக்கு ஆய்வாளர் மதிப்பாய்வு தேவை. உண்மையான பணப்பரிமாற்றம் செய்யப்படவில்லை.']
    else:
        sentences=[f"Synthetic merchant {merchant_id}: {facts['transaction_count']} transactions, gross INR {facts['gross']}.",
                   f"Expected fees INR {facts['expected_fees']}; expected net INR {facts['expected_net']}; recorded settlements INR {facts['observed_net']}.",
                   f"Missing settlements: {facts['missing_count']}; short settlements: {facts['short_count']}; duplicate settlements: {facts['duplicate_count']}; open disputes: {facts['open_disputes']}.",
                   'Differences and disputes require analyst review. No actual payment was executed.']
    return {**explain(sentences,facts=facts,language=language,task='Compose merchant settlement explanation.'),
            'confidence':.9,'routed_to_analyst':False,'facts':facts,
            'limitation':'Ledger totals explain observations; they do not establish a root cause or promise completion time.'}
