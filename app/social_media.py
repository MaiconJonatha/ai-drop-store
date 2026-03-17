"""
AI Social Media Manager - Iris
Auto-posts products to Instagram, TikTok, Twitter/X
Generates captions, hashtags, schedules posts
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

SOCIAL_POSTS = []  # [{platform, product, caption, hashtags, posted_at, engagement}]
SOCIAL_SCHEDULE = []  # [{platform, product_id, scheduled_for, status}]
SOCIAL_STATS = {
    "total_posts": 0,
    "instagram_posts": 0,
    "tiktok_posts": 0,
    "twitter_posts": 0,
    "total_engagement": 0,
    "total_reach": 0,
}

HASHTAGS = {
    "nike": ["#Nike", "#JustDoIt", "#NikeAirMax", "#Sneakers", "#Tênis", "#NikeBrasil", "#AirForce1", "#NikeDunk"],
    "ai": ["#AI", "#Anthropic", "#Claude", "#InteligênciaArtificial", "#IA", "#Tech", "#FuturoDigital", "#AItools"],
    "tech": ["#Tech", "#Gadgets", "#Tecnologia", "#SmartDevice", "#Inovação", "#TechBrasil"],
    "beauty": ["#Beleza", "#Skincare", "#Beauty", "#CuidadosPessoais", "#Makeup", "#SelfCare"],
    "fitness": ["#Fitness", "#Treino", "#GymLife", "#Saúde", "#Workout", "#FitBrasil"],
    "fashion": ["#Moda", "#Fashion", "#Style", "#OOTD", "#Tendência", "#ModaBrasil"],
    "pets": ["#Pets", "#PetLover", "#CachorroFofo", "#GatoFofo", "#AnimalDoméstico"],
    "home": ["#Casa", "#Decoração", "#HomeDecor", "#Design", "#CasaInteligente"],
}

CAPTION_TEMPLATES = [
    "🔥 {name} com {discount}% OFF!\n\n{desc}\n\n💰 De R${old_price} por apenas R${price}\n🚚 Entrega em {days} dias\n\n{hashtags}\n\n🛒 Link na bio!",
    "⚡ OFERTA RELÂMPAGO ⚡\n\n{name}\n{desc}\n\n❌ R${old_price}\n✅ R${price} ({discount}% OFF)\n\n{hashtags}\n\n👉 aidropstore.com",
    "Nosso mais vendido! 🏆\n\n{name}\n🔥 {sold}+ vendidos\n⭐ {rating}/5 estrelas\n\n💰 R${price}\n\n{hashtags}\n\n🤖 Curado por IA",
    "A IA Luna selecionou pra você 👩‍💼✨\n\n{name}\n{desc}\n\nR${price} (era R${old_price})\n📦 Frete grátis +R$199\n\n{hashtags}",
]


def generate_caption(product: dict) -> str:
    """Generate social media caption for product"""
    cat = product.get("category", "tech")
    tags = random.sample(HASHTAGS.get(cat, HASHTAGS["tech"]), min(5, len(HASHTAGS.get(cat, []))))
    tags += ["#AIDropStore", "#DropshippingIA", "#LojaIA"]
    
    template = random.choice(CAPTION_TEMPLATES)
    return template.format(
        name=product["name"],
        desc=product.get("description", "")[:100],
        price=f"{product['price']:.2f}",
        old_price=f"{product['old_price']:.2f}",
        discount=product["discount"],
        sold=product.get("sold", 0),
        rating=product.get("rating", 4.5),
        days=product.get("shipping_days", 7),
        hashtags=" ".join(tags)
    )


def simulate_engagement() -> dict:
    """Simulate social media engagement"""
    return {
        "likes": random.randint(50, 5000),
        "comments": random.randint(5, 200),
        "shares": random.randint(10, 500),
        "saves": random.randint(20, 800),
        "reach": random.randint(500, 50000),
        "impressions": random.randint(1000, 100000),
    }


async def auto_post(product: dict, platform: str = "instagram") -> dict:
    """Create and 'post' to social media"""
    caption = generate_caption(product)
    engagement = simulate_engagement()
    
    post = {
        "platform": platform,
        "product_name": product["name"],
        "product_id": product["id"],
        "caption": caption,
        "image": product["image"],
        "posted_at": datetime.now().isoformat(),
        "engagement": engagement,
        "posted_by": "Iris (IA)",
    }
    
    SOCIAL_POSTS.append(post)
    SOCIAL_STATS["total_posts"] += 1
    SOCIAL_STATS[f"{platform}_posts"] = SOCIAL_STATS.get(f"{platform}_posts", 0) + 1
    SOCIAL_STATS["total_engagement"] += sum(engagement.values()) - engagement["reach"] - engagement["impressions"]
    SOCIAL_STATS["total_reach"] += engagement["reach"]
    
    return post


async def social_media_loop(products: list, log_ai_fn=None):
    """Background loop - auto-post every 30 minutes"""
    while True:
        await asyncio.sleep(1800)  # 30 min
        try:
            if products:
                # Pick a random product (prefer high-discount or popular)
                candidates = sorted(products, key=lambda x: -(x.get("discount", 0) + x.get("sold", 0) / 100))[:10]
                product = random.choice(candidates)
                
                # Post to random platform
                platform = random.choice(["instagram", "instagram", "tiktok", "twitter"])
                post = await auto_post(product, platform)
                
                if log_ai_fn:
                    log_ai_fn("Iris", "SOCIAL_POST", f"📱 {platform}: {product['name']} ({post['engagement']['likes']} likes)")
        except Exception as e:
            print(f"[SOCIAL] Error: {e}")


def get_social_stats():
    return {
        "stats": SOCIAL_STATS,
        "recent_posts": SOCIAL_POSTS[-20:][::-1],
        "top_posts": sorted(SOCIAL_POSTS, key=lambda x: -x["engagement"]["likes"])[:5],
    }
