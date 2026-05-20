"""
Validations strictes pour les inputs - Prévention des injections & malveillances
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class StrictStringField:
    """Validateur pour strings - prévient les injections"""
    
    @staticmethod
    def validate_username(v: str) -> str:
        """Valide username: alphanumérique + - _ . seulement"""
        if not v:
            raise ValueError("Username cannot be empty")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must be at most 50 characters")
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Username can only contain letters, numbers, ., -, _")
        return v
    
    @staticmethod
    def validate_email(v: str) -> str:
        """Valide email - format RFC 5322 simple"""
        if not v:
            raise ValueError("Email cannot be empty")
        if len(v) > 254:
            raise ValueError("Email too long")
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v
    
    @staticmethod
    def validate_safe_string(v: str, max_len: int = 500) -> str:
        """Valide string générique - élimine les caractères dangereux"""
        if not v:
            return ""
        if len(v) > max_len:
            raise ValueError(f"String too long (max {max_len})")
        # Élimine certains caractères contrôle potentiellement dangereux
        dangerous_chars = ['\x00', '\x1a', '\x1b', '\x1c', '\x1d', '\x1e', '\x1f']
        for char in dangerous_chars:
            if char in v:
                raise ValueError("Invalid characters detected")
        return v

class StrictIntField:
    """Validateur pour nombres - prévient les overflow"""
    
    @staticmethod
    def validate_age(v: int) -> int:
        """Valide l'âge: 0-150"""
        if v < 0 or v > 150:
            raise ValueError("Age must be between 0 and 150")
        return v
    
    @staticmethod
    def validate_effectiveness(v: int) -> int:
        """Valide score d'efficacité: 1-10"""
        if v < 1 or v > 10:
            raise ValueError("Effectiveness must be between 1 and 10")
        return v
    
    @staticmethod
    def validate_positive_int(v: int, max_val: int = 10000) -> int:
        """Valide un entier positif avec max"""
        if v < 0 or v > max_val:
            raise ValueError(f"Value must be between 0 and {max_val}")
        return v

# Schémas validés pour les inputs sensibles
class ValidatedUserInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=254)
    
    @validator('username')
    def validate_username(cls, v):
        return StrictStringField.validate_username(v)
    
    @validator('email')
    def validate_email(cls, v):
        return StrictStringField.validate_email(v)

class ValidatedTreatmentInput(BaseModel):
    age: int
    effectiveness: int
    
    @validator('age')
    def validate_age(cls, v):
        return StrictIntField.validate_age(v)
    
    @validator('effectiveness')
    def validate_effectiveness(cls, v):
        return StrictIntField.validate_effectiveness(v)
