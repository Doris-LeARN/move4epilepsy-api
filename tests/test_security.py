"""
Tests pour la sécurité - JWT, hashing, validation
"""
import pytest
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.core.validation import StrictStringField, StrictIntField
from datetime import timedelta


# ============================================================================
# TESTS HASHING & PASSWORD
# ============================================================================

def test_password_hash_not_plain():
    """Vérifier que le hash n'est pas le password en clair"""
    password = "mysecurepassword"
    hashed = get_password_hash(password)
    assert hashed != password


def test_password_hash_different_each_time():
    """Vérifier que les hashes sont différents même pour le même password"""
    password = "mysecurepassword"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    assert hash1 != hash2


def test_verify_password_correct():
    """Vérifier que verify_password fonctionne avec le bon password"""
    password = "mysecurepassword"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Vérifier que verify_password échoue avec mauvais password"""
    password = "mysecurepassword"
    hashed = get_password_hash(password)
    assert verify_password("wrongpassword", hashed) is False


def test_password_hash_long_password():
    """Tester avec un password très long (>72 bytes)"""
    long_password = "a" * 100
    hashed = get_password_hash(long_password)
    # Devrait fonctionner (tronqué à 72 bytes)
    assert verify_password(long_password, hashed) is True


# ============================================================================
# TESTS JWT TOKENS
# ============================================================================

def test_create_access_token():
    """Tester la création d'un token JWT"""
    data = {"sub": "testuser"}
    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_with_expiry():
    """Tester la création d'un token avec expiration personnalisée"""
    data = {"sub": "testuser"}
    expires_delta = timedelta(minutes=60)
    token = create_access_token(data, expires_delta)
    assert isinstance(token, str)


def test_decode_valid_token():
    """Tester le décodage d'un token valide"""
    data = {"sub": "testuser"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "testuser"


def test_decode_invalid_token():
    """Tester le décodage d'un token invalide"""
    invalid_token = "invalid.token.here"
    decoded = decode_access_token(invalid_token)
    assert decoded is None


def test_decode_expired_token():
    """Tester le décodage d'un token expiré"""
    data = {"sub": "testuser"}
    # Token expirant dans -1 minute (déjà expiré)
    expires_delta = timedelta(minutes=-1)
    token = create_access_token(data, expires_delta)
    decoded = decode_access_token(token)
    assert decoded is None


# ============================================================================
# TESTS VALIDATION USERNAME
# ============================================================================

def test_username_valid():
    """Tester un username valide"""
    valid_usernames = [
        "user",
        "user123",
        "user_name",
        "user-name",
        "user.name",
        "u",  # Sera rejeté (trop court)
    ]
    for username in valid_usernames:
        try:
            result = StrictStringField.validate_username(username)
            # Doit être au moins 3 chars
            if len(username) >= 3:
                assert result == username
        except ValueError:
            assert len(username) < 3


def test_username_too_short():
    """Tester qu'un username trop court est rejeté"""
    with pytest.raises(ValueError):
        StrictStringField.validate_username("ab")


def test_username_invalid_characters():
    """Tester que les caractères invalides sont rejetés"""
    invalid = ["user@invalid", "user#test", "user invalid", "user/name"]
    for username in invalid:
        with pytest.raises(ValueError):
            StrictStringField.validate_username(username)


def test_username_too_long():
    """Tester qu'un username trop long est rejeté"""
    long_username = "a" * 51
    with pytest.raises(ValueError):
        StrictStringField.validate_username(long_username)


# ============================================================================
# TESTS VALIDATION EMAIL
# ============================================================================

def test_email_valid():
    """Tester des emails valides"""
    valid_emails = [
        "user@example.com",
        "test.user@example.co.uk",
        "user+tag@example.com",
        "user123@test.org",
    ]
    for email in valid_emails:
        result = StrictStringField.validate_email(email)
        assert result == email


def test_email_invalid():
    """Tester des emails invalides"""
    invalid_emails = [
        "notanemail",
        "user@",
        "@example.com",
        "user @example.com",
        "user@.com",
    ]
    for email in invalid_emails:
        with pytest.raises(ValueError):
            StrictStringField.validate_email(email)


def test_email_empty():
    """Tester qu'un email vide est rejeté"""
    with pytest.raises(ValueError):
        StrictStringField.validate_email("")


# ============================================================================
# TESTS VALIDATION SAFE STRING
# ============================================================================

def test_safe_string_valid():
    """Tester une string sûre"""
    safe_string = "This is a safe string"
    result = StrictStringField.validate_safe_string(safe_string)
    assert result == safe_string


def test_safe_string_dangerous_chars():
    """Tester qu'une string avec caractères dangereux est rejetée"""
    dangerous_string = "string\x00with\x1bnull"
    with pytest.raises(ValueError):
        StrictStringField.validate_safe_string(dangerous_string)


def test_safe_string_too_long():
    """Tester qu'une string trop longue est rejetée"""
    long_string = "a" * 501
    with pytest.raises(ValueError):
        StrictStringField.validate_safe_string(long_string)


# ============================================================================
# TESTS VALIDATION INTEGERS
# ============================================================================

def test_age_valid():
    """Tester des âges valides"""
    valid_ages = [0, 1, 18, 50, 100, 150]
    for age in valid_ages:
        result = StrictIntField.validate_age(age)
        assert result == age


def test_age_invalid():
    """Tester des âges invalides"""
    invalid_ages = [-1, 151, 200]
    for age in invalid_ages:
        with pytest.raises(ValueError):
            StrictIntField.validate_age(age)


def test_effectiveness_valid():
    """Tester des scores d'efficacité valides"""
    valid_scores = [1, 5, 10]
    for score in valid_scores:
        result = StrictIntField.validate_effectiveness(score)
        assert result == score


def test_effectiveness_invalid():
    """Tester des scores d'efficacité invalides"""
    invalid_scores = [0, 11, -1, 100]
    for score in invalid_scores:
        with pytest.raises(ValueError):
            StrictIntField.validate_effectiveness(score)


def test_positive_int_valid():
    """Tester des entiers positifs valides"""
    valid_ints = [0, 1, 50, 100, 10000]
    for value in valid_ints:
        result = StrictIntField.validate_positive_int(value)
        assert result == value


def test_positive_int_invalid():
    """Tester des entiers positifs invalides"""
    invalid_ints = [-1, 10001, 50000]
    for value in invalid_ints:
        with pytest.raises(ValueError):
            StrictIntField.validate_positive_int(value)
