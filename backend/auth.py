"""SQLite-backed user accounts and cookie sessions for the VertexFlow API.

Passwords are hashed with scrypt from the standard library, so no extra
dependency is required. Sessions are server-side rows referenced by a random
token stored in an HttpOnly cookie, which makes them revocable on logout.
"""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator

SESSION_COOKIE = "vf_session"
SESSION_TTL = timedelta(days=7)

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# scrypt cost parameters: ~16 MiB per hash, which is a reasonable interactive cost.
_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DB_PATH = Path(
    os.environ.get("VERTEXFLOW_DB") or Path(__file__).resolve().parent / "vertexflow.db"
)
COOKIE_SECURE = os.environ.get("VERTEXFLOW_COOKIE_SECURE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL_PATTERN.match(email):
            raise ValueError("Enter a valid email address.")
        return email

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Use at least {MIN_PASSWORD_LENGTH} characters.")
        if len(value) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Use at most {MAX_PASSWORD_LENGTH} characters.")
        return value


class UserOut(BaseModel):
    id: int
    email: str
    created_at: str


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #


def hash_password(password: str) -> str:
    """Return a self-describing scrypt hash with a random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of a password against a stored hash."""
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


# Compared against when the email is unknown so that a failed login costs the
# same time whether or not the account exists.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    """Create the account and session tables if they do not exist yet."""
    with _db() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)"
        )


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #


def _create_session(connection: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (_iso(now),))
    connection.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_hash_token(token), user_id, _iso(now), _iso(now + SESSION_TTL)),
    )
    return token


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def _unauthorised(detail: str = "Sign in to continue.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def require_user(request: Request) -> UserOut:
    """FastAPI dependency that resolves the signed-in user or raises 401."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _unauthorised()

    with _db() as connection:
        row = connection.execute(
            """
            SELECT u.id AS id, u.email AS email, u.created_at AS created_at,
                   s.expires_at AS expires_at
            FROM sessions AS s
            JOIN users AS u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (_hash_token(token),),
        ).fetchone()

        if row is None:
            raise _unauthorised()

        if row["expires_at"] <= _iso(_now()):
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),)
            )
            raise _unauthorised("Your session expired. Sign in again.")

    return UserOut(id=row["id"], email=row["email"], created_at=row["created_at"])


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, response: Response) -> UserOut:
    """Create an account and start a session."""
    now = _iso(_now())
    password_hash = hash_password(payload.password)

    try:
        with _db() as connection:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (payload.email, password_hash, now),
            )
            user_id = int(cursor.lastrowid or 0)
            token = _create_session(connection, user_id)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        ) from exc

    _set_session_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return UserOut(id=user_id, email=payload.email, created_at=now)


@router.post("/login", response_model=UserOut)
def login(payload: Credentials, response: Response) -> UserOut:
    """Exchange email and password for a session cookie."""
    with _db() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (payload.email,),
        ).fetchone()

        if row is None:
            verify_password(payload.password, _DUMMY_HASH)
            raise _unauthorised("Incorrect email or password.")

        if not verify_password(payload.password, row["password_hash"]):
            raise _unauthorised("Incorrect email or password.")

        token = _create_session(connection, row["id"])

    _set_session_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return UserOut(id=row["id"], email=row["email"], created_at=row["created_at"])


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> Response:
    """Revoke the current session server-side and clear the cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with _db() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),)
            )

    # An injected Response has no status yet; without this uvicorn fails with
    # KeyError: None while writing the status line.
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return response


@router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(require_user)) -> UserOut:
    """Return the signed-in user, or 401 when the session is missing or expired."""
    return user
