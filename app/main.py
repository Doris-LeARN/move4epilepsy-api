"""
Move4Epilepsy API - Application principale - SÉCURISÉE
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from app.core.config import settings
from app.api.v1.router import api_router
from app.database.base import engine, Base
import os

# Configuration logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Créer le répertoire logs s'il n'existe pas
os.makedirs(settings.LOG_DIR, exist_ok=True)

# Créer les tables au démarrage (pour le développement)
# En production, utiliser Alembic pour les migrations
Base.metadata.create_all(bind=engine)

# Configuration docs selon l'environnement
docs_url = f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None
redoc_url = "/redoc" if settings.DEBUG else None

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API pour l'application Move4Epilepsy",
    openapi_url=docs_url,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=redoc_url,
)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.client.host}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )

# Configuration CORS stricte
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Trusted Host Middleware (sécurité)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# Middleware pour les headers de sécurité
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Headers de sécurité HTTP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Logging d'accès
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    
    return response

# Inclusion des routes API
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Endpoint de base pour vérifier que l'API fonctionne"""
    return {
        "message": "Move4Epilepsy API",
        "version": settings.VERSION,
        "docs": "/docs" if settings.DEBUG else None,
        "environment": settings.ENVIRONMENT,
    }

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
    }

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 API starting - Environment: {settings.ENVIRONMENT}")
    if settings.ENVIRONMENT == "production" and settings.DEBUG:
        logger.warning("⚠️  DEBUG mode enabled in production!")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 API shutting down")
