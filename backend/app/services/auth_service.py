from werkzeug.security import generate_password_hash, check_password_hash

from app.models.user import User
from app.extensions import db


def create_user(username, password, role="user"):
    existing_user = User.query.filter_by(
        username=username
    ).first()

    if existing_user:
        return None

    password_hash = generate_password_hash(password)

    user = User(
        username=username,
        password_hash=password_hash,
        role=role
    )

    db.session.add(user)
    db.session.commit()

    return user


def verify_user(username, password):
    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        return None

    if not check_password_hash(
        user.password_hash,
        password
    ):
        return None

    return user