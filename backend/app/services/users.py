from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User


DEV_USER_EMAIL = "dev@example.local"


def get_or_create_dev_user(db: Session) -> User:
    user = db.query(User).filter(User.email == DEV_USER_EMAIL).first()
    if user:
        return user

    user = User(email=DEV_USER_EMAIL, display_name="Development User", auth_provider="dev")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
