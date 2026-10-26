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


def test_password_login_uses_http_only_session_cookie(monkeypatch):
    monkeypatch.setenv('WEB_LOGIN_PASSWORD', 'correct-password')
    monkeypatch.setenv('WEB_SESSION_SECRET', 'a-long-test-session-secret')
    client = TestClient(app, base_url='https://localhost')
    assert client.get('/api/settings').status_code == 401
    assert client.post('/auth/login', json={'password': 'wrong'}).status_code == 401
    response = client.post('/auth/login', json={'password': 'correct-password'})
    assert response.status_code == 200
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    assert client.get('/api/settings').status_code != 401
    assert client.post('/auth/logout').status_code == 200
    assert client.get('/api/settings').status_code == 401


def test_static_assets_are_served():
    client = TestClient(app)
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/static/styles.css').status_code == 200


def test_readiness_checks_database_and_hides_errors(monkeypatch):
    from app.main import app
    import app.database.db as database
    class BrokenEngine:
        def connect(self):
            raise RuntimeError('private-database-credentials')
    monkeypatch.setattr(database, 'engine', BrokenEngine())
    response = TestClient(app).get('/ready')
    assert response.status_code == 503
    assert 'private-database-credentials' not in response.text
    assert TestClient(app).get('/health').status_code == 200
