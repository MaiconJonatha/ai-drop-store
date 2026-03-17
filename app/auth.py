"""Customer Accounts & Auth for AI Drop Store"""
import os
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

SECRET_KEY = os.environ.get("SECRET_KEY", "ai-drop-store-secret-2026-nike-anthropic")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SQLITE_PATH = Path(__file__).parent.parent / "store.db"

async def init_auth_db():
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                phone TEXT DEFAULT '',
                address TEXT DEFAULT '',
                city TEXT DEFAULT '',
                state TEXT DEFAULT '',
                cep TEXT DEFAULT '',
                total_orders INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS customer_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                order_id TEXT,
                product_name TEXT,
                qty INTEGER,
                total REAL,
                status TEXT DEFAULT 'Processando',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                product_id TEXT,
                product_name TEXT,
                qty INTEGER DEFAULT 1,
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        await db.commit()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(customer_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": str(customer_id), "email": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"id": int(payload["sub"]), "email": payload["email"]}
    except Exception:
        return None

async def register_customer(name: str, email: str, password: str) -> dict:
    async with aiosqlite.connect(SQLITE_PATH) as db:
        existing = await db.execute("SELECT id FROM customers WHERE email = ?", (email,))
        if await existing.fetchone():
            return {"error": "Email já cadastrado"}
        cursor = await db.execute(
            "INSERT INTO customers (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, hash_password(password))
        )
        await db.commit()
        cid = cursor.lastrowid
        token = create_token(cid, email)
        return {"success": True, "token": token, "customer_id": cid, "name": name}

async def login_customer(email: str, password: str) -> dict:
    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM customers WHERE email = ?", (email,))
        customer = await cursor.fetchone()
        if not customer or not verify_password(password, customer["password_hash"]):
            return {"error": "Email ou senha incorretos"}
        token = create_token(customer["id"], email)
        return {"success": True, "token": token, "customer_id": customer["id"], "name": customer["name"]}

async def get_customer(customer_id: int) -> dict:
    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, name, email, phone, address, city, state, cep, total_orders, total_spent, created_at FROM customers WHERE id = ?", (customer_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_customer_orders(customer_id: int) -> list:
    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM customer_orders WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
        return [dict(r) for r in await cursor.fetchall()]

async def save_customer_order(customer_id: int, order: dict):
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(
            "INSERT INTO customer_orders (customer_id, order_id, product_name, qty, total, status) VALUES (?,?,?,?,?,?)",
            (customer_id, order["id"], order["product"], order["qty"], order["total"], order["status"])
        )
        await db.execute("UPDATE customers SET total_orders = total_orders + 1, total_spent = total_spent + ? WHERE id = ?",
                        (order["total"], customer_id))
        await db.commit()

async def update_customer_profile(customer_id: int, **kwargs):
    async with aiosqlite.connect(SQLITE_PATH) as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        await db.execute(f"UPDATE customers SET {sets} WHERE id = ?", list(kwargs.values()) + [customer_id])
        await db.commit()

async def customer_count() -> int:
    async with aiosqlite.connect(SQLITE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM customers")
        return (await cursor.fetchone())[0]
