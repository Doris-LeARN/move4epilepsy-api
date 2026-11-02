"""Repair known encoding damage in the medication catalog."""

from sqlalchemy import text

from app.database.base import engine


NAME_FIXES = {
    "Carbamaz?\ufffdpine": "Carbamazépine",
    "Clonaz?\ufffdpam": "Clonazépam",
    "L?\ufffdv?\ufffdtirac?\ufffdtam": "Lévétiracétam",
    "Oxcarbaz?\ufffdpine": "Oxcarbazépine",
    "Ph?\ufffdnyto?\ufffdne": "Phénytoïne",
    "Pr?\ufffdgabaline": "Prégabaline",
}

FORM_FIXES = {
    "Comprim?\ufffd": "Comprimé",
    "G?\ufffdlule": "Gélule",
}


def migrate_medication_accents() -> int:
    repaired = 0
    with engine.begin() as connection:
        for damaged, corrected in NAME_FIXES.items():
            result = connection.execute(
                text("UPDATE medications SET name = :corrected WHERE name = :damaged"),
                {"damaged": damaged, "corrected": corrected},
            )
            repaired += result.rowcount

        for damaged, corrected in FORM_FIXES.items():
            result = connection.execute(
                text("UPDATE medications SET form = :corrected WHERE form = :damaged"),
                {"damaged": damaged, "corrected": corrected},
            )
            repaired += result.rowcount

    print(f"Médicaments corrigés: {repaired}")
    return repaired


if __name__ == "__main__":
    migrate_medication_accents()
