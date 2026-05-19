import bcrypt
from sqlalchemy.orm import Session

from database.models import User, UserPermission
from utils.permissions import default_permissions_for_role


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def authenticate(session: Session, username: str, password: str) -> User | None:
    user = (
        session.query(User)
        .filter(User.username == username, User.is_active.is_(True))
        .first()
    )
    if user and verify_password(password, user.password_hash):
        return user
    return None


def get_user_permissions(session: Session, user: User) -> dict:
    perms = {}
    for p in session.query(UserPermission).filter_by(user_id=user.id).all():
        perms[p.page_key] = {"can_view": p.can_view, "can_edit": p.can_edit}
    if not perms:
        perms = default_permissions_for_role(user.role)
    return perms


def create_user(
    session: Session,
    username: str,
    password: str,
    full_name: str,
    role: str,
    permissions: dict | None = None,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    perms = permissions or default_permissions_for_role(role)
    for page_key, access in perms.items():
        session.add(
            UserPermission(
                user_id=user.id,
                page_key=page_key,
                can_view=access.get("can_view", False),
                can_edit=access.get("can_edit", False),
            )
        )
    return user


def reset_password(session: Session, user_id: int, new_password: str):
    user = session.get(User, user_id)
    if user:
        user.password_hash = hash_password(new_password)


def set_user_active(session: Session, user_id: int, is_active: bool):
    user = session.get(User, user_id)
    if user:
        user.is_active = is_active


def update_user_permissions(session: Session, user_id: int, permissions: dict):
    session.query(UserPermission).filter_by(user_id=user_id).delete()
    for page_key, access in permissions.items():
        session.add(
            UserPermission(
                user_id=user_id,
                page_key=page_key,
                can_view=access.get("can_view", False),
                can_edit=access.get("can_edit", False),
            )
        )
