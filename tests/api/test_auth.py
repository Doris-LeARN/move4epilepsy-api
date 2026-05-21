"""Tests pour les endpoints d'authentification"""
import pytest
from fastapi import status


class TestAuthRegister:
    """Tests pour POST /auth/register"""
    
    def test_register_success(self, client):
        """Test enregistrement utilisateur réussi"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "hashed_password" not in data
    
    def test_register_duplicate_username(self, client, test_user):
        """Test que username en doublon est rejeté"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "different@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"]
    
    def test_register_duplicate_email(self, client, test_user):
        """Test que email en doublon est rejeté"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "differentuser",
                "email": "testuser@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"]
    
    def test_register_invalid_email(self, client):
        """Test que email invalide est rejeté"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "invalid-email",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthLogin:
    """Tests pour POST /auth/login"""
    
    def test_login_success(self, client, test_user):
        """Test connexion réussie"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, test_user):
        """Test connexion avec mauvais mot de passe"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test connexion utilisateur inexistant"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "anypassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_inactive_user(self, client, db_session):
        """Test connexion utilisateur inactif"""
        from app.models.user import User, UserProfile
        from app.core.security import get_password_hash
        
        user = User(
            username="inactiveuser",
            email="inactive@example.com",
            hashed_password=get_password_hash("pass123"),
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "inactiveuser", "password": "pass123"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Inactive user" in response.json()["detail"]


class TestAuthMe:
    """Tests pour GET /auth/me"""
    
    def test_get_current_user_authenticated(self, client, auth_headers):
        """Test récupération utilisateur courant authentifié"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"
    
    def test_get_current_user_no_token(self, client):
        """Test récupération sans token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_current_user_invalid_token(self, client):
        """Test récupération avec token invalide"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthProfile:
    """Tests pour GET /auth/me/profile"""
    
    def test_get_profile_authenticated(self, client, auth_headers):
        """Test récupération profil utilisateur"""
        response = client.get(
            "/api/v1/auth/me/profile",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "patient"
