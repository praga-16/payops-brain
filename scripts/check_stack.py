"""HTTP acceptance checks for a running local or Docker stack."""
import argparse
import httpx


def check(frontend: str, backend: str) -> dict:
    with httpx.Client(timeout=30) as c:
        assert c.get(frontend).status_code==200
        assert c.get(backend+'/health').json()['ok']
        assert c.get(frontend+'/api/health').json()['ok']
        summary=c.get(frontend+'/api/dashboard/summary').json()
        assert summary['total_transactions']>=16 and summary['synthetic_only']
        assert len(c.get(frontend+'/api/disputes').json())==30
        assert c.get(frontend+'/api/notices/D001.png').headers['content-type']=='image/png'
        assert c.get(frontend+'/api/audit').json()['integrity']['valid']
        report=c.get(frontend+'/api/evaluation').json()['report']
        assert report and report['transaction_count']==512
        return {'frontend':200,'backend':200,'proxy':'passed','audit':'valid',
                'transactions':summary['total_transactions'],'evaluation_cases':report['case_count']}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--frontend',default='http://127.0.0.1:8080')
    parser.add_argument('--backend',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    print(check(args.frontend,args.backend))
