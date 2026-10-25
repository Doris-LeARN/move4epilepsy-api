"""Add checkout price snapshots to pharmacy subscriptions."""

from sqlalchemy import text

from app.database.base import engine


def migrate_subscription_checkout_fields():
    with engine.begin() as connection:
        connection.execute(text("""
            ALTER TABLE pharmacy_subscriptions
            ADD COLUMN IF NOT EXISTS billing_country VARCHAR;
        """))
        connection.execute(text("""
            ALTER TABLE pharmacy_subscriptions
            ADD COLUMN IF NOT EXISTS billing_period VARCHAR NOT NULL DEFAULT 'monthly';
        """))
        connection.execute(text("""
            ALTER TABLE pharmacy_subscriptions
            ADD COLUMN IF NOT EXISTS amount NUMERIC(10, 2);
        """))
        connection.execute(text("""
            ALTER TABLE pharmacy_subscriptions
            ADD COLUMN IF NOT EXISTS currency VARCHAR;
        """))
    print("Subscription checkout columns are ready.")


if __name__ == "__main__":
    migrate_subscription_checkout_fields()
