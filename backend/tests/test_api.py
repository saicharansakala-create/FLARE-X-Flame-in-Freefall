from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health():
 r=client.get('/api/health'); assert r.status_code==200 and r.json()['status']=='ok'
def test_dataset_summary():
 d=client.get('/api/datasets/summary').json(); assert d['catalogue_investigations']==24 and d['prevention_measures']==136 and d['accidents']==14
def test_mission_rank():
 d=client.get('/api/mission/rank?habitat=Moon%20base').json(); assert len(d['items'])>0 and d['items'][0]['score']>=d['items'][-1]['score']
def test_validation():
 d=client.get('/api/validation/report').json(); assert d['passed']>=4 and d['scientific_scope']
def test_assistant():
 d=client.post('/api/assistant/ask',json={'question':'What does BASS-II show about low airflow and flame stability?','habitat':'Moon base'}).json(); assert d['answer'] and d['mode'] and d['mission_context']['habitat']=='Moon base' and d['mission_context']['top_investigations']
def test_assistant_changes_with_habitat():
 q='Which investigations are useful for fire safety and flame spread?'
 moon=client.post('/api/assistant/ask',json={'question':q,'habitat':'Moon base'}).json()
 mars=client.post('/api/assistant/ask',json={'question':q,'habitat':'Mars base'}).json()
 assert moon['mission_context']['habitat']=='Moon base'
 assert mars['mission_context']['habitat']=='Mars base'
 assert moon['mission_context']['top_investigations'] and mars['mission_context']['top_investigations']
def test_workbook_sheet():
 d=client.get('/api/workbook/Accidents').json(); assert d['total']==14
