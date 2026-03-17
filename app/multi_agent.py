"""
🤖 Sistema Multi-Agentes Sistêmico
6 IAs trabalhando juntas com rotinas automáticas, comunicação inter-agentes,
e decisões colaborativas.

Arquitetura:
- Cada IA tem rotinas que rodam em intervalos definidos
- Canal de mensagens entre IAs (message bus)
- Decisões colaborativas (votação entre IAs)
- Memória compartilhada (knowledge base)
- Relatórios de performance
"""

import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field, asdict

# ─── Message Bus (Comunicação Inter-Agentes) ───

@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str  # "all" for broadcast
    type: str  # "info", "request", "decision", "alert", "report"
    content: str
    data: dict = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class MessageBus:
    def __init__(self):
        self.messages: list[dict] = []
        self.max_messages = 500
    
    def send(self, msg: AgentMessage):
        self.messages.append(asdict(msg))
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_for(self, agent: str, limit: int = 20) -> list[dict]:
        return [m for m in self.messages if m["to_agent"] in (agent, "all")][-limit:]
    
    def get_all(self, limit: int = 50) -> list[dict]:
        return self.messages[-limit:][::-1]
    
    def get_conversations(self, limit: int = 30) -> list[dict]:
        return self.messages[-limit:][::-1]

# ─── Knowledge Base (Memória Compartilhada) ───

class KnowledgeBase:
    def __init__(self):
        self.facts: dict[str, dict] = {}
        self.trends: list[dict] = []
        self.decisions: list[dict] = []
        self.performance: dict[str, dict] = {}
    
    def add_fact(self, agent: str, key: str, value, confidence: float = 1.0):
        self.facts[key] = {
            "value": value, "by": agent,
            "confidence": confidence,
            "updated": datetime.now().isoformat()
        }
    
    def get_fact(self, key: str):
        f = self.facts.get(key)
        return f["value"] if f else None
    
    def add_trend(self, agent: str, category: str, direction: str, detail: str):
        self.trends.append({
            "agent": agent, "category": category,
            "direction": direction, "detail": detail,
            "time": datetime.now().isoformat()
        })
        if len(self.trends) > 200:
            self.trends = self.trends[-200:]
    
    def add_decision(self, agents: list[str], decision: str, reason: str, impact: str):
        self.decisions.append({
            "agents": agents, "decision": decision,
            "reason": reason, "impact": impact,
            "time": datetime.now().isoformat()
        })
        if len(self.decisions) > 100:
            self.decisions = self.decisions[-100:]
    
    def update_performance(self, agent: str, metric: str, value: float):
        if agent not in self.performance:
            self.performance[agent] = {}
        self.performance[agent][metric] = {
            "value": value, "updated": datetime.now().isoformat()
        }

# ─── Agent Routines ───

bus = MessageBus()
kb = KnowledgeBase()

# Reference to main app data (set by init)
_products = []
_orders = []
_stats = {}
_activity_log = []
_ask_ai_fn = None
_log_ai_fn = None
_log_activity_fn = None
_inc_stat_fn = None
_update_product_fn = None
_notify_fns = {}

def init_multi_agent(products, orders, stats, activity_log,
                     ask_ai_fn, log_ai_fn, log_activity_fn, 
                     inc_stat_fn, update_product_fn, notify_fns):
    global _products, _orders, _stats, _activity_log
    global _ask_ai_fn, _log_ai_fn, _log_activity_fn, _inc_stat_fn, _update_product_fn, _notify_fns
    _products = products
    _orders = orders
    _stats = stats
    _activity_log = activity_log
    _ask_ai_fn = ask_ai_fn
    _log_ai_fn = log_ai_fn
    _log_activity_fn = log_activity_fn
    _inc_stat_fn = inc_stat_fn
    _update_product_fn = update_product_fn
    _notify_fns = notify_fns


# ═══════════════════════════════════════════
# LUNA - CEO & Product Manager
# Rotinas: análise de catálogo, decisões estratégicas, coordenação
# ═══════════════════════════════════════════

async def luna_routine():
    """Luna analisa o catálogo e toma decisões estratégicas"""
    while True:
        await asyncio.sleep(90)  # A cada 1.5 min
        try:
            if not _products:
                continue
            
            # 1. Análise de catálogo
            total = len(_products)
            low_stock = [p for p in _products if p["stock"] < 10]
            top_sellers = sorted(_products, key=lambda x: x["sold"], reverse=True)[:5]
            poor_sellers = sorted(_products, key=lambda x: x["sold"])[:5]
            
            kb.add_fact("Luna", "total_products", total)
            kb.add_fact("Luna", "low_stock_count", len(low_stock))
            kb.add_fact("Luna", "top_seller", top_sellers[0]["name"] if top_sellers else "N/A")
            
            # 2. Decisão: restock?
            if low_stock:
                for p in low_stock[:3]:
                    old_stock = p["stock"]
                    p["stock"] += random.randint(20, 50)
                    if _update_product_fn:
                        await _update_product_fn(p["id"], stock=p["stock"])
                    
                    bus.send(AgentMessage(
                        from_agent="Luna", to_agent="Vega", type="request",
                        content=f"Reabastecer {p['name']}: {old_stock} → {p['stock']} unidades",
                        data={"product_id": p["id"], "new_stock": p["stock"]}
                    ))
                    _log_ai_fn("Luna", "RESTOCK", f"{p['name']}: +{p['stock']-old_stock} un (estoque: {p['stock']})")
                
                kb.add_decision(
                    ["Luna", "Vega"], 
                    f"Reabastecimento de {len(low_stock)} produtos",
                    "Estoque abaixo de 10 unidades",
                    f"Evitar ruptura de estoque"
                )
            
            # 3. Briefing para equipe
            revenue = _stats.get("total_revenue", 0)
            orders_n = _stats.get("orders_count", 0)
            
            bus.send(AgentMessage(
                from_agent="Luna", to_agent="all", type="report",
                content=f"📊 Status: {total} produtos, {orders_n} pedidos, R${revenue:.2f} receita. Top: {top_sellers[0]['name'] if top_sellers else 'N/A'}",
                data={"revenue": revenue, "orders": orders_n, "products": total}
            ))
            
            # 4. Ask AI for strategic insight (sometimes)
            if random.random() < 0.2 and _ask_ai_fn:
                top_names = ", ".join(p["name"] for p in top_sellers[:3])
                poor_names = ", ".join(p["name"] for p in poor_sellers[:3])
                insight = await _ask_ai_fn("luna", 
                    f"Como CEO da loja, analise: Top vendas: {top_names}. Piores vendas: {poor_names}. "
                    f"Receita total: R${revenue:.2f}. Dê 1 insight estratégico curto (1 frase).", 100)
                if insight:
                    bus.send(AgentMessage(
                        from_agent="Luna", to_agent="all", type="info",
                        content=f"💡 Insight: {insight[:200]}"
                    ))
                    _log_ai_fn("Luna", "STRATEGY", insight[:150])
            
            kb.update_performance("Luna", "catalog_reviews", 
                                  kb.performance.get("Luna", {}).get("catalog_reviews", {}).get("value", 0) + 1)
            
        except Exception:
            pass


# ═══════════════════════════════════════════
# ARIA - Copywriter & Marketing
# Rotinas: atualizar descrições, campanhas, SEO
# ═══════════════════════════════════════════

async def aria_routine():
    """Aria melhora descrições e cria campanhas"""
    while True:
        await asyncio.sleep(120)  # A cada 2 min
        try:
            if not _products:
                continue
            
            # 1. Melhorar descrição de 1 produto aleatório
            p = random.choice(_products)
            old_desc = p.get("description", "")
            
            if _ask_ai_fn and random.random() < 0.3:
                new_desc = await _ask_ai_fn("aria",
                    f"Reescreva esta descrição de produto para ser mais persuasiva (max 2 frases): "
                    f"Produto: {p['name']}. Descrição atual: {old_desc[:100]}. "
                    f"Use gatilhos mentais de urgência.", 150)
                if new_desc and len(new_desc) > 20:
                    p["description"] = new_desc
                    bus.send(AgentMessage(
                        from_agent="Aria", to_agent="Luna", type="info",
                        content=f"📝 Descrição atualizada: {p['name']}",
                        data={"product": p["name"], "new_desc": new_desc[:100]}
                    ))
                    _log_ai_fn("Aria", "COPY_UPDATE", f"Nova descrição para {p['name']}")
            
            # 2. Criar campanha/promoção
            if random.random() < 0.25:
                top = sorted(_products, key=lambda x: x["sold"], reverse=True)[:3]
                campaign_types = [
                    f"🔥 FLASH SALE: {top[0]['name']} com {top[0]['discount']}% OFF!",
                    f"🎯 COMBO: {top[0]['name']} + {top[1]['name'] if len(top)>1 else 'brinde'} = desconto especial!",
                    f"⏰ ÚLTIMA CHANCE: Só restam {random.randint(3,15)} unidades de {random.choice(_products)['name']}!",
                    f"🏆 BEST SELLER: {top[0]['name']} - {top[0]['sold']} vendidos! Garanta o seu.",
                    f"💎 LANÇAMENTO: Novos produtos chegando! Fique atento.",
                ]
                campaign = random.choice(campaign_types)
                
                bus.send(AgentMessage(
                    from_agent="Aria", to_agent="Iris", type="request",
                    content=f"Nova campanha para redes sociais: {campaign}",
                    data={"campaign": campaign, "type": "social_post"}
                ))
                bus.send(AgentMessage(
                    from_agent="Aria", to_agent="all", type="info",
                    content=f"📢 Campanha criada: {campaign}"
                ))
                _log_ai_fn("Aria", "CAMPAIGN", campaign[:120])
                
                kb.add_trend("Aria", "marketing", "up", f"Campanha: {campaign[:80]}")
            
            kb.update_performance("Aria", "descriptions_updated",
                                  kb.performance.get("Aria", {}).get("descriptions_updated", {}).get("value", 0) + 1)
            
        except Exception:
            pass


# ═══════════════════════════════════════════
# NOVA - Suporte ao Cliente
# Rotinas: monitorar pedidos, responder automaticamente, satisfação
# ═══════════════════════════════════════════

async def nova_routine():
    """Nova monitora pedidos e satisfação"""
    while True:
        await asyncio.sleep(100)  # A cada ~1.7 min
        try:
            # 1. Monitorar pedidos pendentes
            pending = [o for o in _orders if o.get("status") == "Processando"]
            shipped = [o for o in _orders if o.get("status") == "Enviado"]
            transit = [o for o in _orders if o.get("status") == "Em trânsito"]
            
            kb.add_fact("Nova", "pending_orders", len(pending))
            kb.add_fact("Nova", "shipped_orders", len(shipped))
            kb.add_fact("Nova", "transit_orders", len(transit))
            
            # 2. Atualizar status de pedidos antigos
            for o in pending[:2]:
                if random.random() < 0.4:
                    o["status"] = "Enviado"
                    bus.send(AgentMessage(
                        from_agent="Nova", to_agent="Vega", type="info",
                        content=f"📦 Pedido {o['id']} atualizado: Processando → Enviado",
                        data={"order_id": o["id"]}
                    ))
                    _log_ai_fn("Nova", "ORDER_UPDATE", f"Pedido {o['id']} → Enviado")
            
            for o in shipped[:2]:
                if random.random() < 0.3:
                    o["status"] = "Em trânsito"
                    bus.send(AgentMessage(
                        from_agent="Nova", to_agent="all", type="info",
                        content=f"🚚 Pedido {o['id']} em trânsito!"
                    ))
                    _log_ai_fn("Nova", "TRACKING", f"Pedido {o['id']} → Em trânsito")
            
            # 3. Gerar feedback de satisfação
            if _orders and random.random() < 0.3:
                o = random.choice(_orders[-20:] if len(_orders) > 20 else _orders)
                satisfaction = random.choice(["⭐⭐⭐⭐⭐ Excelente!", "⭐⭐⭐⭐ Muito bom!", "⭐⭐⭐⭐⭐ Perfeito!"])
                bus.send(AgentMessage(
                    from_agent="Nova", to_agent="Luna", type="report",
                    content=f"📋 Feedback pedido {o['id']}: {satisfaction}",
                    data={"order_id": o["id"], "satisfaction": satisfaction}
                ))
                _log_ai_fn("Nova", "FEEDBACK", f"Pedido {o['id']}: {satisfaction}")
            
            # 4. Report to Luna
            if random.random() < 0.2:
                total_orders = len(_orders)
                bus.send(AgentMessage(
                    from_agent="Nova", to_agent="Luna", type="report",
                    content=f"📊 Suporte: {total_orders} pedidos | {len(pending)} pendentes | {len(shipped)} enviados | {len(transit)} em trânsito"
                ))
            
            kb.update_performance("Nova", "orders_monitored",
                                  kb.performance.get("Nova", {}).get("orders_monitored", {}).get("value", 0) + 1)
            
        except Exception:
            pass


# ═══════════════════════════════════════════
# ZARA - Pricing & Analytics
# Rotinas: ajuste dinâmico de preços, análise de margens, competitividade
# ═══════════════════════════════════════════

async def zara_routine():
    """Zara otimiza preços e analisa dados"""
    while True:
        await asyncio.sleep(80)  # A cada ~1.3 min
        try:
            if not _products:
                continue
            
            # 1. Ajuste dinâmico de preço (2-3 produtos por ciclo)
            adjusted = []
            for _ in range(random.randint(1, 3)):
                p = random.choice(_products)
                old = p["price"]
                
                # Estratégia baseada em vendas
                if p["sold"] > 1500:  # Alta demanda → pode subir
                    change = random.uniform(0.0, 0.08)
                elif p["sold"] < 200:  # Baixa demanda → desconto
                    change = random.uniform(-0.10, -0.02)
                else:  # Normal
                    change = random.uniform(-0.05, 0.05)
                
                p["price"] = round(p["price"] * (1 + change), 2)
                if p["price"] < p["supplier_price"] * 1.5:
                    p["price"] = round(p["supplier_price"] * 2.5, 2)
                
                p["old_price"] = round(p["price"] * random.uniform(1.2, 1.5), 2)
                p["discount"] = round((1 - p["price"] / p["old_price"]) * 100)
                p["margin"] = round((p["price"] - p["supplier_price"]) / p["price"] * 100, 1)
                
                if _update_product_fn:
                    await _update_product_fn(p["id"], price=p["price"], old_price=p["old_price"], 
                                            discount=p["discount"])
                
                direction = "📈" if p["price"] > old else "📉"
                adjusted.append(f"{p['name'][:20]}: R${old:.2f}→R${p['price']:.2f}")
                _log_ai_fn("Zara", "PRICING", f"{direction} {p['name']}: R${old:.2f} → R${p['price']:.2f}")
            
            if adjusted:
                bus.send(AgentMessage(
                    from_agent="Zara", to_agent="Luna", type="report",
                    content=f"💰 Preços ajustados: {'; '.join(adjusted[:3])}",
                    data={"adjustments": len(adjusted)}
                ))
            
            # 2. Análise de margens
            margins = [p["margin"] for p in _products]
            avg_margin = sum(margins) / len(margins)
            low_margin = [p for p in _products if p["margin"] < 30]
            high_margin = [p for p in _products if p["margin"] > 70]
            
            kb.add_fact("Zara", "avg_margin", round(avg_margin, 1))
            kb.add_fact("Zara", "low_margin_count", len(low_margin))
            kb.add_fact("Zara", "high_margin_count", len(high_margin))
            
            # 3. Insight analítico
            if random.random() < 0.2:
                total_rev = _stats.get("total_revenue", 0)
                total_orders = _stats.get("orders_count", 0)
                avg_ticket = round(total_rev / total_orders, 2) if total_orders > 0 else 0
                
                kb.add_fact("Zara", "avg_ticket", avg_ticket)
                kb.add_trend("Zara", "analytics", "up" if avg_ticket > 100 else "stable",
                            f"Ticket médio: R${avg_ticket:.2f}")
                
                bus.send(AgentMessage(
                    from_agent="Zara", to_agent="all", type="info",
                    content=f"📊 Analytics: Margem média {avg_margin:.1f}% | Ticket médio R${avg_ticket:.2f} | {len(low_margin)} produtos margem baixa"
                ))
                _log_ai_fn("Zara", "ANALYTICS", f"Margem: {avg_margin:.1f}% | Ticket: R${avg_ticket:.2f}")
            
            kb.update_performance("Zara", "price_adjustments",
                                  kb.performance.get("Zara", {}).get("price_adjustments", {}).get("value", 0) + len(adjusted))
            
        except Exception:
            pass


# ═══════════════════════════════════════════
# IRIS - Social Media Manager
# Rotinas: criar posts, engajamento, tendências
# ═══════════════════════════════════════════

async def iris_routine():
    """Iris gerencia redes sociais e engajamento"""
    while True:
        await asyncio.sleep(150)  # A cada 2.5 min
        try:
            if not _products:
                continue
            
            # 1. Criar post para redes sociais
            p = random.choice(sorted(_products, key=lambda x: x["sold"], reverse=True)[:10])
            
            post_templates = [
                f"🔥 {p['name']} - OFERTA IMPERDÍVEL! De R${p['old_price']:.2f} por apenas R${p['price']:.2f}! ({p['discount']}% OFF) #dropshipping #IA",
                f"⚡ {p['sold']}+ vendidos! {p['name']} é o favorito dos nossos clientes! Garanta o seu 🛒 #bestseller",
                f"🎯 Nossa IA Zara encontrou o melhor preço para {p['name']}: R${p['price']:.2f}! Aproveite! #AIpowered",
                f"💎 DESTAQUE DA SEMANA: {p['name']} com entrega em {p['shipping_days']} dias! Frete para todo Brasil 🇧🇷",
                f"🤖 Selecionado pela IA Luna: {p['name']} - {p['rating']}⭐ | {p['sold']} vendidos | R${p['price']:.2f} #AIdropstore",
            ]
            
            post = random.choice(post_templates)
            platforms = random.sample(["Instagram", "TikTok", "Twitter/X", "Facebook", "Pinterest"], k=random.randint(2, 4))
            
            bus.send(AgentMessage(
                from_agent="Iris", to_agent="all", type="info",
                content=f"📱 Post criado para {', '.join(platforms)}: {post[:100]}...",
                data={"platforms": platforms, "post": post, "product": p["name"]}
            ))
            _log_ai_fn("Iris", "SOCIAL_POST", f"[{'+'.join(p[:2] for p in platforms)}] {post[:80]}")
            
            # 2. Engajamento simulado
            likes = random.randint(50, 500)
            comments = random.randint(5, 50)
            shares = random.randint(2, 30)
            
            _stats["visitors"] += random.randint(10, 80)  # Social traffic
            if _inc_stat_fn:
                await _inc_stat_fn("visitors", random.randint(10, 80))
            
            bus.send(AgentMessage(
                from_agent="Iris", to_agent="Aria", type="report",
                content=f"📊 Engajamento: {likes} likes, {comments} comentários, {shares} compartilhamentos",
                data={"likes": likes, "comments": comments, "shares": shares}
            ))
            _log_ai_fn("Iris", "ENGAGEMENT", f"❤️ {likes} likes | 💬 {comments} comments | 🔄 {shares} shares")
            
            # 3. Trend analysis
            if random.random() < 0.3:
                trends = ["Sustentabilidade", "Tech wearable", "Minimalismo", "Fitness tech", 
                         "AI tools", "Nike retro", "Skincare coreano", "Smart home"]
                trend = random.choice(trends)
                kb.add_trend("Iris", "social_media", "trending", f"Tendência: {trend}")
                
                bus.send(AgentMessage(
                    from_agent="Iris", to_agent="Luna", type="info",
                    content=f"📈 Tendência detectada: {trend} - considerar para catálogo?",
                    data={"trend": trend}
                ))
                _log_ai_fn("Iris", "TREND", f"🔍 Tendência: {trend}")
            
            kb.update_performance("Iris", "posts_created",
                                  kb.performance.get("Iris", {}).get("posts_created", {}).get("value", 0) + 1)
            
        except Exception:
            pass


# ═══════════════════════════════════════════
# VEGA - Supply Chain & Logistics
# Rotinas: monitorar estoque, fornecedores, entregas
# ═══════════════════════════════════════════

async def vega_routine():
    """Vega gerencia logística e supply chain"""
    while True:
        await asyncio.sleep(110)  # A cada ~1.8 min
        try:
            if not _products:
                continue
            
            # 1. Monitorar estoque
            stock_status = {
                "critical": [p for p in _products if p["stock"] <= 5],
                "low": [p for p in _products if 5 < p["stock"] <= 15],
                "ok": [p for p in _products if 15 < p["stock"] <= 50],
                "high": [p for p in _products if p["stock"] > 50],
            }
            
            kb.add_fact("Vega", "stock_critical", len(stock_status["critical"]))
            kb.add_fact("Vega", "stock_low", len(stock_status["low"]))
            kb.add_fact("Vega", "total_stock", sum(p["stock"] for p in _products))
            
            # 2. Alertar estoque crítico
            for p in stock_status["critical"][:2]:
                bus.send(AgentMessage(
                    from_agent="Vega", to_agent="Luna", type="alert",
                    content=f"⚠️ ESTOQUE CRÍTICO: {p['name']} = {p['stock']} un!",
                    data={"product_id": p["id"], "stock": p["stock"]}
                ))
                _log_ai_fn("Vega", "STOCK_ALERT", f"⚠️ {p['name']}: apenas {p['stock']} un")
                
                # Notify via Telegram
                if _notify_fns.get("stock_low"):
                    await _notify_fns["stock_low"](p["name"], p["stock"])
            
            # 3. Simular recebimento de fornecedores
            if random.random() < 0.2:
                p = random.choice(_products)
                qty_received = random.randint(10, 40)
                p["stock"] += qty_received
                if _update_product_fn:
                    await _update_product_fn(p["id"], stock=p["stock"])
                
                bus.send(AgentMessage(
                    from_agent="Vega", to_agent="all", type="info",
                    content=f"📦 Recebimento: +{qty_received} un de {p['name']} (estoque: {p['stock']})",
                    data={"product": p["name"], "received": qty_received, "new_stock": p["stock"]}
                ))
                _log_ai_fn("Vega", "RECEIVING", f"📦 +{qty_received} un {p['name']} | Estoque: {p['stock']}")
            
            # 4. Atualizar prazos de entrega
            if random.random() < 0.15:
                p = random.choice(_products)
                old_days = p["shipping_days"]
                p["shipping_days"] = random.randint(3, 12)
                if p["shipping_days"] != old_days:
                    _log_ai_fn("Vega", "SHIPPING", f"🚚 {p['name']}: {old_days}d → {p['shipping_days']}d")
                    bus.send(AgentMessage(
                        from_agent="Vega", to_agent="Nova", type="info",
                        content=f"📬 Prazo atualizado: {p['name']} = {p['shipping_days']} dias"
                    ))
            
            # 5. Supply chain report
            if random.random() < 0.2:
                total_stock = sum(p["stock"] for p in _products)
                avg_ship = sum(p["shipping_days"] for p in _products) / len(_products)
                bus.send(AgentMessage(
                    from_agent="Vega", to_agent="Luna", type="report",
                    content=f"📊 Supply: {total_stock} un total | Entrega média: {avg_ship:.1f}d | {len(stock_status['critical'])} críticos"
                ))
                _log_ai_fn("Vega", "SUPPLY_REPORT", f"Estoque: {total_stock} un | Média entrega: {avg_ship:.1f}d")
            
            kb.update_performance("Vega", "stock_checks",
                                  kb.performance.get("Vega", {}).get("stock_checks", {}).get("value", 0) + 1)
            
        except Exception:
            pass


# ═══════════════════════════════════════════
# COLLABORATIVE DECISIONS (Multi-Agent)
# ═══════════════════════════════════════════

async def collaborative_decisions():
    """Decisões colaborativas entre múltiplas IAs"""
    while True:
        await asyncio.sleep(300)  # A cada 5 min
        try:
            if not _products or len(_products) < 5:
                continue
            
            decision_type = random.choice(["promotion", "restock", "discontinue", "price_war"])
            
            if decision_type == "promotion":
                # Luna + Aria + Zara decidem promoção
                candidates = sorted(_products, key=lambda x: x["stock"], reverse=True)[:5]
                p = random.choice(candidates)
                
                old_price = p["price"]
                p["price"] = round(p["price"] * 0.85, 2)
                p["old_price"] = old_price
                p["discount"] = round((1 - p["price"] / old_price) * 100)
                if _update_product_fn:
                    await _update_product_fn(p["id"], price=p["price"], old_price=p["old_price"], discount=p["discount"])
                
                kb.add_decision(
                    ["Luna", "Aria", "Zara"],
                    f"PROMOÇÃO RELÂMPAGO: {p['name']} -{p['discount']}%",
                    f"Estoque alto ({p['stock']} un) + margem permite desconto",
                    f"R${old_price:.2f} → R${p['price']:.2f}"
                )
                
                bus.send(AgentMessage(
                    from_agent="Luna", to_agent="all", type="decision",
                    content=f"⚡ DECISÃO CONJUNTA (Luna+Aria+Zara): PROMOÇÃO {p['name']} de R${old_price:.2f} → R${p['price']:.2f} (-{p['discount']}%)"
                ))
                _log_ai_fn("Luna", "COLLAB_DECISION", f"⚡ Promoção: {p['name']} -{p['discount']}%")
                _log_ai_fn("Aria", "COLLAB_DECISION", f"📢 Criando campanha para promoção {p['name']}")
                _log_ai_fn("Zara", "COLLAB_DECISION", f"💰 Margem ajustada: {p['margin']:.1f}%")
            
            elif decision_type == "restock":
                # Luna + Vega decidem grande restock
                low = sorted(_products, key=lambda x: x["stock"])[:3]
                for p in low:
                    add = random.randint(30, 80)
                    p["stock"] += add
                    if _update_product_fn:
                        await _update_product_fn(p["id"], stock=p["stock"])
                
                kb.add_decision(
                    ["Luna", "Vega"],
                    f"RESTOCK MASSIVO: {len(low)} produtos",
                    "Múltiplos produtos com estoque baixo",
                    f"Total adicionado: ~{sum(30 for _ in low)} unidades"
                )
                
                names = ", ".join(p["name"][:15] for p in low)
                bus.send(AgentMessage(
                    from_agent="Vega", to_agent="all", type="decision",
                    content=f"📦 DECISÃO (Luna+Vega): Restock massivo - {names}"
                ))
                _log_ai_fn("Vega", "COLLAB_DECISION", f"📦 Restock massivo: {len(low)} produtos")
                _log_ai_fn("Luna", "COLLAB_DECISION", f"✅ Aprovado restock de {names[:60]}")
            
            elif decision_type == "price_war":
                # Zara + Luna ajustam preços competitivos
                cats = {}
                for p in _products:
                    cats.setdefault(p["category"], []).append(p)
                
                cat = random.choice(list(cats.keys()))
                prods = cats[cat]
                adjusted = 0
                for p in prods:
                    if random.random() < 0.5:
                        p["price"] = round(p["price"] * random.uniform(0.92, 0.98), 2)
                        if p["price"] < p["supplier_price"] * 1.5:
                            p["price"] = round(p["supplier_price"] * 2.0, 2)
                        p["old_price"] = round(p["price"] * random.uniform(1.25, 1.5), 2)
                        p["discount"] = round((1 - p["price"] / p["old_price"]) * 100)
                        if _update_product_fn:
                            await _update_product_fn(p["id"], price=p["price"], old_price=p["old_price"], discount=p["discount"])
                        adjusted += 1
                
                if adjusted > 0:
                    kb.add_decision(
                        ["Zara", "Luna"],
                        f"AJUSTE COMPETITIVO: {adjusted} produtos em '{cat}'",
                        "Aumentar competitividade na categoria",
                        f"Preços reduzidos em média 5%"
                    )
                    bus.send(AgentMessage(
                        from_agent="Zara", to_agent="all", type="decision",
                        content=f"💰 DECISÃO (Zara+Luna): Ajuste competitivo em '{cat}' - {adjusted} produtos reajustados"
                    ))
                    _log_ai_fn("Zara", "COLLAB_DECISION", f"💰 Ajuste competitivo: {cat} ({adjusted} produtos)")
            
        except Exception:
            pass


# ═══════════════════════════════════════════
# API ENDPOINTS DATA
# ═══════════════════════════════════════════

def get_agent_status():
    """Retorna status de todos os agentes para dashboard"""
    agents = []
    for key, ai in [("luna", "Luna"), ("aria", "Aria"), ("nova", "Nova"), 
                     ("zara", "Zara"), ("iris", "Iris"), ("vega", "Vega")]:
        perf = kb.performance.get(ai, {})
        agents.append({
            "name": ai,
            "role": {"luna": "CEO", "aria": "Copywriter", "nova": "Suporte",
                    "zara": "Pricing", "iris": "Social Media", "vega": "Logística"}[key],
            "status": "online",
            "performance": {k: v.get("value", 0) for k, v in perf.items()},
            "last_active": perf.get(list(perf.keys())[-1], {}).get("updated", "") if perf else "",
        })
    return agents

def get_multi_agent_data():
    """Retorna dados completos do sistema multi-agente"""
    return {
        "agents": get_agent_status(),
        "messages": bus.get_all(50),
        "decisions": kb.decisions[-20:][::-1],
        "trends": kb.trends[-20:][::-1],
        "facts": {k: v for k, v in kb.facts.items()},
        "performance": kb.performance,
    }


# ═══════════════════════════════════════════
# START ALL ROUTINES
# ═══════════════════════════════════════════

async def start_all_agents():
    """Inicia todas as rotinas dos agentes"""
    tasks = [
        asyncio.create_task(luna_routine()),
        asyncio.create_task(aria_routine()),
        asyncio.create_task(nova_routine()),
        asyncio.create_task(zara_routine()),
        asyncio.create_task(iris_routine()),
        asyncio.create_task(vega_routine()),
        asyncio.create_task(collaborative_decisions()),
    ]
    
    bus.send(AgentMessage(
        from_agent="Sistema", to_agent="all", type="info",
        content="🚀 Sistema Multi-Agentes inicializado! 6 IAs + decisões colaborativas ativas."
    ))
    
    return tasks
