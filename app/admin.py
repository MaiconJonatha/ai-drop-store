"""
Admin Panel - Complete Store Management
- Dashboard with KPIs
- Product CRUD (add/edit/remove)
- Order management (update status, tracking)
- Coupon management
- Review moderation
- AI agent control
- Export reports (CSV)

Admin credentials: admin@aidropstore.com / admin2026
"""

import hashlib
import csv
import io
from datetime import datetime
from typing import Optional

# Admin credentials (hashed)
ADMIN_USERS = {
    "admin@aidropstore.com": {
        "password_hash": hashlib.sha256("admin2026".encode()).hexdigest(),
        "name": "Admin",
        "role": "superadmin",
    }
}

ADMIN_SESSIONS = {}  # token -> {email, name, role, created_at}


def admin_login(email: str, password: str) -> dict:
    admin = ADMIN_USERS.get(email)
    if not admin:
        return {"success": False, "error": "Admin não encontrado"}
    
    if hashlib.sha256(password.encode()).hexdigest() != admin["password_hash"]:
        return {"success": False, "error": "Senha incorreta"}
    
    token = hashlib.sha256(f"{email}{datetime.now()}".encode()).hexdigest()
    ADMIN_SESSIONS[token] = {
        "email": email,
        "name": admin["name"],
        "role": admin["role"],
        "created_at": datetime.now().isoformat(),
    }
    return {"success": True, "token": token, "name": admin["name"]}


def verify_admin(token: str) -> Optional[dict]:
    return ADMIN_SESSIONS.get(token)


def admin_logout(token: str):
    ADMIN_SESSIONS.pop(token, None)


def export_orders_csv(orders: list) -> str:
    """Export orders to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Produto", "Qtd", "Total", "Lucro", "Status", "Cliente", "Data"])
    for o in orders:
        writer.writerow([
            o.get("id", ""), o.get("product", o.get("product_name", "")),
            o.get("qty", 0), o.get("total", 0), o.get("profit", 0),
            o.get("status", ""), o.get("customer", ""),
            o.get("created_at", ""),
        ])
    return output.getvalue()


def export_products_csv(products: list) -> str:
    """Export products to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nome", "Categoria", "Marca", "Preço", "Preço Antigo", "Desconto", "Margem", "Estoque", "Vendidos", "Rating", "Fornecedor"])
    for p in products:
        writer.writerow([
            p.get("id", ""), p["name"], p.get("category", ""), p.get("brand", ""),
            p.get("price", 0), p.get("old_price", 0), p.get("discount", 0),
            p.get("margin", 0), p.get("stock", 0), p.get("sold", 0),
            p.get("rating", 0), p.get("supplier", ""),
        ])
    return output.getvalue()
