"""
Configuration pytest et fixtures globales
"""
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Importer après avoir configuré l'env
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.database.base import Base, get_db
from app.models.user import User, UserProfile
from app.core.security import get_password_hash


@pytest.fixture(scope="session")
def test_db():
    """Crée une base de données test en mémoire"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield engine, SessionLocal
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Crée une session DB pour chaque test"""
    engine, SessionLocal = test_db
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Client FastAPI avec DB de test"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Crée un utilisateur de test"""
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    
    profile = UserProfile(
        user_id=user.id,
        username="testuser",
        role="patient",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def test_admin(db_session):
    """Crée un utilisateur admin de test"""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    
    profile = UserProfile(
        user_id=user.id,
        username="admin",
        role="admin",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Retourne les headers d'authentification JWT"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client, test_admin):
    """Retourne les headers d'authentification admin"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "adminpass123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
