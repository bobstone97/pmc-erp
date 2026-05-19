"""Initialize database and create default admin user."""
import bcrypt

from config import PAGE_KEYS
from database.connection import get_session, init_db
from database.models import User, UserPermission


def seed_admin():
    with get_session() as session:
        existing = session.query(User).filter_by(username="admin").first()
        if existing:
            print("Admin user already exists.")
            return
        password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        admin = User(
            username="admin",
            password_hash=password_hash,
            full_name="System Administrator",
            role="admin",
            is_active=True,
        )
        session.add(admin)
        session.flush()
        for page_key in PAGE_KEYS:
            session.add(
                UserPermission(
                    user_id=admin.id,
                    page_key=page_key,
                    can_view=True,
                    can_edit=True,
                )
            )
        print("Default admin created: username=admin, password=admin123")


if __name__ == "__main__":
    init_db()
    from database.migrate import run_migrations

    run_migrations()
    seed_admin()
    print("Database initialized successfully.")
