import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_FILE = DATA_DIR / "users.json"


def create_user(name: str, email: str, password: str) -> dict:
    data = _read_users()
    normalized_email = email.lower()

    if _find_user(data, normalized_email):
        raise ValueError("USER_EXISTS")

    now = _utc_now()
    salt = secrets.token_hex(16)
    user = {
        "id": secrets.token_hex(8),
        "name": name.strip(),
        "email": normalized_email,
        "password_hash": _hash_password(password, salt),
        "password_salt": salt,
        "created_at": now,
        "updated_at": now,
    }

    data["users"].append(user)
    _write_users(data)
    return _public_user(user)


def authenticate_user(email: str, password: str) -> dict | None:
    data = _read_users()
    user = _find_user(data, email.lower())

    if not user:
        return None

    expected_hash = _hash_password(password, user["password_salt"])
    if not secrets.compare_digest(expected_hash, user["password_hash"]):
        return None

    return _public_user(user)


def reset_password(email: str, password: str) -> dict | None:
    data = _read_users()
    user = _find_user(data, email.lower())

    if not user:
        return None

    salt = secrets.token_hex(16)
    user["password_hash"] = _hash_password(password, salt)
    user["password_salt"] = salt
    user["updated_at"] = _utc_now()
    _write_users(data)
    return _public_user(user)


def _read_users() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        return {"users": []}

    with USERS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        return {"users": []}

    return data


def _write_users(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = USERS_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temp_file.replace(USERS_FILE)


def _find_user(data: dict, email: str) -> dict | None:
    return next((user for user in data["users"] if user.get("email") == email), None)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def _public_user(user: dict) -> dict:
    return {"name": user["name"], "email": user["email"]}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
