from decimal import Decimal
from fastapi.testclient import TestClient
from backend.simulator import seed
from backend.impact import impact_report
from backend.review import persist,review_case
from backend.dispute_intelligence import analyze
from backend.ledger import connect


def test_impact_is_not_fabricated_recovery(tmp_path,monkeypatch):
    path=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(path));seed(32,70,path)
    persist(analyze(path),path)
    result=impact_report(path)
    assert result['resolved_recovery_paise']==0
    assert result['ground_truth_coverage']==32
    assert Decimal(result['per_100000_transactions']['leakage_found_rupees'])==(
        Decimal(result['leakage_found_paise'])/100*100000/32).quantize(Decimal('.01'))
    with connect(path) as c:
        c.execute('INSERT INTO synthetic_recoveries VALUES(?,?,?,?)',('RECOVERY-1','SIM-70-32-T00001',100,'synthetic observed adjustment'))
    assert impact_report(path)['resolved_recovery_paise']==100
    from backend.main import app
    with TestClient(app) as c:assert c.get('/api/impact').json()['synthetic']
