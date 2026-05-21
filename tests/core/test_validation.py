"""Tests pour les validateurs d'input"""
import pytest
from app.core.validation import StrictStringField, StrictIntField


class TestUsernameValidation:
    """Tests validation username"""
    
    def test_valid_username(self):
        """Test username valide"""
        assert StrictStringField.validate_username("valid_user123") == "valid_user123"
        assert StrictStringField.validate_username("user-with-dash") == "user-with-dash"
        assert StrictStringField.validate_username("user.with.dot") == "user.with.dot"
    
    def test_username_too_short(self):
        """Test username trop court"""
        with pytest.raises(ValueError, match="at least 3 characters"):
            StrictStringField.validate_username("ab")
    
    def test_username_too_long(self):
        """Test username trop long"""
        with pytest.raises(ValueError, match="at most 50 characters"):
            StrictStringField.validate_username("a" * 51)
    
    def test_username_invalid_characters(self):
        """Test username avec caractères invalides"""
        with pytest.raises(ValueError, match="can only contain"):
            StrictStringField.validate_username("user@invalid")
        
        with pytest.raises(ValueError):
            StrictStringField.validate_username("user with spaces")
    
    def test_username_empty(self):
        """Test username vide"""
        with pytest.raises(ValueError, match="cannot be empty"):
            StrictStringField.validate_username("")


class TestEmailValidation:
    """Tests validation email"""
    
    def test_valid_email(self):
        """Test email valide"""
        assert StrictStringField.validate_email("user@example.com") == "user@example.com"
        assert StrictStringField.validate_email("test.user@domain.co.uk") == "test.user@domain.co.uk"
    
    def test_email_invalid_format(self):
        """Test email format invalide"""
        with pytest.raises(ValueError, match="Invalid email"):
            StrictStringField.validate_email("notanemail")
        
        with pytest.raises(ValueError):
            StrictStringField.validate_email("user@")
        
        with pytest.raises(ValueError):
            StrictStringField.validate_email("@example.com")
    
    def test_email_too_long(self):
        """Test email trop long"""
        with pytest.raises(ValueError, match="too long"):
            StrictStringField.validate_email("a" * 300 + "@example.com")
    
    def test_email_empty(self):
        """Test email vide"""
        with pytest.raises(ValueError, match="cannot be empty"):
            StrictStringField.validate_email("")


class TestSafeStringValidation:
    """Tests validation string générique"""
    
    def test_valid_string(self):
        """Test string valide"""
        result = StrictStringField.validate_safe_string("This is a safe string")
        assert result == "This is a safe string"
    
    def test_string_too_long(self):
        """Test string trop long"""
        with pytest.raises(ValueError, match="too long"):
            StrictStringField.validate_safe_string("a" * 501, max_len=500)
    
    def test_string_with_control_characters(self):
        """Test string avec caractères de contrôle"""
        with pytest.raises(ValueError, match="Invalid characters"):
            StrictStringField.validate_safe_string("text\x00with\x1anull")
    
    def test_empty_string_allowed(self):
        """Test que string vide est acceptée"""
        result = StrictStringField.validate_safe_string("")
        assert result == ""


class TestAgeValidation:
    """Tests validation âge"""
    
    def test_valid_age(self):
        """Test âge valide"""
        assert StrictIntField.validate_age(0) == 0
        assert StrictIntField.validate_age(35) == 35
        assert StrictIntField.validate_age(150) == 150
    
    def test_age_too_low(self):
        """Test âge trop bas"""
        with pytest.raises(ValueError, match="between 0 and 150"):
            StrictIntField.validate_age(-1)
    
    def test_age_too_high(self):
        """Test âge trop haut"""
        with pytest.raises(ValueError, match="between 0 and 150"):
            StrictIntField.validate_age(151)


class TestEffectivenessValidation:
    """Tests validation effectiveness"""
    
    def test_valid_effectiveness(self):
        """Test effectiveness valide"""
        assert StrictIntField.validate_effectiveness(1) == 1
        assert StrictIntField.validate_effectiveness(5) == 5
        assert StrictIntField.validate_effectiveness(10) == 10
    
    def test_effectiveness_too_low(self):
        """Test effectiveness trop bas"""
        with pytest.raises(ValueError, match="between 1 and 10"):
            StrictIntField.validate_effectiveness(0)
    
    def test_effectiveness_too_high(self):
        """Test effectiveness trop haut"""
        with pytest.raises(ValueError, match="between 1 and 10"):
            StrictIntField.validate_effectiveness(11)


class TestPositiveIntValidation:
    """Tests validation entiers positifs"""
    
    def test_valid_positive_int(self):
        """Test entier positif valide"""
        assert StrictIntField.validate_positive_int(0) == 0
        assert StrictIntField.validate_positive_int(100) == 100
        assert StrictIntField.validate_positive_int(10000, max_val=10000) == 10000
    
    def test_negative_int_rejected(self):
        """Test que négatif est rejeté"""
        with pytest.raises(ValueError):
            StrictIntField.validate_positive_int(-1)
    
    def test_exceeds_max_value(self):
        """Test que dépasse max est rejeté"""
        with pytest.raises(ValueError):
            StrictIntField.validate_positive_int(10001, max_val=10000)
