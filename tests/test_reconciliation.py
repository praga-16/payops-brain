from copy import deepcopy

import pytest
from backend import audit
from backend.ledger import records, connect
from backend.reconciliation import analyze, match, match_model
from backend.review import persist, queue
from backend.simulator import seed, BREAKS


def test_all_breaks_and_evidence(tmp_path):
    path=tmp_path/'ledger.db'
    seed(160,42,path)
    results=analyze(path)
    assert {r['break_type'] for r in results}==set(BREAKS+['CLEAN'])
    assert persist(results,path)==160
    assert persist(results,path)==0
    assert any(r['tier']=='AUTO_RESOLVED' for r in queue(path))
    with connect(path) as conn:
        assert audit.verify(conn)['valid']
    bad=deepcopy(results[0]); bad['decision']['case_id']='BAD'; bad['decision']['evidence']=['FAKE']
    with pytest.raises(ValueError,match='nonexistent'):
        persist([bad],path)


def test_reference_priority_and_ambiguous_candidates(tmp_path):
    path=tmp_path/'ledger.db'; seed(32,42,path)
    tx=records('transactions',path)[9]
    original=next(s for s in records('settlements',path) if s['transaction_id']==tx['id'])
    assert match(tx,[original])[1]=='exact reference'
    normalized={**original,'transaction_id':None,'reference':tx['id'].lower().replace('-','')}
    assert match(tx,[normalized])[1]=='normalized reference rule'
    fuzzy={**normalized,'reference':tx['id']+'x'}
    assert match(tx,[fuzzy])[1]=='fuzzy reference + gradient boosting'
    assert not match(tx,[fuzzy,{**fuzzy,'id':'SECOND'}])[0]
    assert not match(tx,[normalized],assisted=False)[0]
    assert match_model().n_features_in_==6


def test_wrong_amount_cannot_auto_resolve(tmp_path):
    path=tmp_path/'ledger.db';seed(32,42,path)
    with connect(path) as c:
        c.execute('UPDATE settlements SET amount_paise=1')
    results=analyze(path)
    assert not any(r['decision']['action']=='RECONCILE' for r in results)


def test_cross_transaction_citation_and_amount_rejected_atomically(tmp_path):
    path=tmp_path/'ledger.db';seed(32,42,path)
    result=analyze(path)[0]
    unrelated=deepcopy(result)
    unrelated['decision']['evidence'].append('SIM-42-32-T00001')
    with pytest.raises(ValueError,match='unrelated'):
        persist([unrelated],path)
    wrong=deepcopy(result);wrong['decision']['amount']='1.00'
    with pytest.raises(ValueError,match='amount'):
        persist([wrong],path)
    assert queue(path)==[]
