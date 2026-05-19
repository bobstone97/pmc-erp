"""Apply lightweight schema updates (run: python -m database.migrate)."""
from sqlalchemy import inspect, text

from database.connection import get_engine, init_db


def column_exists(inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspector.get_columns(table)}


def run_migrations():
    init_db()
    engine = get_engine()
    inspector = inspect(engine)
    alters = [
        ("doctor_expense", "attachment_path", "VARCHAR(500)"),
        ("sales_person_expense", "attachment_path", "VARCHAR(500)"),
        ("company_expense", "attachment_path", "VARCHAR(500)"),
    ]
    with engine.connect() as conn:
        for table, col, col_type in alters:
            if not column_exists(inspector, table, col):
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
                print(f"Added {table}.{col}")
    print("Migrations complete.")


if __name__ == "__main__":
    run_migrations()
