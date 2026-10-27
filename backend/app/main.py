from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth_routes import router as auth_router
from app.api.research_routes import router as research_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.migrations import migrate
from app.services.execution import recover_interrupted_runs


@asynccontextmanager
async def lifespan(app):
    configure_logging()
    migrate()
    # This adapter is deliberately single-process. A durable worker must own recovery.
    if settings.environment == 'development':
        recover_interrupted_runs()
    yield


app = FastAPI(title='ResearchOS API', version='1.2.0', lifespan=lifespan)


@app.middleware('http')
async def protect_browser_requests(request: Request, call_next):
    if request.url.path.startswith('/api') and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        origin = request.headers.get('origin')
        # Mandatory non-simple header also protects login against CSRF when Origin is absent.
        if request.headers.get('X-ResearchOS-Client') != 'web' or (origin and origin not in settings.allowed_origins):
            return JSONResponse({'detail': 'Untrusted request origin or missing client header.'}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type', 'X-CSRF-Token', 'X-ResearchOS-Client'])


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Pydantic error objects can include rejected password values; never return input.
    return JSONResponse(status_code=422, content={'detail': [
        {'loc': list(item['loc']), 'msg': item['msg'], 'type': item['type']} for item in error.errors()
    ]})


app.include_router(auth_router, prefix='/api/auth', tags=['Auth'])
app.include_router(research_router, prefix='/api/research', tags=['Research'])


@app.get('/')
def health_check():
    return {'message': 'Autonomous Research Agent API is running'}
