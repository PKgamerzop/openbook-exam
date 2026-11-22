import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from threading import BoundedSemaphore
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import Connection

from app.store import now, one, rows, transaction

router = APIRouter(prefix="/api")
DB = Annotated[Connection, Depends(transaction, scope="function")]
COOKIE = "openbook_session"
TTL = timedelta(hours=8)
password_checks = BoundedSemaphore(2)


def derive(password, salt):
    return hashlib.scrypt(
        password.encode(), salt=salt, n=2**17, r=8, p=1, maxmem=256 * 1024**2
    ).hex()


def password_hash(password):
    salt = secrets.token_bytes(16)
    return salt.hex() + "." + derive(password, salt)


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(min_length=1, max_length=256)


def identity(request: Request, db: DB):
    user = one(
        db,
        """SELECT a.id,a.role,a.username FROM account a
               JOIN login_session s ON a.id=s.user_id
               WHERE s.digest=:key AND s.expires_at>:time""",
        key=digest(request.cookies.get(COOKIE, "")),
        time=now(),
    )
    if not user:
        raise HTTPException(401, "Sign in to continue")
    return dict(user)


def lecturer(user=Depends(identity)):
    if user["role"] != "lecturer":
        raise HTTPException(403, "Lecturer access required")
    return user["id"]


def student(user=Depends(identity)):
    if user["role"] != "student":
        raise HTTPException(403, "Student access required")
    return user["id"]


Lecturer = Annotated[int, Depends(lecturer)]
Student = Annotated[int, Depends(student)]


@router.post("/login")
def login(data: Login, request: Request, response: Response, db: DB):
    user = one(db, "SELECT * FROM account WHERE username=:u", u=data.username)
    salt, expected = (user["password_hash"] if user else "00." + "0" * 128).split(".")
    if not password_checks.acquire(blocking=False):
        raise HTTPException(429, "Sign-in is busy. Try again shortly.")
    try:
        actual = derive(data.password.get_secret_value(), bytes.fromhex(salt))
    finally:
        password_checks.release()
    if not hmac.compare_digest(actual, expected) or not user:
        raise HTTPException(401, "Invalid username or password")
    token = secrets.token_urlsafe(32)
    time = now()
    rows(
        db,
        "DELETE FROM login_session WHERE expires_at<=:t OR digest=:old RETURNING 1",
        t=time,
        old=digest(request.cookies.get(COOKIE, "")),
    )
    rows(
        db,
        """INSERT INTO login_session VALUES (:key,:uid,:expiry) RETURNING 1""",
        key=digest(token),
        uid=user["id"],
        expiry=time + TTL,
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        path="/api",
        secure=os.getenv("OPENBOOK_LOCAL_HTTP") != "1",
        max_age=int(TTL.total_seconds()),
    )
    return {k: user[k] for k in ("id", "username", "role")}


@router.get("/me")
def me(user=Depends(identity)):
    return user


@router.post("/logout")
def logout(request: Request, response: Response, db: DB, user=Depends(identity)):
    rows(
        db,
        "DELETE FROM login_session WHERE digest=:key RETURNING 1",
        key=digest(request.cookies.get(COOKIE, "")),
    )
    response.delete_cookie(COOKIE, path="/api")
    return {"signed_out": True}
