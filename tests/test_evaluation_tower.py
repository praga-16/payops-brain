from backend.evaluation import run_evaluation,wilson
from backend.ledger import initialize


def test_heldout_evaluation_reproducible(tmp_path):
    path=tmp_path/'db';initialize(path)
    a=run_evaluation(count=64,test_seed=916,path=path)
    b=run_evaluation(count=64,test_seed=916,persist=False)
    assert a['baseline']==b['baseline'] and a['assisted']==b['assisted']
    assert a['transaction_count']==64
    assert a['sample_counts']['assisted']['classified']==64
    for method in ('baseline','assisted'):
        assert all(v is None or 0<=v<=1 for v in a[method].values())
        assert a[method]['false_auto_resolution_rate']==0
    assert a['assisted']['break_classification_accuracy']>=a['baseline']['break_classification_accuracy']
    assert 'Synthetic-demo' in a['limitations']
    assert wilson(0,0) is None
    assert wilson(0,10)[1]>0
