import hashlib
import hmac
import os
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.pilot_db import open_database

router = APIRouter(prefix="/api/account")
COOKIE = "remi_session"


def database():
    with open_database() as connection:
        yield connection


DB = Depends(database, scope="function")


def digest(token):
    return hashlib.sha256(token.encode()).digest()


def owner(request: Request, db=DB):
    row = db.execute("""SELECT s.student_id,s.display_name,m.moderator_id FROM web_tokens t
        JOIN students s USING(student_id) LEFT JOIN moderators m USING(student_id)
        WHERE digest=%s AND expires_at>now()""",(digest(request.cookies.get(COOKIE,"")),)).fetchone()
    if not row:
        raise HTTPException(401,"Войдите в профиль.")
    return row


def moderator(person=Depends(owner)):
    if not person["moderator_id"]:
        raise HTTPException(403,"Нужна роль модератора.")
    return person["moderator_id"]


def password_key(password, salt):
    return hashlib.scrypt(password.encode(),salt=salt,n=2**15,r=8,p=3,maxmem=80*1024**2).hex()


class Credentials(BaseModel):
    email: str = Field(min_length=3,max_length=254)
    password: str = Field(min_length=8,max_length=256)


class Registration(Credentials):
    alias: str = Field(min_length=1,max_length=100)


def issue_cookie(db, response, student_id):
    token = secrets.token_urlsafe(32)
    db.execute("INSERT INTO web_tokens VALUES (%s,%s,now()+interval '7 days')",(digest(token),student_id))
    response.set_cookie(COOKIE,token,httponly=True,samesite="strict",max_age=604800,
                        secure=os.getenv("REMI_HTTPS")=="1")


@router.post("/register")
def register(data: Registration, response: Response, db=DB):
    email = data.email.strip().lower()
    if not data.alias.strip() or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
        raise HTTPException(422,"Укажите псевдоним и адрес почты.")
    salt = secrets.token_bytes(16)
    stored = f"scrypt-v1${salt.hex()}${password_key(data.password,salt)}"
    row = db.execute("""INSERT INTO students(display_name,email,password_hash) VALUES (%s,%s,%s)
                        ON CONFLICT(email) DO NOTHING RETURNING student_id""",(data.alias.strip(),email,stored)).fetchone()
    if not row:
        raise HTTPException(409,"Этот адрес уже используется.")
    issue_cookie(db,response,row["student_id"])
    return {"alias": data.alias.strip()}


@router.post("/login")
def login(data: Credentials, response: Response, db=DB):
    row = db.execute("SELECT student_id,password_hash FROM students WHERE email=%s",
                     (data.email.strip().lower(),)).fetchone()
    parts = (row["password_hash"] or "").split("$") if row else []
    known = len(parts)==3 and parts[0]=="scrypt-v1"
    candidate = password_key(data.password,bytes.fromhex(parts[1]) if known else bytes(16))
    if not known or not hmac.compare_digest(candidate,parts[2]):
        raise HTTPException(401,"Проверьте почту и пароль.")
    issue_cookie(db,response,row["student_id"])
    return {"ok": True}


@router.get("/me")
def me(person=Depends(owner)):
    return {"alias":person["display_name"],"moderator":bool(person["moderator_id"])}


@router.post("/logout")
def logout(request: Request,response: Response,db=DB):
    db.execute("DELETE FROM web_tokens WHERE digest=%s",(digest(request.cookies.get(COOKIE,"")),))
    response.delete_cookie(COOKIE)
    return {"ok": True}

