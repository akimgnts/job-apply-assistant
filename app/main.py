"""Job Apply web workspace, sharing the existing application database and agents."""
from contextlib import asynccontextmanager
import hmac
import ipaddress
import logging
import os
import base64
import hashlib
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from app.config import config
from app.web.api import router

logger = logging.getLogger(__name__)
WEB_DIR = Path(__file__).parent / 'web'
@asynccontextmanager
async def lifespan(app):
    from app.database.db import engine
    from app.database.db import Base
    from app.database.workflow_schema import ensure_workflow_schema
    Base.metadata.create_all(engine)
    ensure_workflow_schema(engine)
    schedulers = []
    try:
        from app.scheduler.email_ingestion_scheduler import start_scheduler
        scheduler = start_scheduler()
        if scheduler:
            schedulers.append(scheduler)
    except Exception as exc:
        logger.warning("Gmail scheduler not started: %s", type(exc).__name__)
    try:
        from app.scheduler.ats_ingestion_scheduler import start_ats_scheduler
        scheduler = start_ats_scheduler()
        if scheduler:
            schedulers.append(scheduler)
    except Exception as exc:
        logger.warning("ATS scheduler not started: %s", type(exc).__name__)
    try:
        yield
    finally:
        for scheduler in schedulers:
            scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan, title='Job Apply Assistant', description='Votre espace personnel de candidature', version='0.2.0')

SESSION_COOKIE = 'jobapply_session'
SESSION_TTL = 12 * 60 * 60


def _session_secret() -> str:
    return os.getenv('WEB_SESSION_SECRET') or os.getenv('WEB_ACCESS_TOKEN', '')


def _session_signature(payload: str) -> str:
    return hmac.new(_session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()


def _valid_session(value: str | None) -> bool:
    if not value or not _session_secret():
        return False
    try:
        payload, signature = value.rsplit('.', 1)
        expires = int(payload)
    except (ValueError, TypeError):
        return False
    return expires >= int(time.time()) and hmac.compare_digest(signature, _session_signature(payload))


def _password_configured() -> bool:
    return bool(os.getenv('WEB_LOGIN_PASSWORD') and _session_secret())


@app.post('/auth/login')
async def login(request: Request):
    """Create a short-lived signed browser session without exposing a bearer token."""
    if not _password_configured():
        return JSONResponse({'detail': 'WEB_LOGIN_PASSWORD et WEB_SESSION_SECRET doivent être configurés.'}, status_code=503)
    body = await request.json()
    password = str(body.get('password') or '')
    if not hmac.compare_digest(password, os.getenv('WEB_LOGIN_PASSWORD', '')):
        return JSONResponse({'detail': 'Mot de passe incorrect.'}, status_code=401)
    payload = str(int(time.time()) + SESSION_TTL)
    response = JSONResponse({'authenticated': True, 'expires_in': SESSION_TTL})
    response.set_cookie(SESSION_COOKIE, f'{payload}.{_session_signature(payload)}', max_age=SESSION_TTL,
                        httponly=True, secure=request.url.scheme == 'https', samesite='lax', path='/')
    return response


@app.post('/auth/logout')
async def logout():
    response = JSONResponse({'authenticated': False})
    response.delete_cookie(SESSION_COOKIE, path='/')
    return response


@app.get('/auth/me')
async def auth_me(request: Request):
    return {'authenticated': _valid_session(request.cookies.get(SESSION_COOKIE))}


def is_local(request: Request) -> bool:
    """Require both a loopback peer and host to avoid DNS-rebinding exposure."""
    try:
        peer = ipaddress.ip_address(request.client.host)
        return peer.is_loopback and request.url.hostname in ('localhost', '127.0.0.1', '::1')
    except (ValueError, AttributeError):
        return False


@app.middleware('http')
async def protect_workspace(request: Request, call_next):
    """Keep candidate data private and reject cross-origin writes."""
    if request.url.path.startswith('/api/'):
        token = os.getenv('WEB_ACCESS_TOKEN', '')
        session_ok = _valid_session(request.cookies.get(SESSION_COOKIE))
        if session_ok:
            pass
        elif token:
            supplied = request.headers.get('authorization', '')
            if not hmac.compare_digest(supplied.encode(), f'Bearer {token}'.encode()):
                return JSONResponse({'detail': 'Saisissez la clé d’accès de cet espace pour continuer.'}, status_code=401)
        elif _password_configured():
            return JSONResponse({'detail': 'Connexion requise.'}, status_code=401)
        elif not is_local(request) or config.APP_ENV == 'production':
            return JSONResponse({'detail': 'L’accès distant nécessite WEB_ACCESS_TOKEN sur le serveur.'}, status_code=403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            if origin and urlsplit(origin).netloc != request.url.netloc:
                return JSONResponse({'detail': 'Cette origine n’est pas autorisée.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request: Request, exc: SQLAlchemyError):
    """Expose an actionable message, never a connection string or SQL parameters."""
    logger.error('Workspace database request failed: %s', type(exc).__name__)
    return JSONResponse({'detail': 'La base de données est indisponible ou non initialisée. Vérifiez DATABASE_URL et les migrations, puis réessayez.'}, status_code=503)


@app.get('/health')
async def health_check():
    """Process liveness only; database availability is checked through the workspace."""
    return {'status': 'ok', 'environment': config.APP_ENV}


@app.get('/ready', include_in_schema=False)
def readiness_check():
    """Routing readiness: schema and database must be available."""
    from sqlalchemy import text
    from app.database.db import engine
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT id FROM opportunities LIMIT 1'))
        return {'status': 'ready'}
    except Exception:
        return JSONResponse({'status': 'unavailable'}, status_code=503)


@app.get('/', include_in_schema=False)
async def root():
    return FileResponse(WEB_DIR / 'index.html')


from app.api.tracking import router as tracking_router
from app.api.daily import router as daily_router
from app.api.preparation import router as preparation_router
from app.api.workflow import router as workflow_router
from app.api.assistant import router as assistant_router
app.include_router(tracking_router)
app.include_router(daily_router)
app.include_router(preparation_router)
app.include_router(workflow_router)
app.include_router(assistant_router)
app.include_router(router)
app.mount('/static', StaticFiles(directory=WEB_DIR / 'static'), name='static')
