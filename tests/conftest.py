import os
os.environ['PAYOPS_MOCK'] = 'true'
import pytest
from copy import deepcopy
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.main import app, cases, lock
    with lock:
        saved = deepcopy(cases)
        for case in cases.values():
            case.update(status='QUEUED', result=None, decisions=[], running=False)
            case.pop('voice', None)
    with TestClient(app) as test_client:
        yield test_client
    with lock:
        cases.clear()
        cases.update(saved)
