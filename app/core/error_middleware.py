"""
Middleware pour standardiser les réponses d'erreur API
Mappe les messages d'erreur internes à des messages génériques
"""

import logging
from typing import Callable, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.error_messages import get_user_message, ErrorCategory

logger = logging.getLogger(__name__)


class ErrorMappingMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui intercept les réponses d'erreur et les mappe à des messages génériques
    
    Cela évite:
    - L'exposition d'informations sensibles (chemins, versions, etc.)
    - L'énumération d'utilisateurs/comptes
    - La fuite de détails internes du serveur
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            
            # Logger les erreurs (côté serveur)
            if response.status_code >= 400:
                logger.warning(
                    "HTTP %d %s %s",
                    response.status_code,
                    request.method,
                    request.url.path,
                )
            
            return response
            
        except StarletteHTTPException as exc:
            # Les exceptions HTTP sont loggées mais pas leurs détails
            logger.info(
                "HTTPException %d: %s",
                exc.status_code,
                request.url.path,
            )
            
            # Mapper le message d'erreur
            error_data = get_user_message(str(exc.detail))
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "message": error_data.get("user_message"),
                        "category": error_data.get("category"),
                        "severity": error_data.get("severity"),
                    }
                },
            )
            
        except Exception as exc:
            # Erreurs non gérées: message générique sans détails
            logger.exception("Unhandled exception in %s %s", request.method, request.url.path)
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "message": "Une erreur serveur s'est produite. Veuillez réessayer plus tard.",
                        "category": ErrorCategory.SERVER_ERROR,
                        "severity": "error",
                    }
                },
            )


def create_error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    category: Optional[str] = None,
    severity: Optional[str] = None,
) -> JSONResponse:
    """
    Crée une réponse d'erreur standardisée
    
    Args:
        message: Message d'erreur (sera mappé)
        status_code: Code HTTP
        category: Catégorie d'erreur (optionnel, auto-détecté si absent)
        severity: Niveau de sévérité (optionnel, auto-détecté si absent)
        
    Returns:
        JSONResponse formatée
    """
    error_data = get_user_message(message)
    
    if category:
        error_data["category"] = category
    if severity:
        error_data["severity"] = severity
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": error_data.get("user_message"),
                "category": error_data.get("category"),
                "severity": error_data.get("severity"),
            }
        },
    )
