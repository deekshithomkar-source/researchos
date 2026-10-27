import secrets
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import token_digest
from app.db.database import get_db
from app.models.user import AuthSession, User, utcnow
from app.services.user_store import COOKIE_NAME


def get_session(request: Request, db: Session = Depends(get_db)) -> AuthSession:
    token = request.cookies.get(COOKIE_NAME, '')
    session = db.get(AuthSession, token_digest(token)) if token else None
    if session is None or session.expires_at <= utcnow():
        raise HTTPException(401, 'Please sign in to continue.')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        if not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), session.csrf_token):
            raise HTTPException(403, 'Invalid CSRF token. Refresh and try again.')
    return session


def get_current_user(session: AuthSession = Depends(get_session), db: Session = Depends(get_db)) -> User:
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, 'Please sign in to continue.')
    return user
