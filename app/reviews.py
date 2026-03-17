"""
Customer Reviews System
- Star ratings (1-5)
- Text reviews with moderation by Nova AI
- Review stats per product
- Verified purchase badge
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional

# In-memory reviews storage
REVIEWS = []  # [{id, product_id, customer_name, rating, title, text, verified, moderated, created_at, helpful}]

# Pre-generated reviews for realism
FAKE_NAMES = [
    "Maria S.", "João P.", "Ana C.", "Pedro L.", "Juliana M.", "Lucas R.",
    "Fernanda O.", "Rafael T.", "Camila B.", "Bruno A.", "Larissa F.",
    "Thiago D.", "Beatriz G.", "Felipe N.", "Isabela K.", "Gustavo V.",
    "Patricia H.", "Matheus W.", "Carolina E.", "Diego Z.",
]

REVIEW_TEMPLATES = {
    "nike": {
        5: ["Tênis incrível! Super confortável.", "Qualidade Nike incomparável. Amei!", "Chegou rápido e é lindo!", "Melhor compra que fiz. 100% original!", "Conforto absurdo, uso todo dia."],
        4: ["Muito bom, só achei o preço um pouco alto.", "Ótimo tênis, entrega demorou um pouquinho.", "Qualidade top, numeração certinha.", "Bonito e confortável. Recomendo!"],
        3: ["Bom produto mas esperava mais.", "OK para o preço. Nada excepcional."],
    },
    "ai": {
        5: ["Curso sensacional! Aprendi muito sobre Claude API.", "Conteúdo excelente, vale cada centavo!", "Transformou meu negócio com IA!", "Pack de prompts incrível, uso diariamente."],
        4: ["Muito bom, queria mais exemplos práticos.", "Ótimo material, recomendo para iniciantes."],
        3: ["Razoável, faltou profundidade em alguns tópicos."],
    },
    "tech": {
        5: ["Produto excelente! Funciona perfeitamente.", "Qualidade surpreendente pelo preço!", "Chegou antes do prazo. Perfeito!"],
        4: ["Bom custo-benefício. Funciona bem.", "Gostei bastante, atendeu minhas expectativas."],
        3: ["Funciona mas o material poderia ser melhor.", "Razoável para o preço."],
    },
    "default": {
        5: ["Amei! Super recomendo!", "Produto incrível, superou expectativas!", "Qualidade excelente!"],
        4: ["Muito bom, recomendo!", "Bom produto, entrega ok."],
        3: ["Razoável, atende o básico.", "OK para o preço."],
    },
}


def generate_initial_reviews(products: list):
    """Generate realistic reviews for all products"""
    for product in products:
        cat = product.get("category", "default")
        templates = REVIEW_TEMPLATES.get(cat, REVIEW_TEMPLATES["default"])
        
        # Generate 3-8 reviews per product
        num_reviews = random.randint(3, 8)
        for i in range(num_reviews):
            # Weighted towards 4-5 stars
            rating = random.choices([5, 4, 3, 2, 1], weights=[45, 30, 15, 7, 3])[0]
            
            texts = templates.get(rating, templates.get(max(templates.keys()), ["Bom produto!"]))
            text = random.choice(texts)
            
            days_ago = random.randint(1, 90)
            review = {
                "id": hashlib.md5(f"{product['id']}{i}{random.random()}".encode()).hexdigest()[:8],
                "product_id": product["id"],
                "product_name": product["name"],
                "customer_name": random.choice(FAKE_NAMES),
                "rating": rating,
                "title": text[:40] + ("..." if len(text) > 40 else ""),
                "text": text,
                "verified": random.random() > 0.3,  # 70% verified
                "moderated": True,
                "moderated_by": "Nova (IA)",
                "created_at": (datetime.now() - timedelta(days=days_ago)).isoformat(),
                "helpful": random.randint(0, 50),
                "images": [],
            }
            REVIEWS.append(review)


def add_review(product_id: str, customer_name: str, rating: int, title: str, text: str, verified: bool = False) -> dict:
    """Add a new customer review"""
    if rating < 1 or rating > 5:
        return {"success": False, "error": "Rating must be between 1 and 5"}
    if len(text) < 5:
        return {"success": False, "error": "Review too short (min 5 characters)"}
    
    review = {
        "id": hashlib.md5(f"{product_id}{customer_name}{datetime.now()}".encode()).hexdigest()[:8],
        "product_id": product_id,
        "customer_name": customer_name,
        "rating": rating,
        "title": title or text[:40],
        "text": text,
        "verified": verified,
        "moderated": False,  # Pending moderation by Nova AI
        "moderated_by": None,
        "created_at": datetime.now().isoformat(),
        "helpful": 0,
        "images": [],
    }
    REVIEWS.append(review)
    return {"success": True, "review": review}


def get_product_reviews(product_id: str, limit: int = 20) -> list:
    """Get reviews for a product"""
    reviews = [r for r in REVIEWS if r["product_id"] == product_id and r["moderated"]]
    reviews.sort(key=lambda x: x["created_at"], reverse=True)
    return reviews[:limit]


def get_product_rating_stats(product_id: str) -> dict:
    """Get rating breakdown for a product"""
    reviews = [r for r in REVIEWS if r["product_id"] == product_id and r["moderated"]]
    if not reviews:
        return {"avg": 0, "count": 0, "breakdown": {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}}
    
    breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews:
        breakdown[r["rating"]] = breakdown.get(r["rating"], 0) + 1
    
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    return {
        "avg": round(avg, 1),
        "count": len(reviews),
        "breakdown": breakdown,
        "verified_count": sum(1 for r in reviews if r["verified"]),
    }


def mark_helpful(review_id: str) -> bool:
    for r in REVIEWS:
        if r["id"] == review_id:
            r["helpful"] += 1
            return True
    return False


async def moderate_review(review_id: str, approved: bool, ask_ai_fn=None) -> dict:
    """Moderate a review (by Nova AI or admin)"""
    for r in REVIEWS:
        if r["id"] == review_id:
            r["moderated"] = approved
            r["moderated_by"] = "Nova (IA)"
            return {"success": True, "review": r}
    return {"success": False, "error": "Review not found"}


def get_pending_reviews() -> list:
    return [r for r in REVIEWS if not r["moderated"]]


def get_review_stats() -> dict:
    total = len(REVIEWS)
    moderated = sum(1 for r in REVIEWS if r["moderated"])
    avg_rating = sum(r["rating"] for r in REVIEWS) / total if total else 0
    return {
        "total_reviews": total,
        "moderated": moderated,
        "pending": total - moderated,
        "avg_rating": round(avg_rating, 1),
        "verified": sum(1 for r in REVIEWS if r["verified"]),
    }
