"""
WhatsApp Bot - Nova AI Customer Support
Uses WhatsApp Cloud API (Meta Business)
Port: integrated with main app on 8020

Nova (IA) responds to customer messages 24/7
Supports: product search, order status, FAQ, human-like conversation
"""

import os
import json
import hashlib
import asyncio
from datetime import datetime
from typing import Optional

import httpx

# WhatsApp Cloud API credentials
WA_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
WA_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "aidropstore2026")
WA_API = "https://graph.facebook.com/v18.0"

# Conversation memory (in-memory, per phone number)
CONVERSATIONS = {}  # phone -> [messages]
WA_STATS = {
    "messages_received": 0,
    "messages_sent": 0,
    "active_conversations": 0,
    "auto_resolved": 0,
    "products_searched": 0,
    "orders_checked": 0,
}

# Quick replies / FAQ
FAQ_RESPONSES = {
    "horario": "🕐 Nossa loja funciona 24/7! As IAs nunca dormem. Atendimento humano: seg-sex 9h-18h.",
    "entrega": "🚚 Prazo de entrega: 3 a 15 dias úteis. Frete grátis acima de R$199! Rastreamento enviado por email.",
    "pagamento": "💳 Aceitamos: PIX (5% off), Cartão (até 12x), Boleto. Pagamento 100% seguro!",
    "troca": "🔄 Trocas e devoluções em até 30 dias. Sem complicação! Envie o produto e reembolsamos.",
    "frete": "📦 Frete grátis acima de R$199! Calculamos o frete na finalização. Média: R$15-25.",
    "garantia": "🛡️ Todos os produtos têm garantia de 90 dias contra defeitos. Nike: garantia estendida de 1 ano.",
    "cupom": "🎉 Use o cupom PRIMEIRACOMPRA para 10% OFF! Cupons exclusivos no nosso Telegram.",
    "pix": "💚 PIX com 5% de desconto! Chave: pagamentos@aidropstore.com. Confirma em segundos!",
    "nike": "👟 Temos Nike Air Max, Air Force 1, Dunk, Jordan, Blazer, Pegasus e muito mais! Todos originais.",
    "anthropic": "🤖 Produtos Anthropic: Cursos de IA, Packs de Prompts, Templates de Chatbot, API Credits e mais!",
}

# Intent detection keywords
INTENTS = {
    "greeting": ["oi", "olá", "ola", "hey", "bom dia", "boa tarde", "boa noite", "eae", "salve", "hello"],
    "product_search": ["produto", "tem", "quero", "procuro", "busco", "nike", "tênis", "tenis", "camiseta", "mochila"],
    "order_status": ["pedido", "rastrear", "entrega", "chegou", "status", "onde está", "rastreio"],
    "price": ["preço", "preco", "quanto", "custa", "valor", "desconto", "promoção", "promocao", "barato"],
    "faq": ["horario", "horário", "entrega", "pagamento", "troca", "frete", "garantia", "cupom", "pix"],
    "complaint": ["reclamação", "reclamacao", "problema", "defeito", "errado", "ruim", "insatisfeito"],
    "thanks": ["obrigado", "obrigada", "valeu", "thanks", "brigado", "vlw"],
    "bye": ["tchau", "até", "ate logo", "bye", "falou", "flw"],
}


def detect_intent(message: str) -> str:
    """Detect user intent from message"""
    msg = message.lower().strip()
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if kw in msg:
                return intent
    return "general"


def get_faq_match(message: str) -> Optional[str]:
    """Try to match FAQ"""
    msg = message.lower()
    for key, response in FAQ_RESPONSES.items():
        if key in msg:
            return response
    return None


class WhatsAppBot:
    """Nova AI WhatsApp Bot"""
    
    def __init__(self, products=None, orders=None, ask_ai_fn=None, log_ai_fn=None):
        self.products = products or []
        self.orders = orders or []
        self.ask_ai = ask_ai_fn
        self.log_ai = log_ai_fn
    
    async def send_message(self, to: str, text: str) -> bool:
        """Send WhatsApp message via Cloud API"""
        if not WA_TOKEN or not WA_PHONE_ID:
            # Fallback: log locally
            print(f"[WA-BOT] → {to}: {text[:100]}")
            return True
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{WA_API}/{WA_PHONE_ID}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {"body": text}
                    },
                    headers={
                        "Authorization": f"Bearer {WA_TOKEN}",
                        "Content-Type": "application/json"
                    }
                )
                WA_STATS["messages_sent"] += 1
                return r.status_code == 200
        except Exception as e:
            print(f"[WA-BOT] Error sending: {e}")
            return False
    
    async def send_template(self, to: str, template_name: str = "hello_world") -> bool:
        """Send template message (for first contact)"""
        if not WA_TOKEN or not WA_PHONE_ID:
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{WA_API}/{WA_PHONE_ID}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "template",
                        "template": {"name": template_name, "language": {"code": "pt_BR"}}
                    },
                    headers={
                        "Authorization": f"Bearer {WA_TOKEN}",
                        "Content-Type": "application/json"
                    }
                )
                return r.status_code == 200
        except:
            return False
    
    async def send_product_card(self, to: str, product: dict) -> bool:
        """Send product info as formatted message"""
        stars = "★" * int(product.get("rating", 4)) + "☆" * (5 - int(product.get("rating", 4)))
        text = (
            f"🛍️ *{product['name']}*\n\n"
            f"{product.get('description', '')}\n\n"
            f"💰 *R$ {product['price']:.2f}* ~~R$ {product['old_price']:.2f}~~\n"
            f"📦 {product.get('stock', 0)} em estoque\n"
            f"🚚 Entrega em {product.get('shipping_days', 7)} dias\n"
            f"{stars} ({product.get('reviews_count', 0)} avaliações)\n"
            f"🔥 {product.get('sold', 0)} vendidos\n\n"
            f"👉 Compre aqui: https://ai-drop-store-nd4f.onrender.com/product/{product['id']}"
        )
        return await self.send_message(to, text)
    
    def search_products(self, query: str) -> list:
        """Search products by query"""
        q = query.lower()
        results = []
        for p in self.products:
            score = 0
            if q in p["name"].lower():
                score += 3
            if q in p.get("description", "").lower():
                score += 1
            if q in p.get("brand", "").lower():
                score += 2
            if q in p.get("category", "").lower():
                score += 2
            if score > 0:
                results.append((score, p))
        results.sort(key=lambda x: -x[0])
        return [r[1] for r in results[:5]]
    
    def find_order(self, order_id: str) -> Optional[dict]:
        """Find order by ID"""
        oid = order_id.upper().strip()
        for o in self.orders:
            if o.get("id", "").upper() == oid:
                return o
        return None
    
    async def generate_ai_response(self, message: str, phone: str) -> str:
        """Use Nova AI to generate response"""
        # Get conversation context
        history = CONVERSATIONS.get(phone, [])[-5:]
        context = "\n".join([f"{'Cliente' if m['role']=='user' else 'Nova'}: {m['text']}" for m in history])
        
        # Top 5 products for context
        top_products = ", ".join([p["name"] for p in sorted(self.products, key=lambda x: -x.get("sold", 0))[:5]])
        
        prompt = f"""Você é Nova, assistente de WhatsApp da AI Drop Store.
Loja de dropshipping com Nike, Anthropic/IA, Tech, Beleza, Fitness, Pets.
Seja amigável, use emojis, responda em 2-3 frases curtas.
Produtos populares: {top_products}
Entrega: 3-15 dias. PIX 5% off. Frete grátis +R$199.

Histórico:
{context}

Cliente: {message}
Nova:"""
        
        if self.ask_ai:
            response = await self.ask_ai("nova", prompt, 200)
            if response:
                return response
        
        # Fallback responses
        return "Olá! 😊 Sou a Nova, assistente da AI Drop Store. Temos Nike, produtos de IA e muito mais! Como posso ajudar?"
    
    async def handle_message(self, phone: str, message: str, name: str = "") -> str:
        """Main message handler - processes and responds"""
        WA_STATS["messages_received"] += 1
        
        # Initialize conversation
        if phone not in CONVERSATIONS:
            CONVERSATIONS[phone] = []
            WA_STATS["active_conversations"] += 1
        
        # Save user message
        CONVERSATIONS[phone].append({
            "role": "user", "text": message,
            "time": datetime.now().isoformat(), "name": name
        })
        
        # Detect intent
        intent = detect_intent(message)
        response = ""
        
        # Handle by intent
        if intent == "greeting":
            nome = name or "cliente"
            response = f"Olá, {nome}! 👋 Sou a Nova, assistente IA da AI Drop Store! Temos Nike, produtos de IA, Tech e muito mais. Como posso te ajudar hoje? 😊"
        
        elif intent == "thanks":
            response = "De nada! 😊 Fico feliz em ajudar. Se precisar de mais alguma coisa, é só chamar! 🛍️"
            WA_STATS["auto_resolved"] += 1
        
        elif intent == "bye":
            response = f"Tchau, {name or 'amigo'}! 👋 Volte sempre à AI Drop Store. Boas compras! 🛒✨"
            WA_STATS["auto_resolved"] += 1
        
        elif intent == "product_search":
            WA_STATS["products_searched"] += 1
            results = self.search_products(message)
            if results:
                product_list = "\n".join([
                    f"• *{p['name']}* - R$ {p['price']:.2f} (-{p['discount']}%)"
                    for p in results[:5]
                ])
                response = f"🔍 Encontrei esses produtos:\n\n{product_list}\n\n👉 Quer detalhes de algum? Me diz qual!"
                # Send first product card
                await self.send_product_card(phone, results[0])
            else:
                response = "🔍 Não encontrei exatamente isso, mas temos Nike, Tech, Beleza, Fitness e Pets! Quer que eu busque algo diferente?"
        
        elif intent == "order_status":
            WA_STATS["orders_checked"] += 1
            # Try to extract order ID
            import re
            order_match = re.search(r'ORD-?\d+', message, re.IGNORECASE)
            if order_match:
                order = self.find_order(order_match.group())
                if order:
                    response = (
                        f"📦 *Pedido {order['id']}*\n"
                        f"Produto: {order['product']}\n"
                        f"Total: R$ {order['total']:.2f}\n"
                        f"Status: {order['status']}\n"
                        f"Responsável: IA {order.get('handled_by', 'Vega')}\n\n"
                        f"🚚 Rastreio será enviado por email quando despachado!"
                    )
                else:
                    response = "🔍 Não encontrei esse pedido. Confirme o número (ex: ORD-0001) ou me envie o email cadastrado."
            else:
                response = "📦 Para consultar seu pedido, me envie o número (ex: ORD-0001). Caso não tenha, me envie o email cadastrado!"
        
        elif intent == "price":
            # Show best deals
            deals = sorted(self.products, key=lambda x: -x.get("discount", 0))[:5]
            deal_list = "\n".join([
                f"🔥 *{p['name']}* - R$ {p['price']:.2f} (-{p['discount']}% OFF!)"
                for p in deals
            ])
            response = f"💰 Melhores ofertas agora:\n\n{deal_list}\n\n🎉 Cupom PRIMEIRACOMPRA = 10% extra!"
        
        elif intent == "faq":
            faq = get_faq_match(message)
            if faq:
                response = faq
                WA_STATS["auto_resolved"] += 1
            else:
                response = await self.generate_ai_response(message, phone)
        
        elif intent == "complaint":
            response = (
                "😔 Sinto muito pelo inconveniente! Sua satisfação é nossa prioridade.\n\n"
                "📧 Envie detalhes para: suporte@aidropstore.com\n"
                "📱 Ou descreva o problema aqui que vou encaminhar para resolução imediata!\n\n"
                "Equipe Vega (Logística IA) vai cuidar do seu caso pessoalmente."
            )
        
        else:
            # General - use AI
            response = await self.generate_ai_response(message, phone)
        
        # Save bot response
        CONVERSATIONS[phone].append({
            "role": "bot", "text": response,
            "time": datetime.now().isoformat()
        })
        
        # Keep conversation manageable
        if len(CONVERSATIONS[phone]) > 50:
            CONVERSATIONS[phone] = CONVERSATIONS[phone][-30:]
        
        # Log AI activity
        if self.log_ai:
            self.log_ai("Nova", "WHATSAPP", f"📱 {phone[-4:]}: {message[:50]}...")
        
        # Send via WhatsApp API
        await self.send_message(phone, response)
        
        return response


# Global bot instance
wa_bot = WhatsAppBot()


def init_whatsapp_bot(products, orders, ask_ai_fn, log_ai_fn):
    """Initialize bot with app data"""
    global wa_bot
    wa_bot = WhatsAppBot(products, orders, ask_ai_fn, log_ai_fn)
    return wa_bot
