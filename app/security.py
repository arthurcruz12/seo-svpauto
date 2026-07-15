import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
if os.getenv("ENVIRONMENT", "development") == "production" and SECRET_KEY == "change-this-secret-key-in-production":
    raise RuntimeError("SECRET_KEY must be configured in production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_PERMISSIONS = {
    "admin": {"users:manage", "companies:write", "companies:read", "documents:write", "documents:read", "audit:read", "dashboard:read"},
    "accountant": {"companies:write", "companies:read", "documents:write", "documents:read", "audit:read", "dashboard:read"},
    "manager": {"companies:read", "documents:read", "dashboard:read"},
    "employee": {"documents:write", "documents:read"},
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(data: dict, token_type: str, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return create_token(data, "access", expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return create_token(data, "refresh", expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid authentication token") from exc
    if expected_type and payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    return payload


def decode_access_token(token: str) -> dict:
    return decode_token(token, "access")


def decode_refresh_token(token: str) -> dict:
    return decode_token(token, "refresh")


def require_permission(user, permission: str) -> None:
    if permission not in ROLE_PERMISSIONS.get(user.role, set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
