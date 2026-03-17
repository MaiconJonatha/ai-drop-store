"""
Shopping Cart + Coupons + Checkout System
- Cart stored in memory (per session/token)
- Coupon system with validation
- Checkout with address and shipping
- Frete calculation by region
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional

# In-memory carts: {session_id: {items: [], updated_at}}
CARTS = {}

# Coupon system
COUPONS = {
    "PRIMEIRACOMPRA": {"type": "percent", "value": 10, "min_order": 0, "max_uses": 9999, "used": 0, "active": True, "description": "10% OFF primeira compra"},
    "VOLTEI": {"type": "percent", "value": 5, "min_order": 0, "max_uses": 9999, "used": 0, "active": True, "description": "5% OFF para quem voltou"},
    "NIKE20": {"type": "percent", "value": 20, "min_order": 200, "max_uses": 100, "used": 0, "active": True, "description": "20% OFF em Nike (mín R$200)"},
    "FRETEGRATIS": {"type": "free_shipping", "value": 0, "min_order": 99, "max_uses": 500, "used": 0, "active": True, "description": "Frete grátis acima de R$99"},
    "FLASH50": {"type": "fixed", "value": 50, "min_order": 300, "max_uses": 50, "used": 0, "active": True, "description": "R$50 OFF (mín R$300)"},
    "AI10": {"type": "percent", "value": 10, "min_order": 50, "max_uses": 200, "used": 0, "active": True, "description": "10% OFF produtos de IA"},
    "PIX5": {"type": "percent", "value": 5, "min_order": 0, "max_uses": 9999, "used": 0, "active": True, "description": "5% OFF pagamento PIX"},
}

# Flash Sales
FLASH_SALES = []

# Shipping rates by state/region
SHIPPING_RATES = {
    "SP": {"name": "São Paulo", "standard": 15.90, "express": 29.90, "days_std": 3, "days_exp": 1},
    "RJ": {"name": "Rio de Janeiro", "standard": 18.90, "express": 34.90, "days_std": 4, "days_exp": 2},
    "MG": {"name": "Minas Gerais", "standard": 19.90, "express": 35.90, "days_std": 5, "days_exp": 2},
    "RS": {"name": "Rio Grande do Sul", "standard": 24.90, "express": 42.90, "days_std": 7, "days_exp": 3},
    "PR": {"name": "Paraná", "standard": 21.90, "express": 38.90, "days_std": 5, "days_exp": 2},
    "SC": {"name": "Santa Catarina", "standard": 22.90, "express": 39.90, "days_std": 6, "days_exp": 3},
    "BA": {"name": "Bahia", "standard": 25.90, "express": 44.90, "days_std": 7, "days_exp": 3},
    "PE": {"name": "Pernambuco", "standard": 27.90, "express": 47.90, "days_std": 8, "days_exp": 4},
    "CE": {"name": "Ceará", "standard": 28.90, "express": 48.90, "days_std": 8, "days_exp": 4},
    "GO": {"name": "Goiás", "standard": 22.90, "express": 39.90, "days_std": 6, "days_exp": 3},
    "DF": {"name": "Distrito Federal", "standard": 21.90, "express": 37.90, "days_std": 5, "days_exp": 2},
    "PA": {"name": "Pará", "standard": 32.90, "express": 55.90, "days_std": 10, "days_exp": 5},
    "AM": {"name": "Amazonas", "standard": 39.90, "express": 65.90, "days_std": 12, "days_exp": 6},
    "DEFAULT": {"name": "Outros", "standard": 29.90, "express": 49.90, "days_std": 10, "days_exp": 5},
}

# CEP to state mapping (first 2 digits)
CEP_STATES = {
    "01": "SP", "02": "SP", "03": "SP", "04": "SP", "05": "SP", "06": "SP", "07": "SP", "08": "SP", "09": "SP",
    "11": "SP", "12": "SP", "13": "SP", "14": "SP", "15": "SP", "16": "SP", "17": "SP", "18": "SP", "19": "SP",
    "20": "RJ", "21": "RJ", "22": "RJ", "23": "RJ", "24": "RJ", "25": "RJ", "26": "RJ", "27": "RJ", "28": "RJ",
    "30": "MG", "31": "MG", "32": "MG", "33": "MG", "34": "MG", "35": "MG", "36": "MG", "37": "MG", "38": "MG", "39": "MG",
    "40": "BA", "41": "BA", "42": "BA", "43": "BA", "44": "BA", "45": "BA", "46": "BA", "47": "BA", "48": "BA",
    "49": "SE",
    "50": "PE", "51": "PE", "52": "PE", "53": "PE", "54": "PE", "55": "PE", "56": "PE",
    "57": "AL", "58": "PB",
    "59": "RN", "60": "CE", "61": "CE", "62": "CE", "63": "CE",
    "64": "PI", "65": "MA", "66": "PA", "67": "PA", "68": "AP", "69": "AM",
    "70": "DF", "71": "DF", "72": "GO", "73": "GO", "74": "GO", "75": "GO", "76": "TO",
    "77": "TO", "78": "MT", "79": "MS",
    "80": "PR", "81": "PR", "82": "PR", "83": "PR", "84": "PR", "85": "PR", "86": "PR", "87": "PR",
    "88": "SC", "89": "SC",
    "90": "RS", "91": "RS", "92": "RS", "93": "RS", "94": "RS", "95": "RS", "96": "RS", "97": "RS", "98": "RS", "99": "RS",
}

# Completed orders
CHECKOUT_ORDERS = []


def get_state_from_cep(cep: str) -> str:
    cep_clean = cep.replace("-", "").replace(".", "").strip()
    if len(cep_clean) >= 2:
        return CEP_STATES.get(cep_clean[:2], "DEFAULT")
    return "DEFAULT"


def calc_shipping(cep: str, cart_total: float) -> dict:
    state = get_state_from_cep(cep)
    rates = SHIPPING_RATES.get(state, SHIPPING_RATES["DEFAULT"])
    
    free_shipping = cart_total >= 199
    
    return {
        "state": state,
        "state_name": rates["name"],
        "standard": {
            "price": 0 if free_shipping else rates["standard"],
            "days": rates["days_std"],
            "name": "Padrão",
            "free": free_shipping,
        },
        "express": {
            "price": rates["express"] * (0.5 if free_shipping else 1),
            "days": rates["days_exp"],
            "name": "Expresso",
            "free": False,
        },
        "free_threshold": 199,
        "cart_total": cart_total,
    }


def get_cart(session_id: str) -> dict:
    if session_id not in CARTS:
        CARTS[session_id] = {"items": [], "coupon": None, "updated_at": datetime.now().isoformat()}
    return CARTS[session_id]


def add_to_cart(session_id: str, product: dict, qty: int = 1) -> dict:
    cart = get_cart(session_id)
    
    # Check if product already in cart
    for item in cart["items"]:
        if item["product_id"] == product["id"]:
            item["qty"] += qty
            item["subtotal"] = round(item["qty"] * item["price"], 2)
            cart["updated_at"] = datetime.now().isoformat()
            return cart
    
    cart["items"].append({
        "product_id": product["id"],
        "name": product["name"],
        "price": product["price"],
        "old_price": product.get("old_price", product["price"]),
        "image": product.get("image", ""),
        "qty": qty,
        "subtotal": round(product["price"] * qty, 2),
        "brand": product.get("brand", ""),
        "category": product.get("category", ""),
    })
    cart["updated_at"] = datetime.now().isoformat()
    return cart


def update_cart_qty(session_id: str, product_id: str, qty: int) -> dict:
    cart = get_cart(session_id)
    if qty <= 0:
        cart["items"] = [i for i in cart["items"] if i["product_id"] != product_id]
    else:
        for item in cart["items"]:
            if item["product_id"] == product_id:
                item["qty"] = qty
                item["subtotal"] = round(qty * item["price"], 2)
    cart["updated_at"] = datetime.now().isoformat()
    return cart


def remove_from_cart(session_id: str, product_id: str) -> dict:
    return update_cart_qty(session_id, product_id, 0)


def clear_cart(session_id: str):
    if session_id in CARTS:
        CARTS[session_id] = {"items": [], "coupon": None, "updated_at": datetime.now().isoformat()}


def apply_coupon(session_id: str, code: str) -> dict:
    cart = get_cart(session_id)
    code = code.upper().strip()
    
    if code not in COUPONS:
        return {"success": False, "error": "Cupom inválido"}
    
    coupon = COUPONS[code]
    if not coupon["active"]:
        return {"success": False, "error": "Cupom expirado"}
    if coupon["used"] >= coupon["max_uses"]:
        return {"success": False, "error": "Cupom esgotado"}
    
    subtotal = sum(i["subtotal"] for i in cart["items"])
    if subtotal < coupon["min_order"]:
        return {"success": False, "error": f"Pedido mínimo: R${coupon['min_order']:.2f}"}
    
    cart["coupon"] = {"code": code, **coupon}
    return {"success": True, "coupon": coupon, "message": f"Cupom {code} aplicado! {coupon['description']}"}


def get_cart_totals(session_id: str, cep: str = "") -> dict:
    cart = get_cart(session_id)
    subtotal = sum(i["subtotal"] for i in cart["items"])
    discount = 0
    
    if cart.get("coupon"):
        c = cart["coupon"]
        if c["type"] == "percent":
            discount = round(subtotal * c["value"] / 100, 2)
        elif c["type"] == "fixed":
            discount = min(c["value"], subtotal)
    
    shipping = 0
    shipping_info = None
    if cep:
        shipping_info = calc_shipping(cep, subtotal)
        shipping = shipping_info["standard"]["price"]
        if cart.get("coupon") and cart["coupon"].get("type") == "free_shipping":
            shipping = 0
    
    total = max(0, subtotal - discount + shipping)
    
    return {
        "items_count": sum(i["qty"] for i in cart["items"]),
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "shipping": round(shipping, 2),
        "total": round(total, 2),
        "coupon": cart.get("coupon"),
        "shipping_info": shipping_info,
        "savings": round(sum(((i["old_price"] - i["price"]) * i["qty"]) for i in cart["items"]), 2),
    }


def create_flash_sale(product_id: str, product_name: str, discount_pct: int, duration_hours: int = 2):
    """Create a flash sale"""
    sale = {
        "id": hashlib.md5(f"{product_id}{datetime.now()}".encode()).hexdigest()[:8],
        "product_id": product_id,
        "product_name": product_name,
        "discount_pct": discount_pct,
        "starts_at": datetime.now().isoformat(),
        "ends_at": (datetime.now() + timedelta(hours=duration_hours)).isoformat(),
        "active": True,
    }
    FLASH_SALES.append(sale)
    return sale


def get_active_flash_sales() -> list:
    now = datetime.now()
    active = []
    for sale in FLASH_SALES:
        if sale["active"] and datetime.fromisoformat(sale["ends_at"]) > now:
            remaining = (datetime.fromisoformat(sale["ends_at"]) - now).total_seconds()
            sale["remaining_seconds"] = int(remaining)
            active.append(sale)
    return active


def get_cart_stats():
    total_carts = len(CARTS)
    active_carts = sum(1 for c in CARTS.values() if c["items"])
    total_items = sum(sum(i["qty"] for i in c["items"]) for c in CARTS.values())
    return {
        "total_carts": total_carts,
        "active_carts": active_carts,
        "total_items": total_items,
        "coupons_available": len([c for c in COUPONS.values() if c["active"]]),
        "flash_sales_active": len(get_active_flash_sales()),
        "checkout_orders": len(CHECKOUT_ORDERS),
    }
