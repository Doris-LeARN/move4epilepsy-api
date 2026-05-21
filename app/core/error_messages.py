"""
Gestion centralisée des messages d'erreur sécurisés
Masque les détails internes, expose des messages génériques à l'utilisateur
"""

from enum import Enum
from typing import Dict


class ErrorCategory(str, Enum):
    """Catégories d'erreurs standardisées"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    SERVER_ERROR = "server_error"
    RATE_LIMIT = "rate_limit"


# Mapping: Erreur backend → Message générique
ERROR_MESSAGE_MAP: Dict[str, Dict[str, str]] = {
    # === AUTHENTIFICATION ===
    "Incorrect username or password": {
        "user_message": "Identifiants invalides. Veuillez réessayer.",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": "info",
    },
    "User not found": {
        "user_message": "Identifiants invalides. Veuillez réessayer.",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": "info",
    },
    "Account is inactive": {
        "user_message": "Ce compte a été désactivé. Contactez l'administrateur.",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": "warning",
    },
    "Account suspended": {
        "user_message": "Ce compte a été suspendu. Veuillez nous contacter.",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": "warning",
    },
    "Invalid token": {
        "user_message": "Votre session a expiré. Veuillez vous reconnecter.",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": "info",
    },
    "Token expired": {
        "user_message": "Votre session a expiré. Veuillez vous reconnecter.",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": "info",
    },
    "Unauthorized": {
        "user_message": "Authentification requise.",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": "info",
    },

    # === INSCRIPTION ===
    "Username already registered": {
        "user_message": "Ce nom d'utilisateur est déjà utilisé. Veuillez en choisir un autre.",
        "category": ErrorCategory.CONFLICT,
        "severity": "info",
    },
    "Email already registered": {
        "user_message": "Un compte avec cet email existe déjà.",
        "category": ErrorCategory.CONFLICT,
        "severity": "info",
    },
    "Email already exists": {
        "user_message": "Un compte avec cet email existe déjà.",
        "category": ErrorCategory.CONFLICT,
        "severity": "info",
    },

    # === VALIDATION ===
    "Invalid email format": {
        "user_message": "Format email invalide.",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },
    "Password must be at least 12 characters": {
        "user_message": "Le mot de passe doit contenir au moins 12 caractères.",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },
    "Password must contain at least one uppercase letter": {
        "user_message": "Le mot de passe doit contenir au moins une majuscule.",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },
    "Password must contain at least one digit": {
        "user_message": "Le mot de passe doit contenir au moins un chiffre.",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },
    "Invalid username": {
        "user_message": "Le nom d'utilisateur contient des caractères invalides.",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },
    "Age must be between 0 and 150": {
        "user_message": "L'âge doit être entre 0 et 150 ans.",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },
    "Effectiveness must be between 1 and 10": {
        "user_message": "L'efficacité doit être entre 1 et 10.",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },

    # === RESSOURCES ===
    "Treatment not found": {
        "user_message": "Ce traitement n'existe pas ou a été supprimé.",
        "category": ErrorCategory.NOT_FOUND,
        "severity": "info",
    },
    "User not found": {
        "user_message": "Cet utilisateur n'existe pas.",
        "category": ErrorCategory.NOT_FOUND,
        "severity": "info",
    },
    "Medication not found": {
        "user_message": "Ce médicament n'existe pas.",
        "category": ErrorCategory.NOT_FOUND,
        "severity": "info",
    },
    "Pharmacy not found": {
        "user_message": "Cette pharmacie n'existe pas.",
        "category": ErrorCategory.NOT_FOUND,
        "severity": "info",
    },

    # === AUTORISATION ===
    "Forbidden": {
        "user_message": "Vous n'avez pas l'autorisation pour effectuer cette action.",
        "category": ErrorCategory.AUTHORIZATION,
        "severity": "warning",
    },
    "Admin access required": {
        "user_message": "Accès administrateur requis.",
        "category": ErrorCategory.AUTHORIZATION,
        "severity": "warning",
    },
    "Doctor access required": {
        "user_message": "Accès médecin requis.",
        "category": ErrorCategory.AUTHORIZATION,
        "severity": "warning",
    },

    # === RATE LIMITING ===
    "Too many requests": {
        "user_message": "Trop de requêtes. Veuillez attendre quelques minutes.",
        "category": ErrorCategory.RATE_LIMIT,
        "severity": "info",
    },

    # === SERVEUR ===
    "Internal server error": {
        "user_message": "Une erreur serveur s'est produite. Veuillez réessayer plus tard.",
        "category": ErrorCategory.SERVER_ERROR,
        "severity": "error",
    },
    "Database error": {
        "user_message": "Une erreur de base de données s'est produite. Veuillez réessayer plus tard.",
        "category": ErrorCategory.SERVER_ERROR,
        "severity": "error",
    },
}


def get_user_message(backend_error: str) -> Dict[str, str]:
    """
    Mappe un message d'erreur backend à un message générique pour l'utilisateur
    
    Args:
        backend_error: Message d'erreur du backend
        
    Returns:
        Dict avec:
        - user_message: Message à afficher à l'utilisateur
        - category: Catégorie d'erreur
        - severity: Niveau de sévérité (info, warning, error)
    """
    # Chercher correspondance exacte
    if backend_error in ERROR_MESSAGE_MAP:
        return ERROR_MESSAGE_MAP[backend_error]
    
    # Chercher correspondance partielle (dans le message)
    for error_key, error_info in ERROR_MESSAGE_MAP.items():
        if error_key.lower() in backend_error.lower():
            return error_info
    
    # Par défaut: message générique
    return {
        "user_message": "Une erreur est survenue. Veuillez réessayer.",
        "category": ErrorCategory.SERVER_ERROR,
        "severity": "error",
    }


# Alias pour utilisation facile
def map_error(error: str) -> str:
    """Retourne le message utilisateur pour un erreur donnée"""
    return get_user_message(error)["user_message"]


def map_error_with_category(error: str) -> Dict[str, str]:
    """Retourne le mapping complet d'une erreur"""
    return get_user_message(error)


# Messages par défaut pour les cas courants
DEFAULT_MESSAGES = {
    "success": "Opération réussie.",
    "password_reset_sent": "Un email de réinitialisation a été envoyé.",
    "profile_updated": "Profil mis à jour avec succès.",
    "treatment_created": "Traitement enregistré avec succès.",
    "treatment_updated": "Traitement mis à jour avec succès.",
}
