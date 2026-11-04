from fastapi.testclient import TestClient
from services.api.app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_projects_list():
    response = client.get('/api/v1/projects')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_project_validation():
    response = client.post('/api/v1/projects', json={'name': 'X', 'description': ''})
    assert response.status_code == 422
