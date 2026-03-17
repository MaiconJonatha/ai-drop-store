"""
Dual Database: PostgreSQL + SQLite
- PostgreSQL: primary (cloud-ready)
- SQLite: backup/fallback (local)
Both are kept in sync.
"""
import os
import aiosqlite
import asyncpg
from pathlib import Path

# Config
SQLITE_PATH = Path(__file__).parent.parent / "store.db"
PG_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/ai_dropstore")
PG_USER = os.environ.get("PGUSER", os.environ.get("USER", "postgres"))

# Connection pools
pg_pool = None

async def init_pg():
    """Initialize PostgreSQL"""
    global pg_pool
    try:
        pg_pool = await asyncpg.create_pool(
            database="ai_dropstore",
            user=PG_USER,
            host="localhost",
            min_size=2, max_size=10
        )
        async with pg_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    brand TEXT DEFAULT '',
                    description TEXT,
                    price REAL NOT NULL,
                    old_price REAL,
                    discount INTEGER DEFAULT 0,
                    margin REAL DEFAULT 0,
                    supplier_price REAL NOT NULL,
                    image TEXT,
                    sold INTEGER DEFAULT 0,
                    rating REAL DEFAULT 4.5,
                    reviews_count INTEGER DEFAULT 0,
                    stock INTEGER DEFAULT 50,
                    shipping_days INTEGER DEFAULT 7,
                    created_by TEXT DEFAULT 'Luna',
                    description_by TEXT DEFAULT 'Aria',
                    price_by TEXT DEFAULT 'Zara',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    product_id TEXT REFERENCES products(id),
                    product_name TEXT,
                    qty INTEGER DEFAULT 1,
                    total REAL,
                    profit REAL,
                    status TEXT DEFAULT 'Processando',
                    customer TEXT,
                    handled_by TEXT DEFAULT 'Vega',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    product_id TEXT REFERENCES products(id),
                    customer TEXT,
                    rating REAL,
                    comment TEXT,
                    ai_generated BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_message TEXT,
                    ai_response TEXT,
                    ai_name TEXT DEFAULT 'Nova',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_activity (
                    id SERIAL PRIMARY KEY,
                    ai_name TEXT,
                    action TEXT,
                    detail TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS store_stats (
                    key TEXT PRIMARY KEY,
                    value REAL DEFAULT 0
                )
            """)
            for key in ['total_revenue', 'orders_count', 'visitors', 'ai_decisions', 'products_curated']:
                await conn.execute(
                    "INSERT INTO store_stats (key, value) VALUES ($1, 0) ON CONFLICT (key) DO NOTHING", key)
        print("[DB] PostgreSQL connected ✓")
        return True
    except Exception as e:
        print(f"[DB] PostgreSQL failed: {e}")
        pg_pool = None
        return False

async def init_sqlite():
    """Initialize SQLite"""
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                brand TEXT DEFAULT '', description TEXT, price REAL NOT NULL,
                old_price REAL, discount INTEGER DEFAULT 0, margin REAL DEFAULT 0,
                supplier_price REAL NOT NULL, image TEXT, sold INTEGER DEFAULT 0,
                rating REAL DEFAULT 4.5, reviews_count INTEGER DEFAULT 0,
                stock INTEGER DEFAULT 50, shipping_days INTEGER DEFAULT 7,
                created_by TEXT DEFAULT 'Luna', description_by TEXT DEFAULT 'Aria',
                price_by TEXT DEFAULT 'Zara', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, product_id TEXT, product_name TEXT,
                qty INTEGER DEFAULT 1, total REAL, profit REAL,
                status TEXT DEFAULT 'Processando', customer TEXT,
                handled_by TEXT DEFAULT 'Vega', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ai_name TEXT,
                action TEXT, detail TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_message TEXT,
                ai_response TEXT, ai_name TEXT DEFAULT 'Nova',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS store_stats (
                key TEXT PRIMARY KEY, value REAL DEFAULT 0
            )
        """)
        for key in ['total_revenue', 'orders_count', 'visitors', 'ai_decisions', 'products_curated']:
            await db.execute("INSERT OR IGNORE INTO store_stats (key, value) VALUES (?, 0)", (key,))
        await db.commit()
    print("[DB] SQLite connected ✓")

async def init_db():
    """Init both databases"""
    pg_ok = await init_pg()
    await init_sqlite()
    return pg_ok

def has_pg():
    return pg_pool is not None

# ─── DUAL WRITE: Write to both PG and SQLite ───

async def insert_product(product: dict):
    cols = ("id", "name", "category", "brand", "description", "price", "old_price",
            "discount", "margin", "supplier_price", "image", "sold", "rating",
            "reviews_count", "stock", "shipping_days", "created_by", "description_by", "price_by")
    vals = tuple(product.get(c, "") for c in cols)
    
    # SQLite
    placeholders_sq = ",".join(["?"] * len(cols))
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(f"INSERT OR REPLACE INTO products ({','.join(cols)}) VALUES ({placeholders_sq})", vals)
        await db.commit()
    
    # PostgreSQL
    if pg_pool:
        try:
            placeholders_pg = ",".join([f"${i+1}" for i in range(len(cols))])
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    f"INSERT INTO products ({','.join(cols)}) VALUES ({placeholders_pg}) ON CONFLICT (id) DO UPDATE SET " +
                    ",".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "id"),
                    *vals)
        except Exception as e:
            print(f"[PG] insert_product error: {e}")

async def update_product(product_id: str, **kwargs):
    # SQLite
    async with aiosqlite.connect(SQLITE_PATH) as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        await db.execute(f"UPDATE products SET {sets} WHERE id = ?", list(kwargs.values()) + [product_id])
        await db.commit()
    
    # PostgreSQL
    if pg_pool:
        try:
            sets = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(kwargs))
            async with pg_pool.acquire() as conn:
                await conn.execute(f"UPDATE products SET {sets} WHERE id = ${len(kwargs)+1}",
                                  *kwargs.values(), product_id)
        except Exception as e:
            print(f"[PG] update_product error: {e}")

async def insert_order(order: dict):
    cols = ("id", "product_id", "product_name", "qty", "total", "profit", "status", "customer", "handled_by")
    vals = (order["id"], order["product_id"], order["product"], order["qty"],
            order["total"], order["profit"], order["status"], order["customer"], order["handled_by"])
    
    # SQLite
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(f"INSERT INTO orders ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})", vals)
        await db.commit()
    
    # PostgreSQL
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    f"INSERT INTO orders ({','.join(cols)}) VALUES ({','.join(f'${i+1}' for i in range(len(cols)))})",
                    *vals)
        except Exception as e:
            print(f"[PG] insert_order error: {e}")

async def log_activity(ai_name: str, action: str, detail: str):
    detail = detail[:200]
    # SQLite
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute("INSERT INTO ai_activity (ai_name, action, detail) VALUES (?,?,?)",
                        (ai_name, action, detail))
        await db.commit()
    # PostgreSQL
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute("INSERT INTO ai_activity (ai_name, action, detail) VALUES ($1,$2,$3)",
                                  ai_name, action, detail)
        except Exception:
            pass
    await inc_stat("ai_decisions")

async def insert_chat(user_msg: str, ai_response: str, ai_name: str = "Nova"):
    # SQLite
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute("INSERT INTO chat_history (user_message, ai_response, ai_name) VALUES (?,?,?)",
                        (user_msg, ai_response, ai_name))
        await db.commit()
    # PostgreSQL
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute("INSERT INTO chat_history (user_message, ai_response, ai_name) VALUES ($1,$2,$3)",
                                  user_msg, ai_response, ai_name)
        except Exception:
            pass

async def inc_stat(key: str, amount: float = 1):
    # SQLite
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute("UPDATE store_stats SET value = value + ? WHERE key = ?", (amount, key))
        await db.commit()
    # PostgreSQL
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute("UPDATE store_stats SET value = value + $1 WHERE key = $2", amount, key)
        except Exception:
            pass

# ─── READ: Prefer PostgreSQL, fallback to SQLite ───

async def get_all_products(category=None, search=None, sort=None) -> list:
    """Read products - try PG first, fallback SQLite"""
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                query = "SELECT * FROM products WHERE TRUE"
                params = []
                idx = 1
                if category:
                    query += f" AND category = ${idx}"; params.append(category); idx += 1
                if search:
                    query += f" AND (name ILIKE ${idx} OR description ILIKE ${idx+1})"
                    params.extend([f"%{search}%", f"%{search}%"]); idx += 2
                order = {"price_asc": "price ASC", "price_desc": "price DESC",
                         "popular": "sold DESC", "rating": "rating DESC",
                         "discount": "discount DESC"}.get(sort, "sold DESC")
                query += f" ORDER BY {order}"
                rows = await conn.fetch(query, *params)
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[PG] get_all_products fallback to SQLite: {e}")
    
    # SQLite fallback
    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"; params.append(category)
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"; params.extend([f"%{search}%", f"%{search}%"])
        order = {"price_asc": "price ASC", "price_desc": "price DESC",
                 "popular": "sold DESC", "rating": "rating DESC",
                 "discount": "discount DESC"}.get(sort, "sold DESC")
        query += f" ORDER BY {order}"
        cursor = await db.execute(query, params)
        return [dict(r) for r in await cursor.fetchall()]

async def get_product(product_id: str) -> dict:
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
                return dict(row) if row else None
        except Exception:
            pass
    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_orders(limit=20) -> list:
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM orders ORDER BY created_at DESC LIMIT $1", limit)
                return [dict(r) for r in rows]
        except Exception:
            pass
    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in await cursor.fetchall()]

async def count_orders() -> int:
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                return await conn.fetchval("SELECT COUNT(*) FROM orders")
        except Exception:
            pass
    async with aiosqlite.connect(SQLITE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM orders")
        return (await cursor.fetchone())[0]

async def get_activity(limit=30) -> list:
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM ai_activity ORDER BY created_at DESC LIMIT $1", limit)
                return [dict(r) for r in rows]
        except Exception:
            pass
    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM ai_activity ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in await cursor.fetchall()]

async def get_all_stats() -> dict:
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                rows = await conn.fetch("SELECT key, value FROM store_stats")
                return {r["key"]: r["value"] for r in rows}
        except Exception:
            pass
    async with aiosqlite.connect(SQLITE_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM store_stats")
        return {r[0]: r[1] for r in await cursor.fetchall()}

async def product_count() -> int:
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                return await conn.fetchval("SELECT COUNT(*) FROM products")
        except Exception:
            pass
    async with aiosqlite.connect(SQLITE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        return (await cursor.fetchone())[0]

async def db_status() -> dict:
    """Return status of both databases"""
    status = {"sqlite": "connected", "sqlite_path": str(SQLITE_PATH)}
    if pg_pool:
        try:
            async with pg_pool.acquire() as conn:
                ver = await conn.fetchval("SELECT version()")
                status["postgresql"] = "connected"
                status["pg_version"] = ver.split(",")[0] if ver else "unknown"
        except Exception:
            status["postgresql"] = "error"
    else:
        status["postgresql"] = "not configured"
    return status
