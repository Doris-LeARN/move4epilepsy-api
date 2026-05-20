"""
Configuration pytest - Fixtures partagées et configuration test
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.base import Base, get_db
from app.main import app
from fastapi.testclient import TestClient


# Database test - en mémoire SQLite
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def test_db():
    """Créer une base de test pour la session"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    # Nettoyer le fichier test.db
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def test_session(test_db):
    """Créer une session test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()
    
    def override_get_db():
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Client de test FastAPI"""
    return TestClient(app)


# Marqueurs personnalisés pour les tests
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: marque un test unitaire"
    )
    config.addinivalue_line(
        "markers", "integration: marque un test d'intégration"
    )
    config.addinivalue_line(
        "markers", "security: marque un test de sécurité"
    )
    config.addinivalue_line(
        "markers", "slow: marque un test lent"
    )
