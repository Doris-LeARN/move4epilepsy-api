"""Ajoute les liens de propriété nécessaires aux suppressions RGPD.

Usage depuis move4epilepsy-api :
    python scripts/migrate_add_data_ownership.py

La migration est idempotente pour PostgreSQL. Les colonnes restent nullable afin
 de préserver les traitements et opinions anonymes déjà enregistrés.
"""
from sqlalchemy import inspect, text

from app.database.base import engine


def add_column_if_missing(table_name: str, column_name: str) -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        print(f"{table_name}.{column_name}: already exists")
        return

    if engine.dialect.name == "postgresql":
        if table_name == "patient_treatments":
            statement = (
                "ALTER TABLE patient_treatments "
                "ADD COLUMN user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE"
            )
        else:
            statement = (
                "ALTER TABLE user_opinions "
                "ADD COLUMN user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE"
            )
    elif engine.dialect.name == "sqlite":
        statement = f"ALTER TABLE {table_name} ADD COLUMN user_id VARCHAR(36)"
    else:
        raise RuntimeError(f"Unsupported database dialect: {engine.dialect.name}")

    with engine.begin() as connection:
        connection.execute(text(statement))
    print(f"{table_name}.{column_name}: added")


def create_index_if_missing(index_name: str, table_name: str) -> None:
    inspector = inspect(engine)
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in indexes:
        return

    with engine.begin() as connection:
        connection.execute(text(f"CREATE INDEX {index_name} ON {table_name} (user_id)"))
    print(f"{index_name}: added")


def main() -> None:
    add_column_if_missing("patient_treatments", "user_id")
    add_column_if_missing("user_opinions", "user_id")
    create_index_if_missing("ix_patient_treatments_user_id", "patient_treatments")
    create_index_if_missing("ix_user_opinions_user_id", "user_opinions")


if __name__ == "__main__":
    main()
