"""
Base de données - Configuration SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Création du moteur SQLAlchemy avec encodage UTF-8
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # Affiche les requêtes SQL en mode debug
    connect_args={
        "client_encoding": "utf8",
        "options": "-c client_encoding=utf8"
    } if "postgresql" in settings.DATABASE_URL else {}
)

# Session locale
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles
Base = declarative_base()


def get_db():
    """
    Dépendance pour obtenir une session de base de données
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
