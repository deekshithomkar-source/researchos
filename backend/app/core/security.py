"""Argon2id password hashes and standard opaque session tokens."""
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        if encoded.startswith("legacy$"):
            _, salt, wrapped_hash = encoded.split("$", 2)
            password = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
            encoded = wrapped_hash
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError, ValueError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
