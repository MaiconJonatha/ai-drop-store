"""
AI Dropshipping Store - Loja 100% gerida por IAs
Port: 8020

Powered by: Anthropic Claude + Ollama (fallback) + SQLite

6 AI Employees:
- Luna (Claude Sonnet) - CEO & Product Manager
- Aria (Claude Haiku) - Copywriter & Marketing  
- Nova (Claude Haiku) - Customer Support
- Zara (Claude Haiku) - Pricing & Analytics
- Iris (Claude Haiku) - Social Media Manager
- Vega (Claude Sonnet) - Supply Chain & Logistics

Brands: Nike, Anthropic, Generic
"""

import asyncio
import json
import random
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="AI Drop Store", version="2.0")
PORT = int(os.environ.get("PORT", 8020))

BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─── AI Employees ───
AI_EMPLOYEES = {
    "luna": {"name": "Luna", "role": "CEO & Product Manager", "model": "claude-sonnet-4-20250514",
             "ollama_model": "llama3.2:3b", "avatar": "👩‍💼", "color": "#8B5CF6",
             "specialty": "curadoria de produtos e estratégia"},
    "aria": {"name": "Aria", "role": "Copywriter & Marketing", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "gemma2:2b", "avatar": "✍️", "color": "#EC4899",
             "specialty": "textos persuasivos e campanhas"},
    "nova": {"name": "Nova", "role": "Suporte ao Cliente", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "phi3:mini", "avatar": "🎧", "color": "#06B6D4",
             "specialty": "atendimento e resolução de problemas"},
    "zara": {"name": "Zara", "role": "Pricing & Analytics", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "qwen2:1.5b", "avatar": "📊", "color": "#F59E0B",
             "specialty": "precificação e análise de dados"},
    "iris": {"name": "Iris", "role": "Social Media Manager", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "tinyllama", "avatar": "📱", "color": "#10B981",
             "specialty": "redes sociais e engajamento"},
    "vega": {"name": "Vega", "role": "Supply Chain & Logistics", "model": "claude-sonnet-4-20250514",
             "ollama_model": "mistral:7b-instruct", "avatar": "🚚", "color": "#EF4444",
             "specialty": "logística e fornecedores"},
}

# ─── Categories ───
CATEGORIES = [
    {"id": "nike", "name": "Nike", "icon": "👟", "emoji": "🏃"},
    {"id": "tech", "name": "Tecnologia", "icon": "💻", "emoji": "🔌"},
    {"id": "beauty", "name": "Beleza & Saúde", "icon": "💄", "emoji": "✨"},
    {"id": "home", "name": "Casa & Decoração", "icon": "🏠", "emoji": "🛋️"},
    {"id": "fashion", "name": "Moda & Acessórios", "icon": "👗", "emoji": "👜"},
    {"id": "fitness", "name": "Fitness & Esporte", "icon": "💪", "emoji": "🏋️"},
    {"id": "pets", "name": "Pets", "icon": "🐾", "emoji": "🐕"},
    {"id": "ai", "name": "AI & Anthropic", "icon": "🤖", "emoji": "🧠"},
]

# In-memory cache (loaded from SQL at startup)
PRODUCTS = []
ORDERS = []
AI_ACTIVITY_LOG = []
STORE_STATS = {
    "total_revenue": 0, "orders_count": 0, "visitors": 0,
    "ai_decisions": 0, "products_curated": 0,
}

# ─── AI Helpers ───

async def ask_claude(prompt: str, max_tokens: int = 300) -> str:
    """Ask Anthropic Claude API"""
    if not ANTHROPIC_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("https://api.anthropic.com/v1/messages", json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }, headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            })
            if r.status_code == 200:
                data = r.json()
                return data["content"][0]["text"].strip()
    except Exception:
        pass
    return ""

async def ask_ollama(model: str, prompt: str, max_tokens: int = 300) -> str:
    """Ask Ollama local"""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{OLLAMA}/api/generate", json={
                "model": model, "prompt": prompt, "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.8}
            })
            if r.status_code == 200:
                return r.json().get("response", "").strip()
    except Exception:
        pass
    return ""

async def ask_ai(employee_key: str, prompt: str, max_tokens: int = 300) -> str:
    """Try Claude first, fallback to Ollama"""
    emp = AI_EMPLOYEES[employee_key]
    # Try Anthropic Claude
    result = await ask_claude(prompt, max_tokens)
    if result:
        return result
    # Fallback to Ollama
    result = await ask_ollama(emp["ollama_model"], prompt, max_tokens)
    return result

def log_ai(ai_name: str, action: str, detail: str):
    AI_ACTIVITY_LOG.append({
        "time": datetime.now().isoformat(),
        "ai": ai_name, "action": action, "detail": detail[:200]
    })
    if len(AI_ACTIVITY_LOG) > 500:
        AI_ACTIVITY_LOG.pop(0)
    STORE_STATS["ai_decisions"] += 1

def make_image_url(name: str, cat: str) -> str:
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    # Dark backgrounds for Nike-style white layout
    cat_colors = {
        "nike": "111111", "ai": "2D1B69", "tech": "1a1a2e",
        "beauty": "4A0E2E", "home": "1B3A2D", "fashion": "2E1A1A",
        "fitness": "1A2E3A", "pets": "3A2E1A",
    }
    color = cat_colors.get(cat, "111111")
    label = name[:18].replace(' ', '+')
    return f"https://placehold.co/400x400/{color}/ffffff?text={label}"

# ─── Product Catalog ───
INITIAL_PRODUCTS = [
    # NIKE
    {"name": "Nike Air Max 90", "cat": "nike", "brand": "Nike", "base_price": 599.90, "supplier_price": 180.00},
    {"name": "Nike Air Force 1 Low", "cat": "nike", "brand": "Nike", "base_price": 549.90, "supplier_price": 165.00},
    {"name": "Nike Dunk Low Panda", "cat": "nike", "brand": "Nike", "base_price": 649.90, "supplier_price": 195.00},
    {"name": "Nike Air Jordan 1 Mid", "cat": "nike", "brand": "Nike", "base_price": 799.90, "supplier_price": 240.00},
    {"name": "Nike Revolution 7", "cat": "nike", "brand": "Nike", "base_price": 349.90, "supplier_price": 105.00},
    {"name": "Nike Blazer Mid 77", "cat": "nike", "brand": "Nike", "base_price": 499.90, "supplier_price": 150.00},
    {"name": "Nike Cortez Classic", "cat": "nike", "brand": "Nike", "base_price": 449.90, "supplier_price": 135.00},
    {"name": "Nike Pegasus 41", "cat": "nike", "brand": "Nike", "base_price": 699.90, "supplier_price": 210.00},
    {"name": "Camiseta Nike Dri-FIT", "cat": "nike", "brand": "Nike", "base_price": 149.90, "supplier_price": 35.00},
    {"name": "Shorts Nike Flex", "cat": "nike", "brand": "Nike", "base_price": 129.90, "supplier_price": 30.00},
    {"name": "Mochila Nike Brasilia", "cat": "nike", "brand": "Nike", "base_price": 199.90, "supplier_price": 55.00},
    {"name": "Boné Nike Club Cap", "cat": "nike", "brand": "Nike", "base_price": 99.90, "supplier_price": 22.00},
    # AI & ANTHROPIC
    {"name": "Curso IA com Claude API", "cat": "ai", "brand": "Anthropic", "base_price": 297.00, "supplier_price": 50.00},
    {"name": "Pack Prompts Anthropic Pro", "cat": "ai", "brand": "Anthropic", "base_price": 147.00, "supplier_price": 20.00},
    {"name": "Template Chatbot Claude", "cat": "ai", "brand": "Anthropic", "base_price": 97.00, "supplier_price": 15.00},
    {"name": "Ebook: IA para Negócios", "cat": "ai", "brand": "Anthropic", "base_price": 49.90, "supplier_price": 5.00},
    {"name": "API Credits Claude Haiku", "cat": "ai", "brand": "Anthropic", "base_price": 197.00, "supplier_price": 80.00},
    {"name": "Automação MCP Server Kit", "cat": "ai", "brand": "Anthropic", "base_price": 397.00, "supplier_price": 60.00},
    # TECH
    {"name": "Fone Bluetooth Pro Max", "cat": "tech", "brand": "", "base_price": 29.90, "supplier_price": 8.50},
    {"name": "Ring Light LED 26cm", "cat": "tech", "brand": "", "base_price": 49.90, "supplier_price": 15.00},
    {"name": "Smartwatch Fitness Y68", "cat": "tech", "brand": "", "base_price": 79.90, "supplier_price": 22.00},
    {"name": "Hub USB-C 7 em 1", "cat": "tech", "brand": "", "base_price": 89.90, "supplier_price": 25.00},
    {"name": "Mini Projetor LED", "cat": "tech", "brand": "", "base_price": 199.90, "supplier_price": 65.00},
    # BEAUTY
    {"name": "Sérum Vitamina C 30ml", "cat": "beauty", "brand": "", "base_price": 39.90, "supplier_price": 9.00},
    {"name": "Massageador Facial Jade", "cat": "beauty", "brand": "", "base_price": 34.90, "supplier_price": 7.50},
    {"name": "Kit Pincéis Maquiagem 12pcs", "cat": "beauty", "brand": "", "base_price": 44.90, "supplier_price": 11.00},
    # HOME
    {"name": "Luminária LED Lua 3D", "cat": "home", "brand": "", "base_price": 69.90, "supplier_price": 20.00},
    {"name": "Umidificador Ultrassônico", "cat": "home", "brand": "", "base_price": 59.90, "supplier_price": 17.00},
    # FASHION
    {"name": "Bolsa Crossbody Minimalista", "cat": "fashion", "brand": "", "base_price": 54.90, "supplier_price": 15.00},
    {"name": "Óculos de Sol Polarizado", "cat": "fashion", "brand": "", "base_price": 39.90, "supplier_price": 8.00},
    {"name": "Relógio Analógico Vintage", "cat": "fashion", "brand": "", "base_price": 69.90, "supplier_price": 19.00},
    # FITNESS
    {"name": "Corda de Pular Speed Rope", "cat": "fitness", "brand": "", "base_price": 29.90, "supplier_price": 6.00},
    {"name": "Faixa Elástica Kit 5 Níveis", "cat": "fitness", "brand": "", "base_price": 39.90, "supplier_price": 10.00},
    {"name": "Garrafa Motivacional 2L", "cat": "fitness", "brand": "", "base_price": 34.90, "supplier_price": 8.00},
    # PETS
    {"name": "Bebedouro Fonte Automática", "cat": "pets", "brand": "", "base_price": 79.90, "supplier_price": 24.00},
    {"name": "Brinquedo Interativo Gato", "cat": "pets", "brand": "", "base_price": 29.90, "supplier_price": 7.00},
    {"name": "Coleira GPS Rastreador", "cat": "pets", "brand": "", "base_price": 129.90, "supplier_price": 42.00},
]

async def gen_description(product: dict) -> str:
    brand_hint = f" da marca {product.get('brand', '')}." if product.get("brand") else "."
    prompt = f"Escreva uma descrição curta e persuasiva (máx 2 frases) para vender: {product['name']}{brand_hint} Categoria: {product['cat']}. Use gatilhos mentais. Responda APENAS a descrição."
    desc = await ask_ai("aria", prompt, 150)
    if not desc or len(desc) < 10:
        fallbacks = {
            "nike": "Estilo icônico Nike com conforto e performance. Just Do It - tecnologia de ponta para os seus pés!",
            "ai": "Domine a Inteligência Artificial com as ferramentas mais avançadas da Anthropic. O futuro é agora!",
            "tech": "Tecnologia de ponta para simplificar seu dia a dia. Qualidade premium!",
            "beauty": "Realce sua beleza natural. Resultados visíveis desde a primeira aplicação!",
            "home": "Transforme sua casa num ambiente dos sonhos. Design moderno!",
            "fashion": "Estilo e elegância para todas as ocasiões!",
            "fitness": "Supere seus limites com o equipamento certo!",
            "pets": "Seu pet merece o melhor! Conforto e diversão garantidos.",
        }
        desc = fallbacks.get(product["cat"], "Produto incrível com qualidade garantida!")
    return desc

def calc_price(product: dict) -> dict:
    base = product["base_price"]
    supplier = product["supplier_price"]
    factor = random.choice([0.95, 0.97, 1.0, 1.0, 1.0, 1.03, 1.05, 1.10])
    price = round(base * factor, 2)
    if price < supplier * 1.5:
        price = round(supplier * 2.5, 2)
    old_price = round(price * random.uniform(1.2, 1.6), 2)
    discount = round((1 - price / old_price) * 100)
    margin = round((price - supplier) / price * 100, 1)
    return {"price": price, "old_price": old_price, "discount": discount, "margin": margin}

# ─── Database Import ───
from app.database import (
    init_db, insert_product, get_all_products, get_product, update_product,
    insert_order, get_orders, count_orders, log_activity, get_activity,
    get_all_stats, inc_stat, product_count, insert_chat, db_status, has_pg
)

# ─── Telegram Notifications ───
from app.telegram_notify import (
    notify_new_order, notify_price_change, notify_stock_low,
    notify_new_customer, notify_daily_summary, register_chat, send_telegram
)

# ─── Customer Auth ───
from app.auth import (
    init_auth_db, register_customer, login_customer, get_customer,
    get_customer_orders, save_customer_order, update_customer_profile,
    decode_token, customer_count
)

# ─── Multi-Agent System ───
from app.multi_agent import (
    init_multi_agent, start_all_agents, get_multi_agent_data,
    get_agent_status, bus, kb
)

async def initialize_catalog():
    """Build catalog with AI descriptions, save to SQLite"""
    await init_db()
    await init_auth_db()
    
    existing = await product_count()
    if existing > 0:
        log_ai("Luna", "STARTUP", f"Catálogo já existe com {existing} produtos no SQL")
        # Load into memory
        prods = await get_all_products()
        PRODUCTS.clear()
        PRODUCTS.extend(prods)
        stats = await get_all_stats()
        STORE_STATS.update({k: v for k, v in stats.items() if k in STORE_STATS})
        asyncio.create_task(ai_background_loop())
        # Start multi-agent system
        init_multi_agent(PRODUCTS, ORDERS, STORE_STATS, AI_ACTIVITY_LOG,
                         ask_ai, log_ai, log_activity, inc_stat, update_product,
                         {"stock_low": notify_stock_low, "new_order": notify_new_order})
        await start_all_agents()
        log_ai("Sistema", "MULTI-AGENT", "🤖 6 IAs + decisões colaborativas ativas!")
        return
    
    log_ai("Luna", "STARTUP", "Iniciando curadoria do catálogo - Nike + Anthropic + 37 produtos")
    await log_activity("Luna", "STARTUP", "Iniciando curadoria com Claude AI + Ollama")
    
    for p in INITIAL_PRODUCTS:
        pricing = calc_price(p)
        desc = await gen_description(p)
        
        pid = hashlib.md5(p["name"].encode()).hexdigest()[:8]
        sold = random.randint(50, 2000)
        rating = round(random.uniform(4.0, 5.0), 1)
        
        product = {
            "id": pid,
            "name": p["name"],
            "category": p["cat"],
            "brand": p.get("brand", ""),
            "description": desc,
            "price": pricing["price"],
            "old_price": pricing["old_price"],
            "discount": pricing["discount"],
            "margin": pricing["margin"],
            "supplier_price": p["supplier_price"],
            "image": make_image_url(p["name"], p["cat"]),
            "sold": sold,
            "rating": rating,
            "reviews_count": random.randint(10, sold // 2),
            "stock": random.randint(5, 100),
            "shipping_days": random.randint(3, 15),
            "created_by": "Luna",
            "description_by": "Aria (Claude)" if ANTHROPIC_KEY else "Aria (Ollama)",
            "price_by": "Zara",
        }
        PRODUCTS.append(product)
        await insert_product(product)
        await inc_stat("products_curated")
        STORE_STATS["products_curated"] += 1
    
    n = len(PRODUCTS)
    log_ai("Luna", "CATALOG", f"Catálogo criado: {n} produtos (Nike + Anthropic + Tech)")
    log_ai("Aria", "COPY", f"Descrições escritas para {n} produtos via {'Claude' if ANTHROPIC_KEY else 'Ollama'}")
    log_ai("Zara", "PRICING", f"Preços otimizados para {n} produtos")
    await log_activity("Luna", "CATALOG", f"{n} produtos inseridos no SQLite")
    await log_activity("Aria", "COPY", f"Descrições via {'Anthropic Claude' if ANTHROPIC_KEY else 'Ollama'}")

    asyncio.create_task(ai_background_loop())
    # Start multi-agent system
    init_multi_agent(PRODUCTS, ORDERS, STORE_STATS, AI_ACTIVITY_LOG,
                     ask_ai, log_ai, log_activity, inc_stat, update_product,
                     {"stock_low": notify_stock_low, "new_order": notify_new_order})
    await start_all_agents()
    log_ai("Sistema", "MULTI-AGENT", "🤖 6 IAs + decisões colaborativas ativas!")

async def ai_background_loop():
    while True:
        await asyncio.sleep(60)
        try:
            if PRODUCTS:
                p = random.choice(PRODUCTS)
                old = p["price"]
                change = random.uniform(-0.05, 0.05)
                p["price"] = round(p["price"] * (1 + change), 2)
                if p["price"] < p["supplier_price"] * 1.5:
                    p["price"] = round(p["supplier_price"] * 2.5, 2)
                p["old_price"] = round(p["price"] * random.uniform(1.2, 1.5), 2)
                p["discount"] = round((1 - p["price"] / p["old_price"]) * 100)
                await update_product(p["id"], price=p["price"], old_price=p["old_price"], discount=p["discount"])
                log_ai("Zara", "PRICE_SQL", f"{p['name']}: R${old:.2f} → R${p['price']:.2f}")
            
            STORE_STATS["visitors"] += random.randint(5, 50)
            await inc_stat("visitors", random.randint(5, 50))
            
            if random.random() < 0.3 and PRODUCTS:
                prod = random.choice(PRODUCTS)
                qty = random.randint(1, 3)
                oid = f"ORD-{await count_orders() + 1:04d}"
                order = {
                    "id": oid, "product": prod["name"], "product_id": prod["id"],
                    "qty": qty, "total": round(prod["price"] * qty, 2),
                    "profit": round((prod["price"] - prod["supplier_price"]) * qty, 2),
                    "status": random.choice(["Processando", "Enviado", "Em trânsito"]),
                    "customer": f"Cliente #{random.randint(1000, 9999)}",
                    "handled_by": "Vega",
                }
                await insert_order(order)
                ORDERS.append(order)
                STORE_STATS["orders_count"] += 1
                STORE_STATS["total_revenue"] += order["total"]
                await inc_stat("orders_count")
                await inc_stat("total_revenue", order["total"])
                prod["sold"] += qty
                prod["stock"] = max(0, prod["stock"] - qty)
                await update_product(prod["id"], sold=prod["sold"], stock=prod["stock"])
                log_ai("Vega", "ORDER_SQL", f"Pedido {oid}: {qty}x {prod['name']} = R${order['total']:.2f}")
                # Telegram notification
                await notify_new_order(order, prod)
                if prod["stock"] < 5:
                    await notify_stock_low(prod["name"], prod["stock"])
        except Exception:
            pass

@app.on_event("startup")
async def startup():
    asyncio.create_task(initialize_catalog())

# ─── Routes ───

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, cat: Optional[str] = None, q: Optional[str] = None, sort: Optional[str] = None):
    STORE_STATS["visitors"] += 1
    products = PRODUCTS[:]
    
    if cat:
        products = [p for p in products if p["category"] == cat]
    if q:
        ql = q.lower()
        products = [p for p in products if ql in p["name"].lower() or ql in p.get("description", "").lower() or ql in p.get("brand", "").lower()]
    
    sort_map = {
        "price_asc": lambda x: x["price"],
        "price_desc": lambda x: -x["price"],
        "popular": lambda x: -x["sold"],
        "rating": lambda x: -x["rating"],
        "discount": lambda x: -x["discount"],
    }
    if sort in sort_map:
        products.sort(key=sort_map[sort])
    
    return templates.TemplateResponse("store.html", {
        "request": request, "products": products, "categories": CATEGORIES,
        "current_cat": cat, "search_query": q or "", "current_sort": sort or "",
        "stats": STORE_STATS, "ai_employees": AI_EMPLOYEES,
        "has_anthropic": bool(ANTHROPIC_KEY),
    })

@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return HTMLResponse("<h1>Produto não encontrado</h1>", status_code=404)
    related = [p for p in PRODUCTS if p["category"] == product["category"] and p["id"] != product_id][:4]
    return templates.TemplateResponse("product.html", {
        "request": request, "product": product, "related": related,
        "ai_employees": AI_EMPLOYEES, "stats": STORE_STATS,
    })

@app.post("/api/buy/{product_id}")
async def buy_product(request: Request, product_id: str, qty: int = 1):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return JSONResponse({"error": "Produto não encontrado"}, 404)
    if product["stock"] < qty:
        return JSONResponse({"error": "Estoque insuficiente"}, 400)
    
    oid = f"ORD-{await count_orders() + 1:04d}"
    order = {
        "id": oid, "product": product["name"], "product_id": product["id"],
        "qty": qty, "total": round(product["price"] * qty, 2),
        "profit": round((product["price"] - product["supplier_price"]) * qty, 2),
        "status": "Processando",
        "customer": f"Cliente #{random.randint(1000, 9999)}",
        "handled_by": "Vega",
    }
    await insert_order(order)
    ORDERS.append(order)
    STORE_STATS["orders_count"] += 1
    STORE_STATS["total_revenue"] += order["total"]
    await inc_stat("orders_count")
    await inc_stat("total_revenue", order["total"])
    product["sold"] += qty
    product["stock"] -= qty
    await update_product(product["id"], sold=product["sold"], stock=product["stock"])
    
    log_ai("Vega", "ORDER", f"Pedido {oid}: {qty}x {product['name']}")
    log_ai("Nova", "SUPPORT", f"Confirmação enviada ao {order['customer']}")
    await log_activity("Vega", "ORDER", f"Pedido {oid} salvo no SQLite")

    # Telegram notification
    await notify_new_order(order, product)
    if product["stock"] < 5:
        await notify_stock_low(product["name"], product["stock"])

    # Save to customer account if logged in
    token = request.cookies.get("token") if hasattr(request, 'cookies') else None
    if token:
        user = decode_token(token)
        if user:
            await save_customer_order(user["id"], order)

    return JSONResponse({
        "success": True, "order": order,
        "message": f"Pedido {oid} realizado! IA Vega processando envio."
    })

@app.get("/api/chat")
async def chat_support(message: str = Query(...)):
    prompt = f"""Você é Nova, assistente de suporte da AI Drop Store (loja dropshipping com Nike, produtos Anthropic/IA, tech, beleza, etc).
Responda em português, amigável, máx 3 frases.
Entrega: 3-15 dias. Pagamento: PIX, cartão, boleto.
Pergunta: {message}"""
    
    response = await ask_ai("nova", prompt, 200)
    if not response:
        responses = [
            "Olá! Como posso ajudar? Temos Nike, produtos de IA e muito mais! 😊",
            "Oi! Temos as melhores ofertas em Nike e tecnologia IA!",
            "Bem-vindo(a)! Posso ajudar com produtos, entregas ou pagamentos.",
        ]
        response = random.choice(responses)
    
    await insert_chat(message, response, "Nova")
    log_ai("Nova", "CHAT", f"'{message[:50]}...'")
    return JSONResponse({"response": response, "ai": "Nova", "role": "Suporte ao Cliente"})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    top_products = sorted(PRODUCTS, key=lambda x: x["sold"], reverse=True)[:10]
    recent_orders = (await get_orders(20)) if await count_orders() > 0 else ORDERS[-20:][::-1]
    recent_activity = AI_ACTIVITY_LOG[-30:][::-1]
    db_activity = await get_activity(30)
    
    total_profit = sum(o.get("profit", 0) for o in ORDERS)
    avg_margin = sum(p["margin"] for p in PRODUCTS) / len(PRODUCTS) if PRODUCTS else 0
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "stats": STORE_STATS,
        "top_products": top_products, "recent_orders": recent_orders,
        "recent_activity": recent_activity, "db_activity": db_activity,
        "ai_employees": AI_EMPLOYEES,
        "total_profit": round(total_profit, 2),
        "avg_margin": round(avg_margin, 1),
        "total_products": len(PRODUCTS),
        "categories": CATEGORIES,
        "has_anthropic": bool(ANTHROPIC_KEY),
        "has_pg": has_pg(),
        "db_info": await db_status(),
        "db_size": f"{Path(BASE.parent / 'store.db').stat().st_size / 1024:.1f} KB" if Path(BASE.parent / 'store.db').exists() else "0 KB",
    })

@app.get("/api/stats")
async def get_stats_api():
    dbs = await db_status()
    return JSONResponse({
        "stats": STORE_STATS,
        "products_count": len(PRODUCTS),
        "orders_count": len(ORDERS),
        "recent_activity": AI_ACTIVITY_LOG[-10:][::-1],
        "engine": "Anthropic Claude" if ANTHROPIC_KEY else "Ollama Local",
        "database": dbs,
    })

@app.get("/api/ai-activity")
async def get_ai_activity():
    return JSONResponse({"activity": AI_ACTIVITY_LOG[-50:][::-1]})

# ─── MULTI-AGENT ROUTES ───

@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    data = get_multi_agent_data()
    return templates.TemplateResponse("agents.html", {
        "request": request, "ai_employees": AI_EMPLOYEES,
        "stats": STORE_STATS, "agent_data": data,
        "messages": data["messages"][:40],
        "decisions": data["decisions"][:15],
        "trends": data["trends"][:15],
        "facts": data["facts"],
        "performance": data["performance"],
        "has_anthropic": bool(ANTHROPIC_KEY),
    })

@app.get("/api/agents")
async def api_agents():
    return JSONResponse(get_multi_agent_data())

@app.get("/api/agents/messages")
async def api_agent_messages(agent: Optional[str] = None, limit: int = 50):
    if agent:
        msgs = bus.get_for(agent, limit)
    else:
        msgs = bus.get_all(limit)
    return JSONResponse({"messages": msgs})

@app.get("/api/agents/decisions")
async def api_agent_decisions():
    return JSONResponse({"decisions": kb.decisions[-30:][::-1]})

@app.get("/api/agents/knowledge")
async def api_agent_knowledge():
    return JSONResponse({
        "facts": {k: v for k, v in kb.facts.items()},
        "trends": kb.trends[-30:][::-1],
        "performance": kb.performance,
    })

# ─── AUTH ROUTES (Customer Accounts) ───

@app.post("/api/register")
async def api_register(request: Request):
    data = await request.json()
    result = await register_customer(data.get("name", ""), data.get("email", ""), data.get("password", ""))
    if result.get("success"):
        await notify_new_customer(data["name"], data["email"])
        log_ai("Nova", "REGISTER", f"Novo cliente: {data['email']}")
    return JSONResponse(result)

@app.post("/api/login")
async def api_login(request: Request):
    data = await request.json()
    result = await login_customer(data.get("email", ""), data.get("password", ""))
    return JSONResponse(result)

@app.get("/api/me")
async def api_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = decode_token(token)
    if not user:
        return JSONResponse({"error": "Não autenticado"}, 401)
    customer = await get_customer(user["id"])
    orders = await get_customer_orders(user["id"])
    return JSONResponse({"customer": customer, "orders": orders})

@app.get("/conta", response_class=HTMLResponse)
async def account_page(request: Request):
    return templates.TemplateResponse("account.html", {
        "request": request, "ai_employees": AI_EMPLOYEES,
    })

# ─── TELEGRAM ROUTES ───

@app.post("/api/telegram/register")
async def telegram_register(request: Request):
    data = await request.json()
    chat_id = data.get("chat_id", "")
    if chat_id:
        register_chat(chat_id)
        await send_telegram(f"✅ Chat {chat_id} registrado para notificações da AI Drop Store!", chat_id)
        return JSONResponse({"success": True, "message": f"Chat {chat_id} registrado"})
    return JSONResponse({"error": "chat_id necessário"}, 400)

@app.post("/api/telegram/test")
async def telegram_test():
    ok = await send_telegram("🧪 <b>Teste de notificação</b>\n\nAI Drop Store está conectada ao Telegram!")
    return JSONResponse({"success": ok})

@app.get("/api/telegram/summary")
async def telegram_summary():
    top = sorted(PRODUCTS, key=lambda x: x["sold"], reverse=True)[:5]
    ok = await notify_daily_summary(STORE_STATS, top)
    return JSONResponse({"success": ok})

# ─── SEO ROUTES ───

@app.get("/sitemap.xml")
async def sitemap():
    base = "https://ai-drop-store.onrender.com"
    urls = [f"<url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    urls.append(f"<url><loc>{base}/dashboard</loc><changefreq>hourly</changefreq><priority>0.8</priority></url>")
    for cat in CATEGORIES:
        urls.append(f"<url><loc>{base}/?cat={cat['id']}</loc><changefreq>daily</changefreq><priority>0.9</priority></url>")
    for p in PRODUCTS:
        urls.append(f"<url><loc>{base}/product/{p['id']}</loc><changefreq>daily</changefreq><priority>0.7</priority></url>")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(urls)}
</urlset>"""
    return HTMLResponse(content=xml, media_type="application/xml")

@app.get("/robots.txt")
async def robots():
    return HTMLResponse(content="""User-agent: *
Allow: /
Sitemap: https://ai-drop-store.onrender.com/sitemap.xml

User-agent: Googlebot
Allow: /
Crawl-delay: 1
""", media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
