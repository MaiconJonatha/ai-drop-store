"""
AI Email Marketing - Automated campaigns
- Cart abandonment recovery
- Welcome emails
- Order confirmation
- Weekly deals newsletter
- Re-engagement campaigns

All emails written by Aria (AI Copywriter)
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

import httpx

# Email config (supports multiple providers)
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "resend")  # resend, sendgrid, smtp
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "loja@aidropstore.com")
STORE_URL = os.environ.get("STORE_URL", "https://ai-drop-store-nd4f.onrender.com")

# Email templates
TEMPLATES = {
    "welcome": {
        "subject": "🎉 Bem-vindo à AI Drop Store! 10% OFF no primeiro pedido",
        "body": """
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#fff">
  <div style="background:#111;padding:30px;text-align:center">
    <h1 style="color:#fff;font-size:28px;margin:0"><span style="color:#E30613">AI</span> DROP STORE</h1>
    <p style="color:#999;font-size:12px;margin-top:5px">100% operada por Inteligência Artificial</p>
  </div>
  <div style="padding:30px">
    <h2 style="font-size:22px">Olá, {name}! 👋</h2>
    <p style="color:#666;line-height:1.6">Bem-vindo(a) à primeira loja do mundo operada 100% por IAs!</p>
    <p style="color:#666;line-height:1.6">Nossa equipe de 6 IAs está pronta para te atender:</p>
    <ul style="color:#666;line-height:2">
      <li>👩‍💼 <strong>Luna</strong> - CEO que seleciona os melhores produtos</li>
      <li>✍️ <strong>Aria</strong> - Copywriter que escreveu este email!</li>
      <li>🎧 <strong>Nova</strong> - Suporte 24/7 no WhatsApp</li>
      <li>📊 <strong>Zara</strong> - Pricing dinâmico</li>
    </ul>
    <div style="background:#f5f5f5;padding:20px;border-radius:12px;text-align:center;margin:20px 0">
      <p style="font-size:14px;color:#666">Use o cupom abaixo para 10% OFF:</p>
      <div style="background:#111;color:#fff;padding:12px 24px;border-radius:8px;display:inline-block;font-size:24px;font-weight:900;letter-spacing:2px;margin:10px 0">
        PRIMEIRACOMPRA
      </div>
    </div>
    <a href="{store_url}" style="display:block;background:#E30613;color:#fff;text-decoration:none;padding:16px;border-radius:30px;text-align:center;font-weight:700;font-size:16px">
      EXPLORAR A LOJA 🛒
    </a>
  </div>
  <div style="background:#111;padding:20px;text-align:center">
    <p style="color:#666;font-size:11px">AI Drop Store © 2026 • Nike + Anthropic + Tech</p>
  </div>
</div>"""
    },
    "cart_abandoned": {
        "subject": "😢 Você esqueceu algo no carrinho! {product_name} te espera",
        "body": """
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#fff">
  <div style="background:#111;padding:30px;text-align:center">
    <h1 style="color:#fff;font-size:28px;margin:0"><span style="color:#E30613">AI</span> DROP STORE</h1>
  </div>
  <div style="padding:30px">
    <h2 style="font-size:22px">Hey {name}, não vai deixar escapar! 😱</h2>
    <p style="color:#666;line-height:1.6">Você estava de olho em um produto incrível e ele ainda está te esperando:</p>
    <div style="border:2px solid #E30613;border-radius:12px;padding:20px;margin:20px 0;display:flex;gap:16px">
      <img src="{product_image}" style="width:100px;height:100px;border-radius:8px;object-fit:cover" alt="">
      <div>
        <h3 style="margin:0 0 8px;font-size:18px">{product_name}</h3>
        <p style="color:#E30613;font-size:24px;font-weight:900;margin:0">R$ {price}</p>
        <p style="color:#999;text-decoration:line-through;margin:4px 0 0;font-size:14px">R$ {old_price}</p>
        <span style="background:#E30613;color:#fff;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700">-{discount}% OFF</span>
      </div>
    </div>
    <p style="color:#666;font-size:14px">⚠️ Restam apenas <strong>{stock} unidades</strong> em estoque!</p>
    <a href="{store_url}/product/{product_id}" style="display:block;background:#111;color:#fff;text-decoration:none;padding:16px;border-radius:30px;text-align:center;font-weight:700;font-size:16px;margin:20px 0">
      FINALIZAR COMPRA →
    </a>
    <p style="color:#999;font-size:12px;text-align:center">Cupom especial: VOLTEI = 5% extra de desconto 🎁</p>
  </div>
</div>"""
    },
    "order_confirmed": {
        "subject": "✅ Pedido {order_id} confirmado! IA Vega está preparando",
        "body": """
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#fff">
  <div style="background:#111;padding:30px;text-align:center">
    <h1 style="color:#fff;font-size:28px;margin:0"><span style="color:#E30613">AI</span> DROP STORE</h1>
  </div>
  <div style="padding:30px">
    <div style="text-align:center;margin-bottom:20px">
      <span style="font-size:64px">✅</span>
      <h2 style="font-size:22px;margin:10px 0 0">Pedido Confirmado!</h2>
    </div>
    <div style="background:#f5f5f5;padding:20px;border-radius:12px;margin:20px 0">
      <p><strong>Pedido:</strong> {order_id}</p>
      <p><strong>Produto:</strong> {product_name} x{qty}</p>
      <p><strong>Total:</strong> <span style="color:#E30613;font-weight:900;font-size:20px">R$ {total}</span></p>
      <p><strong>Status:</strong> 🟡 Processando</p>
      <p><strong>Entrega estimada:</strong> {delivery_date}</p>
    </div>
    <p style="color:#666;line-height:1.6">🚚 IA <strong>Vega</strong> já está coordenando a logística do seu pedido. Você receberá o rastreamento por email assim que for despachado!</p>
    <a href="{store_url}/conta" style="display:block;background:#111;color:#fff;text-decoration:none;padding:16px;border-radius:30px;text-align:center;font-weight:700;font-size:16px;margin:20px 0">
      ACOMPANHAR PEDIDO 📦
    </a>
  </div>
</div>"""
    },
    "weekly_deals": {
        "subject": "🔥 Top 5 ofertas da semana - até {max_discount}% OFF!",
        "body": """
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#fff">
  <div style="background:#111;padding:30px;text-align:center">
    <h1 style="color:#fff;font-size:28px;margin:0"><span style="color:#E30613">AI</span> DROP STORE</h1>
    <p style="color:#E30613;font-size:14px;font-weight:700;margin-top:8px">🔥 OFERTAS DA SEMANA</p>
  </div>
  <div style="padding:30px">
    <h2 style="font-size:22px;text-align:center">Curadoria da IA Luna 👩‍💼</h2>
    <p style="color:#666;text-align:center;margin-bottom:20px">Os produtos mais quentes selecionados pela nossa CEO de Inteligência Artificial</p>
    {products_html}
    <a href="{store_url}" style="display:block;background:#E30613;color:#fff;text-decoration:none;padding:16px;border-radius:30px;text-align:center;font-weight:700;font-size:16px;margin:20px 0">
      VER TODAS AS OFERTAS 🛒
    </a>
  </div>
</div>"""
    },
}

# In-memory subscriber list and abandoned carts
SUBSCRIBERS = []  # [{email, name, subscribed_at}]
ABANDONED_CARTS = []  # [{email, name, product, added_at, reminded}]
EMAIL_LOG = []  # [{to, subject, template, sent_at, status}]


async def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send email via Resend API (free tier: 100/day)"""
    if RESEND_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post("https://api.resend.com/emails", json={
                    "from": f"AI Drop Store <{FROM_EMAIL}>",
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                }, headers={"Authorization": f"Bearer {RESEND_API_KEY}"})
                success = r.status_code in (200, 201)
                EMAIL_LOG.append({"to": to, "subject": subject, "sent_at": datetime.now().isoformat(), "status": "sent" if success else "failed"})
                return success
        except Exception as e:
            print(f"[EMAIL] Error: {e}")
    
    # Log locally if no API key
    EMAIL_LOG.append({"to": to, "subject": subject, "sent_at": datetime.now().isoformat(), "status": "queued"})
    print(f"[EMAIL] Queued: {subject} → {to}")
    return True


async def send_welcome_email(name: str, email: str):
    """Send welcome email to new customer"""
    tmpl = TEMPLATES["welcome"]
    body = tmpl["body"].format(name=name, store_url=STORE_URL)
    await send_email(email, tmpl["subject"], body)
    SUBSCRIBERS.append({"email": email, "name": name, "subscribed_at": datetime.now().isoformat()})


async def send_order_email(email: str, name: str, order: dict, product: dict):
    """Send order confirmation email"""
    tmpl = TEMPLATES["order_confirmed"]
    delivery = (datetime.now() + timedelta(days=product.get("shipping_days", 7))).strftime("%d/%m/%Y")
    subject = tmpl["subject"].format(order_id=order["id"])
    body = tmpl["body"].format(
        order_id=order["id"], product_name=order["product"],
        qty=order["qty"], total=f"{order['total']:.2f}",
        delivery_date=delivery, store_url=STORE_URL
    )
    await send_email(email, subject, body)


async def send_cart_reminder(email: str, name: str, product: dict):
    """Send cart abandonment email"""
    tmpl = TEMPLATES["cart_abandoned"]
    subject = tmpl["subject"].format(product_name=product["name"])
    body = tmpl["body"].format(
        name=name, product_name=product["name"],
        product_image=product["image"], price=f"{product['price']:.2f}",
        old_price=f"{product['old_price']:.2f}", discount=product["discount"],
        stock=product["stock"], product_id=product["id"], store_url=STORE_URL
    )
    await send_email(email, subject, body)


async def send_weekly_deals(products: list):
    """Send weekly deals to all subscribers"""
    top5 = sorted(products, key=lambda x: -x.get("discount", 0))[:5]
    products_html = ""
    for p in top5:
        products_html += f"""
        <div style="display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #eee">
          <img src="{p['image']}" style="width:80px;height:80px;border-radius:8px;object-fit:cover">
          <div style="flex:1">
            <h4 style="margin:0;font-size:14px">{p['name']}</h4>
            <p style="color:#E30613;font-weight:900;font-size:18px;margin:4px 0">R$ {p['price']:.2f}</p>
            <span style="background:#E30613;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px">-{p['discount']}%</span>
          </div>
        </div>"""
    
    max_disc = max(p["discount"] for p in top5) if top5 else 50
    tmpl = TEMPLATES["weekly_deals"]
    subject = tmpl["subject"].format(max_discount=max_disc)
    body = tmpl["body"].format(products_html=products_html, store_url=STORE_URL)
    
    sent = 0
    for sub in SUBSCRIBERS:
        await send_email(sub["email"], subject, body)
        sent += 1
    return sent


def add_abandoned_cart(email: str, name: str, product: dict):
    """Track abandoned cart"""
    ABANDONED_CARTS.append({
        "email": email, "name": name, "product": product,
        "added_at": datetime.now().isoformat(), "reminded": False
    })


async def process_abandoned_carts():
    """Send reminders for carts abandoned > 1 hour ago"""
    cutoff = datetime.now() - timedelta(hours=1)
    sent = 0
    for cart in ABANDONED_CARTS:
        if not cart["reminded"]:
            added = datetime.fromisoformat(cart["added_at"])
            if added < cutoff:
                await send_cart_reminder(cart["email"], cart["name"], cart["product"])
                cart["reminded"] = True
                sent += 1
    return sent


def get_email_stats():
    """Get email marketing stats"""
    return {
        "subscribers": len(SUBSCRIBERS),
        "emails_sent": len(EMAIL_LOG),
        "abandoned_carts": len(ABANDONED_CARTS),
        "carts_recovered": sum(1 for c in ABANDONED_CARTS if c["reminded"]),
        "recent_emails": EMAIL_LOG[-20:][::-1],
    }
