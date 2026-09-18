"""The workspace must not expose private candidate data over an unprotected host."""
from fastapi.testclient import TestClient
from app.main import app


def test_frontend_is_served_without_connecting_database():
    response = TestClient(app).get('/')
    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']
    assert 'jobapply' in response.text


def test_remote_host_requires_key(monkeypatch):
    monkeypatch.delenv('WEB_ACCESS_TOKEN', raising=False)
    response = TestClient(app, base_url='http://remote.example').get('/api/settings')
    assert response.status_code == 403


def test_key_is_required_when_configured(monkeypatch):
    monkeypatch.setenv('WEB_ACCESS_TOKEN', 'test-secret')
    client = TestClient(app, base_url='http://localhost')
    assert client.get('/api/settings').status_code == 401
    assert client.get('/api/settings', headers={'Authorization': 'Bearer wrong'}).status_code == 401


def test_cross_origin_mutations_rejected(monkeypatch):
    monkeypatch.setenv('WEB_ACCESS_TOKEN', 'test-secret')
    response = TestClient(app, base_url='http://localhost').post('/api/import-snapshot', headers={
        'Authorization': 'Bearer test-secret', 'Origin': 'https://untrusted.example'})
    assert response.status_code == 403


def test_static_assets_are_served():
    client = TestClient(app)
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/static/styles.css').status_code == 200
