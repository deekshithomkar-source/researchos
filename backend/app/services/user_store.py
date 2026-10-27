"""Database-backed accounts, credential verification, and session lifecycle."""
import secrets
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, Request, Response

from app.core.config import settings
from app.core.security import DUMMY_HASH, hash_password, password_hasher, token_digest, verify_password
from app.models.user import AuthRateLimit, AuthSession, User, utcnow

COOKIE_NAME = 'researchos_session'


def throttle_auth(db, request: Request):
    # Trust the socket peer, not caller-controlled forwarding headers.
    key = token_digest(request.client.host if request.client else 'unknown')
    now = utcnow()
    db.execute(delete(AuthRateLimit).where(AuthRateLimit.expires_at <= now))
    statement = insert(AuthRateLimit).values(
        key=key, attempts=1, expires_at=now + timedelta(seconds=settings.auth_window_seconds)
    ).on_conflict_do_update(index_elements=['key'], set_={'attempts': AuthRateLimit.attempts + 1})
    db.execute(statement)
    db.commit()
    if db.get(AuthRateLimit, key).attempts > settings.auth_attempts:
        raise HTTPException(429, 'Too many authentication attempts. Try again later.', headers={'Retry-After': str(settings.auth_window_seconds)})


def create_user(db, name: str, email: str, password: str) -> User:
    user = User(name=name.strip(), email=email.strip().lower(), password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, 'Unable to create account. Try signing in.') from error
    db.refresh(user)
    return user


def authenticate_user(db, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not verify_password(password, user.password_hash if user else DUMMY_HASH) or user is None:
        return None
    if user.password_hash.startswith('legacy$') or password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def create_session(db, user: User, request: Request, response: Response) -> AuthSession:
    old_token = request.cookies.get(COOKIE_NAME)
    if old_token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(old_token)))
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))
    token = secrets.token_urlsafe(32)
    session = AuthSession(token_hash=token_digest(token), user_id=user.id,
                          csrf_token=secrets.token_urlsafe(32),
                          expires_at=utcnow() + timedelta(hours=settings.session_hours))
    db.add(session)
    db.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=settings.session_hours * 3600,
                        httponly=True, secure=settings.cookie_secure,
                        samesite=settings.cookie_samesite, path='/api')
    return session
