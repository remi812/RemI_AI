import hashlib
import hmac
import os
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth_limits import admission
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
                        secure=os.getenv("REMI_HTTPS")=="1" or os.getenv("REMI_ENV")=="production")


@router.post("/register")
def register(data: Registration, response: Response, request: Request, db=DB):
    with admission(request.client.host,data.email.strip().lower()):
        return register_profile(data,response,db)


def register_profile(data,response,db):
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
def login(data: Credentials, response: Response, request: Request, db=DB):
    with admission(request.client.host,data.email.strip().lower()):
        return authenticate(data,response,db)


def authenticate(data,response,db):
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


class RecoveryRequest(BaseModel):
    email: str = Field(min_length=3,max_length=254)


class RecoveryFinish(BaseModel):
    token: str = Field(min_length=30,max_length=128)
    password: str = Field(min_length=8,max_length=256)


def send_recovery(address, token):
    import smtplib
    import ssl
    from email.message import EmailMessage
    host = os.getenv("REMI_SMTP_HOST")
    sender = os.getenv("REMI_SMTP_FROM")
    if not host or not sender:
        raise HTTPException(503,"Доставка писем пока не настроена. Обратитесь к организатору обучения.")
    letter = EmailMessage()
    letter["To"],letter["From"],letter["Subject"] = address,sender,"Восстановление RemI AI"
    letter.set_content(f"Введите одноразовый код на странице «Моё обучение» в течение 15 минут.\n\n{token}")
    try:
        with smtplib.SMTP_SSL(host,int(os.getenv("REMI_SMTP_PORT","465")),timeout=6,context=ssl.create_default_context()) as smtp:
            if os.getenv("REMI_SMTP_USER"):
                smtp.login(os.environ["REMI_SMTP_USER"],os.environ["REMI_SMTP_PASSWORD"])
            smtp.send_message(letter)
    except (OSError,smtplib.SMTPException,KeyError):
        raise HTTPException(503,"Письмо сейчас доставить не удалось. Попробуйте позже.") from None


@router.post("/recovery")
def recover(data:RecoveryRequest,request:Request,db=DB):
    email = data.email.strip().lower()
    with admission(request.client.host,email):
        if not os.getenv("REMI_SMTP_HOST") or not os.getenv("REMI_SMTP_FROM"):
            raise HTTPException(503,"Доставка писем пока не настроена. Обратитесь к организатору обучения.")
        row = db.execute("SELECT student_id FROM students WHERE email=%s AND password_hash IS NOT NULL FOR UPDATE",(email,)).fetchone()
        if row:
            token = secrets.token_urlsafe(32)
            db.execute("DELETE FROM profile_recovery WHERE student_id=%s OR expires_at<=now()",(row["student_id"],))
            db.execute("INSERT INTO profile_recovery VALUES (%s,%s,now()+interval '15 minutes')",(digest(token),row["student_id"]))
            send_recovery(email,token)
    return {"message":"Если профиль зарегистрирован, код придёт на его почту."}


@router.post("/recovery/finish")
def finish_recovery(data:RecoveryFinish,request:Request,db=DB):
    with admission(request.client.host,digest(data.token).hex()):
        row = db.execute("DELETE FROM profile_recovery WHERE digest=%s AND expires_at>now() RETURNING student_id",
                         (digest(data.token),)).fetchone()
        if not row:
            raise HTTPException(400,"Код недействителен или истёк.")
        salt = secrets.token_bytes(16)
        stored = f"scrypt-v1${salt.hex()}${password_key(data.password,salt)}"
        db.execute("UPDATE students SET password_hash=%s WHERE student_id=%s",(stored,row["student_id"]))
        db.execute("DELETE FROM web_tokens WHERE student_id=%s",(row["student_id"],))
    return {"message":"Пароль обновлён. Войдите с новым паролем."}


@router.get("/routes")
def routes(person=Depends(owner),db=DB):
    from app.catalog_routes import PILOTS
    rows = db.execute("""SELECT pilot_slug,max(started_at) AS last_seen FROM diagnostic_sessions
        WHERE student_id=%s AND pilot_slug IS NOT NULL GROUP BY pilot_slug ORDER BY last_seen DESC""",(person["student_id"],))
    return [{"slug":r["pilot_slug"],"title":PILOTS[r["pilot_slug"]]["topic"]} for r in rows if r["pilot_slug"] in PILOTS]


@router.get("/support")
def support():
    return {"email":os.getenv("REMI_SUPPORT_EMAIL") or None,
            "data_notice":os.getenv("REMI_DATA_NOTICE") or None}
