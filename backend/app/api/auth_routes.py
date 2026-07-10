from fastapi import APIRouter, HTTPException

from app.schemas.auth import AuthUserResponse, LoginRequest, ResetPasswordRequest, SignupRequest
from app.services.user_store import authenticate_user, create_user, reset_password


router = APIRouter()


@router.post("/signup", response_model=AuthUserResponse)
def signup(payload: SignupRequest):
    try:
        user = create_user(payload.name, payload.email, payload.password)
    except ValueError as error:
        if str(error) == "USER_EXISTS":
            raise HTTPException(status_code=409, detail="User already exists. Please sign in.") from error
        raise

    return {**user, "message": "Account created successfully."}


@router.post("/signin", response_model=AuthUserResponse)
def signin(payload: LoginRequest):
    user = authenticate_user(payload.email, payload.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password. Please check your details and try again.")

    return {**user, "message": "Signed in successfully."}


@router.post("/reset-password", response_model=AuthUserResponse)
def change_password(payload: ResetPasswordRequest):
    user = reset_password(payload.email, payload.password)

    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email. Please create an account first.")

    return {**user, "message": "Password changed successfully. Please sign in with your new password."}
