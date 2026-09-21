"""Job Apply web workspace, sharing the existing application database and agents."""
from contextlib import asynccontextmanager
import hmac
import ipaddress
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from app.config import config
from app.web.api import router

logger = logging.getLogger(__name__)
WEB_DIR = Path(__file__).parent / 'web'
@asynccontextmanager
async def lifespan(app):
    from app.scheduler.email_ingestion_scheduler import start_scheduler
    scheduler = start_scheduler()
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan, title='Job Apply Assistant', description='Votre espace personnel de candidature', version='0.2.0')


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
        if token:
            supplied = request.headers.get('authorization', '')
            if not hmac.compare_digest(supplied.encode(), f'Bearer {token}'.encode()):
                return JSONResponse({'detail': 'Saisissez la clé d’accès de cet espace pour continuer.'}, status_code=401)
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
app.include_router(tracking_router)
app.include_router(router)
app.mount('/static', StaticFiles(directory=WEB_DIR / 'static'), name='static')
