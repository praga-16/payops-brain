import os
from pathlib import Path
import pytest


def test_packaging_has_safe_runtime_and_proxy():
    root=Path(__file__).resolve().parents[1]
    assert '.env' in (root/'.dockerignore').read_text()
    assert 'USER payops' in (root/'Dockerfile').read_text()
    assert 'payops-data:/app/runtime' in (root/'compose.yaml').read_text()
    nginx=(root/'frontend/nginx.conf').read_text()
    assert 'health|disputes|notices' in nginx and 'location /api/' in nginx
    for command in ('install','test','seed','demo','eval','run'):
        assert command+':' in (root/'Makefile').read_text()


@pytest.mark.skipif(os.getenv('PAYOPS_DOCKER_TEST')!='1',reason='Requires a running Docker stack; opt in with PAYOPS_DOCKER_TEST=1')
def test_running_docker_stack():
    from scripts.check_stack import check
    result=check(os.getenv('PAYOPS_FRONTEND_URL','http://127.0.0.1:8080'),
                 os.getenv('PAYOPS_BACKEND_URL','http://127.0.0.1:8001'))
    assert result['audit']=='valid'
