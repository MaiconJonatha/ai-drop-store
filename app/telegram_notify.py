"""Telegram Sales Notifications for AI Drop Store"""
import os
import httpx
from datetime import datetime

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8649057152:AAEK8PeHNP1qrM9uORVPEsr-xbA2ptLRV8o")
CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS", "").split(",")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Store chat IDs of users who message the bot
registered_chats = set()

async def send_telegram(text: str, chat_id: str = None, parse_mode: str = "HTML"):
    """Send message to Telegram"""
    targets = [chat_id] if chat_id else list(registered_chats) + [c for c in CHAT_IDS if c]
    if not targets:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for cid in targets:
                if not cid:
                    continue
                await client.post(f"{TELEGRAM_API}/sendMessage", json={
                    "chat_id": cid.strip(),
                    "text": text,
                    "parse_mode": parse_mode,
                })
        return True
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False

async def notify_new_order(order: dict, product: dict):
    """Notify about new sale"""
    msg = (
        f"🛒 <b>NOVA VENDA!</b>\n\n"
        f"📦 Pedido: <b>{order['id']}</b>\n"
        f"🏷️ Produto: <b>{product.get('name', order.get('product', ''))}</b>\n"
        f"{'👟 Nike' if product.get('brand') == 'Nike' else '🤖 Anthropic' if product.get('brand') == 'Anthropic' else '📦 ' + product.get('category', '')}\n"
        f"📊 Qtd: {order['qty']}x\n"
        f"💰 Total: <b>R$ {order['total']:.2f}</b>\n"
        f"📈 Lucro: <b>R$ {order['profit']:.2f}</b>\n"
        f"👤 Cliente: {order['customer']}\n"
        f"🚚 IA Vega processando envio\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
    )
    return await send_telegram(msg)

async def notify_daily_summary(stats: dict, top_products: list):
    """Daily sales summary"""
    top = "\n".join([f"  {i+1}. {p['name']} ({p['sold']} vendas)" for i, p in enumerate(top_products[:5])])
    msg = (
        f"📊 <b>RESUMO DIÁRIO - AI Drop Store</b>\n\n"
        f"💰 Receita: <b>R$ {stats.get('total_revenue', 0):.2f}</b>\n"
        f"📦 Pedidos: <b>{int(stats.get('orders_count', 0))}</b>\n"
        f"👀 Visitantes: <b>{int(stats.get('visitors', 0))}</b>\n"
        f"🧠 Decisões IA: <b>{int(stats.get('ai_decisions', 0))}</b>\n"
        f"🎯 Produtos: <b>{int(stats.get('products_curated', 0))}</b>\n\n"
        f"🏆 <b>Top 5 Produtos:</b>\n{top}\n\n"
        f"🤖 6 IAs trabalhando 24/7"
    )
    return await send_telegram(msg)

async def notify_price_change(product_name: str, old_price: float, new_price: float):
    """Notify about AI price adjustment"""
    direction = "📈" if new_price > old_price else "📉"
    msg = (
        f"{direction} <b>Preço Ajustado pela IA Zara</b>\n\n"
        f"🏷️ {product_name}\n"
        f"💰 R$ {old_price:.2f} → <b>R$ {new_price:.2f}</b>"
    )
    return await send_telegram(msg)

async def notify_stock_low(product_name: str, stock: int):
    """Alert when stock is low"""
    msg = (
        f"⚠️ <b>ESTOQUE BAIXO</b>\n\n"
        f"🏷️ {product_name}\n"
        f"📦 Apenas <b>{stock}</b> unidades restantes!"
    )
    return await send_telegram(msg)

async def notify_new_customer(customer_name: str, email: str):
    """New customer registration"""
    msg = (
        f"👤 <b>NOVO CLIENTE!</b>\n\n"
        f"📧 {email}\n"
        f"👋 {customer_name}\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return await send_telegram(msg)

def register_chat(chat_id: str):
    """Register a chat for notifications"""
    registered_chats.add(str(chat_id))
