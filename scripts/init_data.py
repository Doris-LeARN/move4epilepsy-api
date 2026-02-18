"""
Script pour initialiser les données de base (médicaments)
"""
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.base import SessionLocal
from app.models.medication import Medication


def init_medications(db: Session):
    """Insère les médicaments de base"""
    medications = [
        {"name": "Lévétiracétam", "dosage": "500mg", "form": "Comprimé"},
        {"name": "Lévétiracétam", "dosage": "1000mg", "form": "Comprimé"},
        {"name": "Lamotrigine", "dosage": "25mg", "form": "Comprimé"},
        {"name": "Lamotrigine", "dosage": "100mg", "form": "Comprimé"},
        {"name": "Carbamazépine", "dosage": "200mg", "form": "Comprimé"},
        {"name": "Carbamazépine", "dosage": "400mg", "form": "Comprimé"},
        {"name": "Valproate de sodium", "dosage": "250mg", "form": "Comprimé"},
        {"name": "Valproate de sodium", "dosage": "500mg", "form": "Comprimé"},
        {"name": "Phénytoïne", "dosage": "100mg", "form": "Gélule"},
        {"name": "Oxcarbazépine", "dosage": "300mg", "form": "Comprimé"},
        {"name": "Topiramate", "dosage": "25mg", "form": "Comprimé"},
        {"name": "Topiramate", "dosage": "100mg", "form": "Comprimé"},
        {"name": "Gabapentine", "dosage": "300mg", "form": "Gélule"},
        {"name": "Prégabaline", "dosage": "75mg", "form": "Gélule"},
        {"name": "Clonazépam", "dosage": "0.5mg", "form": "Comprimé"},
    ]
    
    created = 0
    skipped = 0
    
    for med_data in medications:
        # Vérifier si le médicament existe déjà
        existing = db.query(Medication).filter(
            Medication.name == med_data["name"],
            Medication.dosage == med_data["dosage"]
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        medication = Medication(**med_data)
        db.add(medication)
        created += 1
    
    db.commit()
    print(f"✅ Médicaments créés: {created}, ignorés: {skipped}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_medications(db)
        print("✅ Initialisation des données terminée")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        db.rollback()
    finally:
        db.close()
