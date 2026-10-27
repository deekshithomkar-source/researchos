from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.core.config import settings
from app.db.database import get_db
from app.models.user import AuthSession, User
from app.schemas.auth import AuthUserResponse, LoginRequest, SignupRequest
from app.services.user_store import COOKIE_NAME, authenticate_user, create_session, create_user, throttle_auth

router = APIRouter()


def auth_response(user, session, message):
    return {'id': user.id, 'name': user.name, 'email': user.email,
            'csrf_token': session.csrf_token, 'message': message}


@router.post('/signup', response_model=AuthUserResponse, status_code=201)
def signup(payload: SignupRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    throttle_auth(db, request)
    user = create_user(db, payload.name, payload.email, payload.password)
    session = create_session(db, user, request, response)
    return auth_response(user, session, 'Account created successfully.')


@router.post('/signin', response_model=AuthUserResponse)
def signin(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    throttle_auth(db, request)
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(401, 'Invalid email or password.')
    session = create_session(db, user, request, response)
    return auth_response(user, session, 'Signed in successfully.')


@router.get('/me', response_model=AuthUserResponse)
def me(user: User = Depends(get_current_user), session: AuthSession = Depends(get_session)):
    return auth_response(user, session, 'Authenticated.')


@router.post('/signout', status_code=204)
def signout(response: Response, session: AuthSession = Depends(get_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path='/api', secure=settings.cookie_secure,
                           httponly=True, samesite=settings.cookie_samesite)


@router.post('/reset-password', status_code=501)
def reset_password():
    # Never accept an email + new password as proof of account ownership.
    raise HTTPException(501, 'Password recovery is not available yet. A verified email recovery flow is required.')
