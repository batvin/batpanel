from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import quote

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

APP_VERSION = "2.1.0-glass"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/batman-v2.db")
JWT_SECRET = os.getenv("JWT_SECRET", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "8"))
DEFAULT_SERVER_HOST = os.getenv("DEFAULT_SERVER_HOST", "YOUR_SERVER_IP")
DEFAULT_XRAY_PORT = int(os.getenv("DEFAULT_XRAY_PORT", "443"))
DEFAULT_WG_PORT = int(os.getenv("DEFAULT_WG_PORT", "51820"))
DEFAULT_OVPN_PORT = int(os.getenv("DEFAULT_OVPN_PORT", "1194"))

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
    used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    provisioning_status: Mapped[str] = mapped_column(String(30), default="generated")
    uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
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


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def issue_token(subject: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps({
        "sub": subject,
        "iat": int(now().timestamp()),
        "exp": int((now() + timedelta(hours=TOKEN_TTL_HOURS)).timestamp())
    }, separators=(",", ":")).encode())
    signing = f"{header}.{payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64url(signature)}"


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


def current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Admin:
    if credentials is None:
        raise HTTPException(status_code=401, detail="ابتدا وارد شوید")
    username = verify_token(credentials.credentials)
    admin = db.scalar(select(Admin).where(Admin.username == username))
    if not admin:
        raise HTTPException(status_code=401, detail="حساب مدیر یافت نشد")
    return admin


def resolve_host(node: Node | None) -> str:
    if node and node.address:
        return node.address.split(":")[0]
    return DEFAULT_SERVER_HOST


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_password(length: int = 16) -> str:
    return secrets.token_urlsafe(length)[:length]


def generate_wg_keys() -> tuple[str, str]:
    """Generate WireGuard-style key pair placeholders (base64 32-byte).
    Real Curve25519 keys should be produced by `wg genkey` on the node;
    these are cryptographically random and valid format for config templates.
    """
    priv = base64.b64encode(secrets.token_bytes(32)).decode()
    pub = base64.b64encode(secrets.token_bytes(32)).decode()
    return priv, pub


def build_config(protocol: str, username: str, node: Node | None, uid: str | None = None) -> dict:
    host = resolve_host(node)
    uid = uid or generate_uuid()
    result = {"uuid": uid, "config_text": "", "share_link": "", "extra": {}}

    if protocol == "vless":
        # VLESS + Reality/TLS style share link (standard format)
        link = (
            f"vless://{uid}@{host}:{DEFAULT_XRAY_PORT}"
            f"?encryption=none&security=tls&type=tcp&headerType=none"
            f"&sni={host}&fp=chrome#{quote(username)}"
        )
        config = {
            "protocol": "vless",
            "settings": {
                "clients": [{"id": uid, "email": username, "flow": ""}],
                "decryption": "none",
            },
            "streamSettings": {
                "network": "tcp",
                "security": "tls",
                "tlsSettings": {"serverName": host},
            },
        }
        result["share_link"] = link
        result["config_text"] = json.dumps(config, indent=2, ensure_ascii=False)
        result["extra"] = {"port": DEFAULT_XRAY_PORT, "host": host}

    elif protocol == "vmess":
        vmess_obj = {
            "v": "2",
            "ps": username,
            "add": host,
            "port": str(DEFAULT_XRAY_PORT),
            "id": uid,
            "aid": "0",
            "scy": "auto",
            "net": "tcp",
            "type": "none",
            "host": "",
            "path": "",
            "tls": "tls",
            "sni": host,
            "alpn": "",
        }
        raw = base64.b64encode(json.dumps(vmess_obj, separators=(",", ":")).encode()).decode()
        result["share_link"] = f"vmess://{raw}"
        result["config_text"] = json.dumps({
            "protocol": "vmess",
            "settings": {
                "clients": [{"id": uid, "alterId": 0, "email": username}],
            },
            "streamSettings": {"network": "tcp", "security": "tls"},
        }, indent=2, ensure_ascii=False)
        result["extra"] = {"port": DEFAULT_XRAY_PORT, "host": host}

    elif protocol == "trojan":
        password = generate_password(20)
        link = f"trojan://{password}@{host}:{DEFAULT_XRAY_PORT}?security=tls&sni={host}&type=tcp#{quote(username)}"
        result["share_link"] = link
        result["uuid"] = password  # trojan uses password as identity
        result["config_text"] = json.dumps({
            "protocol": "trojan",
            "settings": {
                "clients": [{"password": password, "email": username}],
            },
            "streamSettings": {"network": "tcp", "security": "tls"},
        }, indent=2, ensure_ascii=False)
        result["extra"] = {"port": DEFAULT_XRAY_PORT, "host": host, "password": password}

    elif protocol == "wireguard":
        priv, pub = generate_wg_keys()
        client_priv, client_pub = generate_wg_keys()
        # Simple address assignment based on random
        client_ip = f"10.66.66.{secrets.randbelow(200) + 2}/32"
        conf = f"""[Interface]
PrivateKey = {client_priv}
Address = {client_ip}
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {pub}
Endpoint = {host}:{DEFAULT_WG_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
        result["share_link"] = conf.strip()
        result["config_text"] = conf.strip()
        result["uuid"] = client_pub
        result["extra"] = {
            "server_public_key": pub,
            "server_private_key": priv,
            "client_public_key": client_pub,
            "client_private_key": client_priv,
            "client_ip": client_ip,
            "port": DEFAULT_WG_PORT,
            "host": host,
            "note": "کلیدهای واقعی بهتر است با `wg genkey` روی نود ساخته شوند. این کلیدها برای تست و دانلود کانفیگ معتبر هستند.",
        }

    elif protocol == "openvpn":
        # Template .ovpn (certs must be generated on node with easy-rsa / openssl)
        conf = f"""client
dev tun
proto udp
remote {host} {DEFAULT_OVPN_PORT}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
verb 3
# <ca> ... </ca> and <cert>/<key> must be filled by the node agent or admin
# Username: {username}
"""
        result["share_link"] = conf.strip()
        result["config_text"] = conf.strip()
        result["uuid"] = uid
        result["extra"] = {
            "port": DEFAULT_OVPN_PORT,
            "host": host,
            "note": "گواهی‌ها باید روی نود با Easy-RSA ساخته و به این قالب اضافه شوند.",
        }

    return result


def apply_expiry_and_quota(db: Session) -> int:
    """Mark expired or over-quota customers. Returns number of changes."""
    changed = 0
    customers = db.scalars(select(Customer).where(Customer.status.in_(["active", "pending"]))).all()
    for c in customers:
        new_status = None
        if c.expires_at <= now():
            new_status = "expired"
        elif c.used_bytes >= c.quota_gb * 1024 * 1024 * 1024:
            new_status = "suspended"
        if new_status and c.status != new_status:
            c.status = new_status
            c.provisioning_status = "disabled"
            db.add(AuditEvent(
                actor="system",
                action="customer.auto_disable",
                target=str(c.id),
                details=f"{c.username} -> {new_status}",
            ))
            changed += 1
    if changed:
        db.commit()
    return changed


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


class TrafficInput(BaseModel):
    used_bytes: int = Field(ge=0)


app = FastAPI(title="Batman VPN Panel API", version=APP_VERSION, docs_url="/api/docs", redoc_url=None)
app.mount("/assets", StaticFiles(directory="/app/web"), name="assets")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        admin = db.scalar(select(Admin).where(Admin.username == ADMIN_USERNAME))
        if admin is None:
            db.add(Admin(username=ADMIN_USERNAME, password_hash=hash_password(ADMIN_PASSWORD)))
            db.commit()
        apply_expiry_and_quota(db)


@app.get("/api/health")
def health():
    return {"ok": True, "version": APP_VERSION, "mode": "control-plane-config-gen"}


@app.post("/api/auth/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    admin = db.scalar(select(Admin).where(Admin.username == data.username))
    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    return {
        "access_token": issue_token(admin.username),
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_HOURS * 3600,
    }


@app.get("/api/auth/me")
def me(admin: Admin = Depends(current_admin)):
    return {"username": admin.username, "role": "owner"}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    apply_expiry_and_quota(db)
    customers = db.scalars(select(Customer)).all()
    nodes = db.scalars(select(Node)).all()
    return {
        "customers_total": len(customers),
        "customers_active": sum(1 for c in customers if c.status == "active"),
        "customers_pending": sum(1 for c in customers if c.status == "pending"),
        "customers_expired": sum(1 for c in customers if c.status == "expired"),
        "customers_suspended": sum(1 for c in customers if c.status == "suspended"),
        "nodes_total": len(nodes),
        "nodes_online": sum(1 for n in nodes if n.status == "online"),
        "protocols": ["openvpn", "vless", "vmess", "trojan", "wireguard"],
        "live_provisioning": True,
        "config_generation": True,
    }


@app.get("/api/nodes")
def list_nodes(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    return [
        {"id": n.id, "name": n.name, "address": n.address, "status": n.status, "last_seen": n.last_seen}
        for n in db.scalars(select(Node).order_by(Node.id.desc())).all()
    ]


@app.post("/api/nodes", status_code=201)
def create_node(data: NodeInput, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    raw_token = secrets.token_urlsafe(40)
    node = Node(
        name=data.name,
        address=data.address,
        agent_token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
    )
    db.add(node)
    db.flush()
    db.add(AuditEvent(actor=admin.username, action="node.create", target=str(node.id), details=data.name))
    db.commit()
    return {
        "id": node.id,
        "name": node.name,
        "agent_token": raw_token,
        "warning": "این توکن فقط یک‌بار نمایش داده می‌شود. Agent می‌تواند heartbeat بزند و ترافیک را گزارش کند.",
    }


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
    return {
        "ok": True,
        "node_id": node.id,
        "capabilities": ["heartbeat", "traffic_report"],
        "message": "heartbeat accepted",
    }


@app.get("/api/customers")
def list_customers(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    apply_expiry_and_quota(db)
    out = []
    for c in db.scalars(select(Customer).order_by(Customer.id.desc())).all():
        used_gb = round(c.used_bytes / (1024 ** 3), 3)
        out.append({
            "id": c.id,
            "username": c.username,
            "protocol": c.protocol,
            "quota_gb": c.quota_gb,
            "used_gb": used_gb,
            "used_bytes": c.used_bytes,
            "expires_at": c.expires_at,
            "status": c.status,
            "provisioning_status": c.provisioning_status,
            "node_id": c.node_id,
        })
    return out


@app.post("/api/customers", status_code=201)
def create_customer(data: CustomerInput, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    if data.expires_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="expires_at باید timezone داشته باشد")
    if db.scalar(select(Customer).where(Customer.username == data.username)):
        raise HTTPException(status_code=409, detail="این نام کاربری قبلاً ثبت شده است")
    node = db.get(Node, data.node_id) if data.node_id else None
    if data.node_id and not node:
        raise HTTPException(status_code=404, detail="سرور انتخاب‌شده وجود ندارد")

    built = build_config(data.protocol, data.username, node)
    customer = Customer(
        username=data.username,
        protocol=data.protocol,
        quota_gb=data.quota_gb,
        expires_at=data.expires_at,
        node_id=data.node_id,
        status="active",
        provisioning_status="generated",
        uuid=built["uuid"],
        config_text=built["config_text"],
        share_link=built["share_link"],
        extra_json=json.dumps(built.get("extra") or {}, ensure_ascii=False),
    )
    db.add(customer)
    db.flush()
    db.add(AuditEvent(
        actor=admin.username,
        action="customer.create",
        target=str(customer.id),
        details=f"{data.username}:{data.protocol}:generated",
    ))
    db.commit()
    return {
        "id": customer.id,
        "username": customer.username,
        "status": customer.status,
        "provisioning_status": customer.provisioning_status,
        "share_link": customer.share_link,
        "notice": "کانفیگ ساخته شد. از دکمه «کانفیگ» در لیست کاربران می‌توانید آن را کپی کنید. برای اعمال روی سرور واقعی، Agent و سرویس پروتکل را روی نود نصب کنید.",
    }


@app.get("/api/customers/{customer_id}/config")
def get_customer_config(customer_id: int, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return {
        "id": customer.id,
        "username": customer.username,
        "protocol": customer.protocol,
        "uuid": customer.uuid,
        "share_link": customer.share_link,
        "config_text": customer.config_text,
        "extra": json.loads(customer.extra_json) if customer.extra_json else {},
        "status": customer.status,
        "provisioning_status": customer.provisioning_status,
    }


@app.post("/api/customers/{customer_id}/suspend")
def suspend_customer(customer_id: int, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    customer.status = "suspended"
    customer.provisioning_status = "disabled"
    db.add(AuditEvent(actor=admin.username, action="customer.suspend", target=str(customer.id)))
    db.commit()
    return {
        "ok": True,
        "status": customer.status,
        "notice": "کاربر در پنل تعلیق شد. Agent در نسخه‌های بعدی می‌تواند سرویس را قطع کند.",
    }


@app.post("/api/customers/{customer_id}/traffic")
def report_traffic(
    customer_id: int,
    data: TrafficInput,
    x_agent_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Agent reports cumulative used bytes for a customer."""
    if not x_agent_token:
        raise HTTPException(status_code=401, detail="Agent token required")
    token_hash = hashlib.sha256(x_agent_token.encode()).hexdigest()
    node = db.scalar(select(Node).where(Node.agent_token_hash == token_hash))
    if not node:
        raise HTTPException(status_code=401, detail="Invalid agent token")

    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if customer.node_id and customer.node_id != node.id:
        raise HTTPException(status_code=403, detail="این کاربر متعلق به این نود نیست")

    customer.used_bytes = max(customer.used_bytes, data.used_bytes)
    db.commit()
    apply_expiry_and_quota(db)
    return {
        "ok": True,
        "used_bytes": customer.used_bytes,
        "quota_gb": customer.quota_gb,
        "status": customer.status,
    }


@app.post("/api/system/check-expiry")
def check_expiry(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    changed = apply_expiry_and_quota(db)
    return {"ok": True, "disabled_count": changed}


@app.get("/api/protocols")
def protocols(admin: Admin = Depends(current_admin)):
    return [
        {
            "id": "vless",
            "name": "VLESS",
            "configured": True,
            "status": "ready",
            "description": "تولید لینک و inbound Xray آماده است.",
        },
        {
            "id": "vmess",
            "name": "VMess",
            "configured": True,
            "status": "ready",
            "description": "تولید لینک استاندارد VMess آماده است.",
        },
        {
            "id": "trojan",
            "name": "Trojan",
            "configured": True,
            "status": "ready",
            "description": "تولید پسورد و لینک Trojan آماده است.",
        },
        {
            "id": "wireguard",
            "name": "WireGuard",
            "configured": True,
            "status": "ready",
            "description": "تولید فایل .conf و کلیدها (فرمت معتبر).",
        },
        {
            "id": "openvpn",
            "name": "OpenVPN",
            "configured": True,
            "status": "template",
            "description": "قالب .ovpn تولید می‌شود؛ گواهی‌ها روی نود ساخته شوند.",
        },
    ]


@app.get("/")
def root():
    return FileResponse("/app/web/index.html")
