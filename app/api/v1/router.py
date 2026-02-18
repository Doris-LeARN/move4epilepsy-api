"""
Routeur principal pour l'API v1
"""
from fastapi import APIRouter
from app.api.v1 import auth, medications, pharmacies, search, patients, chat, subscriptions, opinions, admin, routing

api_router = APIRouter()

# Inclusion des routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(medications.router, prefix="/medications", tags=["medications"])
api_router.include_router(pharmacies.router, prefix="/pharmacies", tags=["pharmacies"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(opinions.router, prefix="", tags=["opinions"])  # Pas de prefix pour /opinions, /partnerships, etc.
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(routing.router, prefix="/routing", tags=["routing"])
