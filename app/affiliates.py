"""
Affiliate Program
- Unique referral links per affiliate
- 5-10% commission on referred sales
- Affiliate dashboard with earnings
- Auto-payout tracking
"""

import hashlib
from datetime import datetime
import random
import string

AFFILIATES = {}  # {code: {name, email, commission_pct, total_earned, total_referred, clicks, created_at}}
REFERRAL_SALES = []  # [{affiliate_code, order_id, amount, commission, created_at}]


def generate_code(name: str) -> str:
    base = name.replace(" ", "").upper()[:4]
    rand = ''.join(random.choices(string.digits, k=4))
    return f"{base}{rand}"


def register_affiliate(name: str, email: str) -> dict:
    if any(a["email"] == email for a in AFFILIATES.values()):
        return {"success": False, "error": "Email already registered as affiliate"}
    
    code = generate_code(name)
    AFFILIATES[code] = {
        "name": name,
        "email": email,
        "code": code,
        "commission_pct": 8,  # 8% default commission
        "total_earned": 0,
        "total_referred": 0,
        "clicks": 0,
        "paid_out": 0,
        "created_at": datetime.now().isoformat(),
    }
    return {"success": True, "code": code, "affiliate": AFFILIATES[code]}


def track_click(code: str) -> bool:
    if code in AFFILIATES:
        AFFILIATES[code]["clicks"] += 1
        return True
    return False


def track_sale(code: str, order_id: str, amount: float) -> dict:
    if code not in AFFILIATES:
        return {"success": False, "error": "Invalid affiliate code"}
    
    aff = AFFILIATES[code]
    commission = round(amount * aff["commission_pct"] / 100, 2)
    
    sale = {
        "affiliate_code": code,
        "order_id": order_id,
        "amount": amount,
        "commission": commission,
        "created_at": datetime.now().isoformat(),
    }
    REFERRAL_SALES.append(sale)
    
    aff["total_earned"] += commission
    aff["total_referred"] += 1
    
    return {"success": True, "commission": commission, "sale": sale}


def get_affiliate(code: str) -> dict:
    return AFFILIATES.get(code)


def get_affiliate_sales(code: str) -> list:
    return [s for s in REFERRAL_SALES if s["affiliate_code"] == code]


def get_affiliate_stats() -> dict:
    return {
        "total_affiliates": len(AFFILIATES),
        "total_sales": len(REFERRAL_SALES),
        "total_commission": round(sum(s["commission"] for s in REFERRAL_SALES), 2),
        "total_revenue": round(sum(s["amount"] for s in REFERRAL_SALES), 2),
    }


# Pre-seed some affiliates for demo
def init_affiliates():
    demo_affiliates = [
        ("Tech Reviewer", "tech@example.com"),
        ("Fashion Blog", "fashion@example.com"),
        ("AI Enthusiast", "ai@example.com"),
    ]
    for name, email in demo_affiliates:
        result = register_affiliate(name, email)
        if result["success"]:
            code = result["code"]
            # Simulate some activity
            AFFILIATES[code]["clicks"] = random.randint(50, 500)
            AFFILIATES[code]["total_referred"] = random.randint(5, 30)
            AFFILIATES[code]["total_earned"] = round(random.uniform(100, 1500), 2)
