from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

APP_VERSION = "2.0.0-mvp"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/batman-v2.db")
JWT_SECRET = os.getenv("JWT_SECRET", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "8"))

if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 characters")
if len(ADMIN_PASSWORD) < 14:
    raise RuntimeError("ADMIN_PASSWORD must contain at least 14 characters")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Node(Base):
    __tablename__ = "nodes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    agent_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    protocol: Mapped[str] = mapped_column(String(20))
    quota_gb: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    provisioning_status: Mapped[str] = mapped_column(String(30), default="not_connected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(100))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

def now() -> datetime:
    return datetime.now(timezone.utc)

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()

def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_s, digest_s = encoded.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_s.encode())
        expected = base64.urlsafe_b64decode(digest_s.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def issue_token(subject: str) -> str:
    header = b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",",":")).encode())
    payload = b64(json.dumps({"sub":subject,"iat":int(now().timestamp()),"exp":int((now()+timedelta(hours=TOKEN_TTL_HOURS)).timestamp())}, separators=(",",":")).encode())
    signing = f"{header}.{payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64(signature)}"

def verify_token(token: str) -> str:
    try:
        header, payload, signature = token.split(".")
        signing = f"{header}.{payload}".encode()
        expected = hmac.new(JWT_SECRET.encode(), signing, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))):
            raise ValueError("signature")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) < int(now().timestamp()):
            raise ValueError("expired")
        return str(data["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="توکن نامعتبر یا منقضی شده است")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

bearer = HTTPBearer(auto_error=False)

def current_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> Admin:
    if credentials is None:
        raise HTTPException(status_code=401, detail="ابتدا وارد شوید")
    username = verify_token(credentials.credentials)
    admin = db.scalar(select(Admin).where(Admin.username == username))
    if not admin:
        raise HTTPException(status_code=401, detail="حساب مدیر یافت نشد")
    return admin

class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)

class NodeInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=3, max_length=255)

class CustomerInput(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_.-]{3,64}$")
    protocol: Literal["openvpn", "vless", "vmess", "trojan", "wireguard"]
    quota_gb: int = Field(ge=1, le=100000)
    expires_at: datetime
    node_id: int | None = None

app = FastAPI(title="Batman VPN Panel API", version=APP_VERSION, docs_url="/api/docs", redoc_url=None)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        admin = db.scalar(select(Admin).where(Admin.username == ADMIN_USERNAME))
        if admin is None:
            db.add(Admin(username=ADMIN_USERNAME, password_hash=hash_password(ADMIN_PASSWORD)))
            db.commit()

@app.get("/api/health")
def health():
    return {"ok": True, "version": APP_VERSION, "mode": "control-plane-mvp"}

@app.post("/api/auth/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    admin = db.scalar(select(Admin).where(Admin.username == data.username))
    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    return {"access_token": issue_token(admin.username), "token_type":"bearer", "expires_in":TOKEN_TTL_HOURS*3600}

@app.get("/api/auth/me")
def me(admin: Admin = Depends(current_admin)):
    return {"username": admin.username, "role":"owner"}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    customers = db.scalars(select(Customer)).all()
    nodes = db.scalars(select(Node)).all()
    return {
        "customers_total": len(customers),
        "customers_active": sum(1 for c in customers if c.status == "active"),
        "customers_pending": sum(1 for c in customers if c.status == "pending"),
        "nodes_total": len(nodes),
        "nodes_online": sum(1 for n in nodes if n.status == "online"),
        "protocols": ["openvpn","vless","vmess","trojan","wireguard"],
        "live_provisioning": False
    }

@app.get("/api/nodes")
def list_nodes(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    return [{"id":n.id,"name":n.name,"address":n.address,"status":n.status,"last_seen":n.last_seen} for n in db.scalars(select(Node).order_by(Node.id.desc())).all()]

@app.post("/api/nodes", status_code=201)
def create_node(data: NodeInput, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    raw_token = secrets.token_urlsafe(40)
    node = Node(name=data.name, address=data.address, agent_token_hash=hashlib.sha256(raw_token.encode()).hexdigest())
    db.add(node)
    db.flush()
    db.add(AuditEvent(actor=admin.username, action="node.create", target=str(node.id), details=data.name))
    db.commit()
    return {"id":node.id,"name":node.name,"agent_token":raw_token,"warning":"این توکن فقط همین یک‌بار نمایش داده می‌شود. Agent هنوز در این نسخه عملیات پروتکل را اجرا نمی‌کند."}

@app.post("/api/agent/heartbeat")
def agent_heartbeat(x_agent_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not x_agent_token:
        raise HTTPException(status_code=401, detail="Agent token required")
    token_hash = hashlib.sha256(x_agent_token.encode()).hexdigest()
    node = db.scalar(select(Node).where(Node.agent_token_hash == token_hash))
    if not node:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    node.status = "online"
    node.last_seen = now()
    db.commit()
    return {"ok":True,"node_id":node.id,"capabilities":[],"message":"heartbeat only; protocol execution is not enabled"}

@app.get("/api/customers")
def list_customers(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    return [{"id":c.id,"username":c.username,"protocol":c.protocol,"quota_gb":c.quota_gb,"expires_at":c.expires_at,"status":c.status,"provisioning_status":c.provisioning_status,"node_id":c.node_id} for c in db.scalars(select(Customer).order_by(Customer.id.desc())).all()]

@app.post("/api/customers", status_code=201)
def create_customer(data: CustomerInput, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    if data.expires_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="expires_at باید timezone داشته باشد")
    if db.scalar(select(Customer).where(Customer.username == data.username)):
        raise HTTPException(status_code=409, detail="این نام کاربری قبلاً ثبت شده است")
    if data.node_id and not db.get(Node, data.node_id):
        raise HTTPException(status_code=404, detail="سرور انتخاب‌شده وجود ندارد")
    customer = Customer(username=data.username, protocol=data.protocol, quota_gb=data.quota_gb, expires_at=data.expires_at, node_id=data.node_id)
    db.add(customer)
    db.flush()
    db.add(AuditEvent(actor=admin.username, action="customer.create", target=str(customer.id), details=f"{data.username}:{data.protocol}"))
    db.commit()
    return {"id":customer.id,"username":customer.username,"status":customer.status,"provisioning_status":customer.provisioning_status,"notice":"رکورد مدیریتی ساخته شد؛ هنوز به سرویس VPN اعمال نشده است."}

@app.post("/api/customers/{customer_id}/suspend")
def suspend_customer(customer_id: int, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    customer.status = "suspended"
    db.add(AuditEvent(actor=admin.username, action="customer.suspend", target=str(customer.id)))
    db.commit()
    return {"ok":True,"status":customer.status,"notice":"تعلیق فقط در پنل ثبت شد و هنوز روی سرویس VPN اعمال نمی‌شود."}

@app.get("/api/protocols")
def protocols(admin: Admin = Depends(current_admin)):
    return [{"id":p,"name":p.upper(),"configured":False,"status":"planned"} for p in ("openvpn","vless","vmess","trojan","wireguard")]

@app.get("/")
def root():
    return {"name":"Batman VPN Panel API","version":APP_VERSION,"docs":"/api/docs"}
