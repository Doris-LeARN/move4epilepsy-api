#!/usr/bin/env python3
"""
Crée les canaux de chat par défaut s’ils n’existent pas encore (idempotent).

Usage (depuis la racine du projet API, avec la base configurée dans .env) :

    PYTHONPATH=. python scripts/seed_default_chat_channels.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.base import SessionLocal  # noqa: E402
from app.models.chat import ChatChannel  # noqa: E402

DEFAULT_CHANNELS: list[dict] = [
    {
        "name": "Général",
        "description": "Discussions ouvertes entre membres de la communauté.",
        "type": "general",
        "is_active": True,
    },
    {
        "name": "Soutien",
        "description": "Entraide et accompagnement entre patients.",
        "type": "support",
        "is_active": True,
    },
    {
        "name": "Traitements",
        "description": "Échanges sur les médicaments et le vécu du traitement (sans poser de diagnostic).",
        "type": "medication",
        "is_active": True,
    },
    {
        "name": "Professionnels de santé",
        "description": "Espace dédié aux échanges avec ou entre professionnels.",
        "type": "professional",
        "is_active": True,
    },
]


def main() -> None:
    db = SessionLocal()
    created = 0
    try:
        for data in DEFAULT_CHANNELS:
            exists = db.query(ChatChannel).filter(ChatChannel.name == data["name"]).first()
            if exists:
                continue
            db.add(ChatChannel(**data))
            created += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if created:
        print(f"Canaux créés : {created}.")
    else:
        print("Aucun nouveau canal (déjà présents ou rien à ajouter).")


if __name__ == "__main__":
    main()
