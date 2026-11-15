"""Card-like pattern rejection and defense-in-depth JSON response masking."""
from __future__ import annotations
import json
import re
import logging
from backend.ledger import connect

# Exclude embedded identifiers, hashes and decimal fractions. Match standalone
# 13..19 digits, including conventional space/hyphen card grouping.
PAN=re.compile(r'(?<![\w.])(?:\d[ -]?){12,18}\d(?![\w.])')


def has_pan(value: object) -> bool:
    if isinstance(value,dict):return any(has_pan(v) for v in value.values())
    if isinstance(value,(list,tuple)):return any(has_pan(v) for v in value)
    return bool(PAN.search(str(value))) if value is not None else False


def mask_text(text: str) -> str:
    return PAN.sub(lambda m:'**** **** **** '+re.sub(r'\D','',m.group())[-4:],text)


class CardLogFilter(logging.Filter):
    def filter(self,record) -> bool:
        record.msg=mask_text(record.getMessage());record.args=()
        return True


def install_log_filters() -> None:
    for name in ('payops.control_tower','uvicorn.access'):
        logger=logging.getLogger(name)
        if not any(isinstance(f,CardLogFilter) for f in logger.filters):logger.addFilter(CardLogFilter())


def sanitize(value):
    if isinstance(value,dict):return {k:sanitize(v) for k,v in value.items()}
    if isinstance(value,list):return [sanitize(v) for v in value]
    if isinstance(value,str):return mask_text(value)
    if isinstance(value,int) and has_pan(value):return mask_text(str(value))
    return value


def scan_database(path=None) -> dict:
    findings=[];scanned=0
    with connect(path) as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            quoted='"'+table.replace('"','""')+'"'
            for row in c.execute('SELECT * FROM '+quoted):
                scanned+=1
                for column in row.keys():
                    if has_pan(row[column]):findings.append({'table':table,'column':column})
    return {'synthetic':True,'rows_scanned':scanned,'card_like_findings':findings,
            'note':'Pattern scan excludes hashes/identifiers and decimal fractions. This is not a certified DLP or PCI assessment.'}


class CardSafetyMiddleware:
    def __init__(self,app):self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]));request_receive=receive
        if b'application/json' in headers.get(b'content-type',b''):
            chunks=[]
            while True:
                message=await receive()
                chunks.append(message.get('body',b''))
                if not message.get('more_body'):break
            raw=b''.join(chunks)
            try:unsafe=has_pan(json.loads(raw))
            except (ValueError,UnicodeDecodeError):unsafe=False
            if unsafe:
                body=b'{"detail":"Use masked/tokenized synthetic card references only."}'
                await send({'type':'http.response.start','status':422,'headers':[(b'content-type',b'application/json'),(b'content-length',str(len(body)).encode())]})
                return await send({'type':'http.response.body','body':body})
            used=False
            async def replay_receive():
                nonlocal used
                if not used:used=True;return {'type':'http.request','body':raw,'more_body':False}
                return await receive()
            request_receive=replay_receive
        start=None;body_parts=[];json_response=False
        async def safe_send(message):
            nonlocal start,json_response
            if message['type']=='http.response.start':
                json_response=b'application/json' in dict(message.get('headers',[])).get(b'content-type',b'')
                if json_response:start=message;return
            if message['type']=='http.response.body' and json_response:
                body_parts.append(message.get('body',b''))
                if message.get('more_body'):return
                body=b''.join(body_parts)
                try:body=json.dumps(sanitize(json.loads(body)),ensure_ascii=False,separators=(',',':')).encode()
                except (ValueError,UnicodeDecodeError):pass
                start['headers']=[(k,v) for k,v in start['headers'] if k.lower()!=b'content-length']+[(b'content-length',str(len(body)).encode())]
                await send(start);return await send({'type':'http.response.body','body':body})
            await send(message)
        await self.app(scope,request_receive,safe_send)
