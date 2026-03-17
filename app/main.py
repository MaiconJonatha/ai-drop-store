"""
AI Dropshipping Store - Loja 100% gerida por IAs
Port: 8020

Powered by: Anthropic Claude + Ollama (fallback) + SQLite

6 AI Employees:
- Luna (Claude Sonnet) - CEO & Product Manager
- Aria (Claude Haiku) - Copywriter & Marketing  
- Nova (Claude Haiku) - Customer Support + WhatsApp Bot
- Zara (Claude Haiku) - Pricing & Analytics
- Iris (Claude Haiku) - Social Media Manager (Instagram/TikTok/Twitter)
- Vega (Claude Sonnet) - Supply Chain & Logistics

Features: Nike + Anthropic + 80+ Products, PWA, WhatsApp Bot, Email Marketing,
         Social Media Auto-posting, Advanced Dashboard, Google Analytics
"""

import asyncio
import json
import random
import hashlib
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="AI Drop Store", version="3.0")
PORT = int(os.environ.get("PORT", 8020))

BASE = Path(__file__).parent
static_dir = BASE / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GA_MEASUREMENT_ID = os.environ.get("GA_MEASUREMENT_ID", "G-XXXXXXXXXX")

# ─── AI Employees ───
AI_EMPLOYEES = {
    "luna": {"name": "Luna", "role": "CEO & Product Manager", "model": "claude-sonnet-4-20250514",
             "ollama_model": "llama3.2:3b", "avatar": "👩‍💼", "color": "#8B5CF6",
             "specialty": "curadoria de produtos e estratégia"},
    "aria": {"name": "Aria", "role": "Copywriter & Marketing", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "gemma2:2b", "avatar": "✍️", "color": "#EC4899",
             "specialty": "textos persuasivos e campanhas"},
    "nova": {"name": "Nova", "role": "Suporte ao Cliente + WhatsApp", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "phi3:mini", "avatar": "🎧", "color": "#06B6D4",
             "specialty": "atendimento 24/7 via chat e WhatsApp"},
    "zara": {"name": "Zara", "role": "Pricing & Analytics", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "qwen2:1.5b", "avatar": "📊", "color": "#F59E0B",
             "specialty": "precificação dinâmica e análise de dados"},
    "iris": {"name": "Iris", "role": "Social Media Manager", "model": "claude-haiku-4-5-20251001",
             "ollama_model": "tinyllama", "avatar": "📱", "color": "#10B981",
             "specialty": "Instagram, TikTok e Twitter automatizados"},
    "vega": {"name": "Vega", "role": "Supply Chain & Logistics", "model": "claude-sonnet-4-20250514",
             "ollama_model": "mistral:7b-instruct", "avatar": "🚚", "color": "#EF4444",
             "specialty": "logística, fornecedores e rastreamento"},
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
    {"id": "gaming", "name": "Games & Geek", "icon": "🎮", "emoji": "🕹️"},
    {"id": "food", "name": "Alimentos & Suplementos", "icon": "🥤", "emoji": "💊"},
]

# In-memory cache
PRODUCTS = []
ORDERS = []
AI_ACTIVITY_LOG = []
STORE_STATS = {
    "total_revenue": 0, "orders_count": 0, "visitors": 0,
    "ai_decisions": 0, "products_curated": 0,
}

# ─── AI Helpers ───

async def ask_claude(prompt: str, max_tokens: int = 300) -> str:
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
                return r.json()["content"][0]["text"].strip()
    except Exception:
        pass
    return ""

async def ask_ollama(model: str, prompt: str, max_tokens: int = 300) -> str:
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
    emp = AI_EMPLOYEES[employee_key]
    result = await ask_claude(prompt, max_tokens)
    if result:
        return result
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
    cat_colors = {
        "nike": "111111", "ai": "2D1B69", "tech": "1a1a2e",
        "beauty": "4A0E2E", "home": "1B3A2D", "fashion": "2E1A1A",
        "fitness": "1A2E3A", "pets": "3A2E1A", "gaming": "1A1A3A",
        "food": "2E3A1A",
    }
    color = cat_colors.get(cat, "111111")
    label = name[:18].replace(' ', '+')
    return f"https://placehold.co/400x400/{color}/ffffff?text={label}"

# ─── MEGA Product Catalog (80+ products with real suppliers) ───
INITIAL_PRODUCTS = [
    # ═══ NIKE (15 products) - Supplier: CJ Dropshipping / AliExpress ═══
    {"name": "Nike Air Max 90", "cat": "nike", "brand": "Nike", "base_price": 599.90, "supplier_price": 180.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Air Force 1 Low", "cat": "nike", "brand": "Nike", "base_price": 549.90, "supplier_price": 165.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Dunk Low Panda", "cat": "nike", "brand": "Nike", "base_price": 649.90, "supplier_price": 195.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Air Jordan 1 Mid", "cat": "nike", "brand": "Nike", "base_price": 799.90, "supplier_price": 240.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Revolution 7", "cat": "nike", "brand": "Nike", "base_price": 349.90, "supplier_price": 105.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Blazer Mid 77", "cat": "nike", "brand": "Nike", "base_price": 499.90, "supplier_price": 150.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Cortez Classic", "cat": "nike", "brand": "Nike", "base_price": 449.90, "supplier_price": 135.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Pegasus 41", "cat": "nike", "brand": "Nike", "base_price": 699.90, "supplier_price": 210.00, "supplier": "CJ Dropshipping"},
    {"name": "Camiseta Nike Dri-FIT", "cat": "nike", "brand": "Nike", "base_price": 149.90, "supplier_price": 35.00, "supplier": "CJ Dropshipping"},
    {"name": "Shorts Nike Flex", "cat": "nike", "brand": "Nike", "base_price": 129.90, "supplier_price": 30.00, "supplier": "CJ Dropshipping"},
    {"name": "Mochila Nike Brasilia", "cat": "nike", "brand": "Nike", "base_price": 199.90, "supplier_price": 55.00, "supplier": "CJ Dropshipping"},
    {"name": "Boné Nike Club Cap", "cat": "nike", "brand": "Nike", "base_price": 99.90, "supplier_price": 22.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Air Max 270", "cat": "nike", "brand": "Nike", "base_price": 679.90, "supplier_price": 200.00, "supplier": "CJ Dropshipping"},
    {"name": "Nike Vapormax Flyknit", "cat": "nike", "brand": "Nike", "base_price": 899.90, "supplier_price": 280.00, "supplier": "CJ Dropshipping"},
    {"name": "Meias Nike Everyday 3 Pares", "cat": "nike", "brand": "Nike", "base_price": 59.90, "supplier_price": 12.00, "supplier": "CJ Dropshipping"},

    # ═══ AI & ANTHROPIC (8 products) - Digital, supplier: self ═══
    {"name": "Curso IA com Claude API", "cat": "ai", "brand": "Anthropic", "base_price": 297.00, "supplier_price": 50.00, "supplier": "Digital"},
    {"name": "Pack Prompts Anthropic Pro", "cat": "ai", "brand": "Anthropic", "base_price": 147.00, "supplier_price": 20.00, "supplier": "Digital"},
    {"name": "Template Chatbot Claude", "cat": "ai", "brand": "Anthropic", "base_price": 97.00, "supplier_price": 15.00, "supplier": "Digital"},
    {"name": "Ebook: IA para Negócios", "cat": "ai", "brand": "Anthropic", "base_price": 49.90, "supplier_price": 5.00, "supplier": "Digital"},
    {"name": "API Credits Claude Haiku", "cat": "ai", "brand": "Anthropic", "base_price": 197.00, "supplier_price": 80.00, "supplier": "Digital"},
    {"name": "Automação MCP Server Kit", "cat": "ai", "brand": "Anthropic", "base_price": 397.00, "supplier_price": 60.00, "supplier": "Digital"},
    {"name": "Curso Machine Learning Python", "cat": "ai", "brand": "Anthropic", "base_price": 247.00, "supplier_price": 40.00, "supplier": "Digital"},
    {"name": "Pack 500 Prompts ChatGPT+Claude", "cat": "ai", "brand": "Anthropic", "base_price": 67.00, "supplier_price": 8.00, "supplier": "Digital"},

    # ═══ TECH (12 products) - Supplier: AliExpress / Shein ═══
    {"name": "Fone Bluetooth Pro Max", "cat": "tech", "brand": "", "base_price": 29.90, "supplier_price": 8.50, "supplier": "AliExpress"},
    {"name": "Ring Light LED 26cm", "cat": "tech", "brand": "", "base_price": 49.90, "supplier_price": 15.00, "supplier": "AliExpress"},
    {"name": "Smartwatch Fitness Y68", "cat": "tech", "brand": "", "base_price": 79.90, "supplier_price": 22.00, "supplier": "AliExpress"},
    {"name": "Hub USB-C 7 em 1", "cat": "tech", "brand": "", "base_price": 89.90, "supplier_price": 25.00, "supplier": "AliExpress"},
    {"name": "Mini Projetor LED", "cat": "tech", "brand": "", "base_price": 199.90, "supplier_price": 65.00, "supplier": "AliExpress"},
    {"name": "Teclado Mecânico RGB", "cat": "tech", "brand": "", "base_price": 159.90, "supplier_price": 45.00, "supplier": "AliExpress"},
    {"name": "Mouse Gamer 12000 DPI", "cat": "tech", "brand": "", "base_price": 69.90, "supplier_price": 18.00, "supplier": "AliExpress"},
    {"name": "Webcam Full HD 1080p", "cat": "tech", "brand": "", "base_price": 119.90, "supplier_price": 35.00, "supplier": "AliExpress"},
    {"name": "Carregador Wireless 15W", "cat": "tech", "brand": "", "base_price": 44.90, "supplier_price": 12.00, "supplier": "AliExpress"},
    {"name": "Cabo USB-C Magnético 2m", "cat": "tech", "brand": "", "base_price": 24.90, "supplier_price": 5.50, "supplier": "AliExpress"},
    {"name": "Mini Drone com Câmera", "cat": "tech", "brand": "", "base_price": 249.90, "supplier_price": 78.00, "supplier": "AliExpress"},
    {"name": "Caixa de Som Bluetooth IP67", "cat": "tech", "brand": "", "base_price": 89.90, "supplier_price": 28.00, "supplier": "AliExpress"},

    # ═══ BEAUTY (8 products) - Supplier: Shein / AliExpress ═══
    {"name": "Sérum Vitamina C 30ml", "cat": "beauty", "brand": "", "base_price": 39.90, "supplier_price": 9.00, "supplier": "Shein"},
    {"name": "Massageador Facial Jade", "cat": "beauty", "brand": "", "base_price": 34.90, "supplier_price": 7.50, "supplier": "Shein"},
    {"name": "Kit Pincéis Maquiagem 12pcs", "cat": "beauty", "brand": "", "base_price": 44.90, "supplier_price": 11.00, "supplier": "Shein"},
    {"name": "Ácido Hialurônico Sérum", "cat": "beauty", "brand": "", "base_price": 49.90, "supplier_price": 10.00, "supplier": "Shein"},
    {"name": "Dermaroller Microagulhas", "cat": "beauty", "brand": "", "base_price": 29.90, "supplier_price": 6.00, "supplier": "AliExpress"},
    {"name": "Máscara LED Facial 7 Cores", "cat": "beauty", "brand": "", "base_price": 149.90, "supplier_price": 42.00, "supplier": "AliExpress"},
    {"name": "Kit Skincare Coreano 5 Steps", "cat": "beauty", "brand": "", "base_price": 89.90, "supplier_price": 25.00, "supplier": "AliExpress"},
    {"name": "Escova Facial Elétrica", "cat": "beauty", "brand": "", "base_price": 59.90, "supplier_price": 16.00, "supplier": "AliExpress"},

    # ═══ HOME (7 products) - Supplier: AliExpress / Shopee ═══
    {"name": "Luminária LED Lua 3D", "cat": "home", "brand": "", "base_price": 69.90, "supplier_price": 20.00, "supplier": "AliExpress"},
    {"name": "Umidificador Ultrassônico", "cat": "home", "brand": "", "base_price": 59.90, "supplier_price": 17.00, "supplier": "AliExpress"},
    {"name": "Câmera WiFi 360° Pet", "cat": "home", "brand": "", "base_price": 99.90, "supplier_price": 32.00, "supplier": "AliExpress"},
    {"name": "Aspirador Robô Smart", "cat": "home", "brand": "", "base_price": 399.90, "supplier_price": 120.00, "supplier": "AliExpress"},
    {"name": "Difusor Aromaterapia LED", "cat": "home", "brand": "", "base_price": 49.90, "supplier_price": 14.00, "supplier": "AliExpress"},
    {"name": "Cortina LED Cascata 3m", "cat": "home", "brand": "", "base_price": 39.90, "supplier_price": 10.00, "supplier": "AliExpress"},
    {"name": "Organizador Acrílico Makeup", "cat": "home", "brand": "", "base_price": 44.90, "supplier_price": 12.00, "supplier": "Shopee"},

    # ═══ FASHION (8 products) - Supplier: Shein / CJ Dropshipping ═══
    {"name": "Bolsa Crossbody Minimalista", "cat": "fashion", "brand": "", "base_price": 54.90, "supplier_price": 15.00, "supplier": "Shein"},
    {"name": "Óculos de Sol Polarizado", "cat": "fashion", "brand": "", "base_price": 39.90, "supplier_price": 8.00, "supplier": "AliExpress"},
    {"name": "Relógio Analógico Vintage", "cat": "fashion", "brand": "", "base_price": 69.90, "supplier_price": 19.00, "supplier": "AliExpress"},
    {"name": "Cinto Couro Ecológico", "cat": "fashion", "brand": "", "base_price": 34.90, "supplier_price": 8.00, "supplier": "Shein"},
    {"name": "Carteira Slim RFID Block", "cat": "fashion", "brand": "", "base_price": 44.90, "supplier_price": 11.00, "supplier": "AliExpress"},
    {"name": "Chapéu Bucket Hat Unissex", "cat": "fashion", "brand": "", "base_price": 29.90, "supplier_price": 6.50, "supplier": "Shein"},
    {"name": "Meia Invisível Kit 10 Pares", "cat": "fashion", "brand": "", "base_price": 24.90, "supplier_price": 5.00, "supplier": "AliExpress"},
    {"name": "Pulseira Aço Inox Magnética", "cat": "fashion", "brand": "", "base_price": 39.90, "supplier_price": 9.00, "supplier": "AliExpress"},

    # ═══ FITNESS (8 products) - Supplier: CJ Dropshipping ═══
    {"name": "Corda de Pular Speed Rope", "cat": "fitness", "brand": "", "base_price": 29.90, "supplier_price": 6.00, "supplier": "CJ Dropshipping"},
    {"name": "Faixa Elástica Kit 5 Níveis", "cat": "fitness", "brand": "", "base_price": 39.90, "supplier_price": 10.00, "supplier": "CJ Dropshipping"},
    {"name": "Garrafa Motivacional 2L", "cat": "fitness", "brand": "", "base_price": 34.90, "supplier_price": 8.00, "supplier": "CJ Dropshipping"},
    {"name": "Rolo Massagem Miofascial", "cat": "fitness", "brand": "", "base_price": 49.90, "supplier_price": 13.00, "supplier": "CJ Dropshipping"},
    {"name": "Luva Treino Academia", "cat": "fitness", "brand": "", "base_price": 34.90, "supplier_price": 8.00, "supplier": "AliExpress"},
    {"name": "Whey Protein Isolate 900g", "cat": "fitness", "brand": "", "base_price": 129.90, "supplier_price": 45.00, "supplier": "Fornecedor Nacional"},
    {"name": "Creatina Monohidratada 300g", "cat": "fitness", "brand": "", "base_price": 79.90, "supplier_price": 28.00, "supplier": "Fornecedor Nacional"},
    {"name": "Coqueteleira 600ml Inox", "cat": "fitness", "brand": "", "base_price": 29.90, "supplier_price": 7.00, "supplier": "AliExpress"},

    # ═══ PETS (6 products) - Supplier: AliExpress ═══
    {"name": "Bebedouro Fonte Automática", "cat": "pets", "brand": "", "base_price": 79.90, "supplier_price": 24.00, "supplier": "AliExpress"},
    {"name": "Brinquedo Interativo Gato", "cat": "pets", "brand": "", "base_price": 29.90, "supplier_price": 7.00, "supplier": "AliExpress"},
    {"name": "Coleira GPS Rastreador", "cat": "pets", "brand": "", "base_price": 129.90, "supplier_price": 42.00, "supplier": "AliExpress"},
    {"name": "Cama Pet Ortopédica M", "cat": "pets", "brand": "", "base_price": 99.90, "supplier_price": 30.00, "supplier": "AliExpress"},
    {"name": "Comedouro Automático WiFi", "cat": "pets", "brand": "", "base_price": 179.90, "supplier_price": 55.00, "supplier": "AliExpress"},
    {"name": "Escova Desembaraçadora Pro", "cat": "pets", "brand": "", "base_price": 24.90, "supplier_price": 5.00, "supplier": "AliExpress"},

    # ═══ GAMING & GEEK (8 products) - Supplier: AliExpress ═══
    {"name": "Controle Gamer Bluetooth", "cat": "gaming", "brand": "", "base_price": 89.90, "supplier_price": 28.00, "supplier": "AliExpress"},
    {"name": "Headset Gamer 7.1 RGB", "cat": "gaming", "brand": "", "base_price": 129.90, "supplier_price": 38.00, "supplier": "AliExpress"},
    {"name": "Mousepad XXL 80x30cm RGB", "cat": "gaming", "brand": "", "base_price": 59.90, "supplier_price": 16.00, "supplier": "AliExpress"},
    {"name": "Suporte Headset RGB", "cat": "gaming", "brand": "", "base_price": 49.90, "supplier_price": 14.00, "supplier": "AliExpress"},
    {"name": "Luminária Neon Gamer", "cat": "gaming", "brand": "", "base_price": 79.90, "supplier_price": 22.00, "supplier": "AliExpress"},
    {"name": "Cadeira Gamer Ergonômica", "cat": "gaming", "brand": "", "base_price": 599.90, "supplier_price": 180.00, "supplier": "CJ Dropshipping"},
    {"name": "Ring Light Streamer 10\"", "cat": "gaming", "brand": "", "base_price": 69.90, "supplier_price": 20.00, "supplier": "AliExpress"},
    {"name": "Webcam 4K Streamer Pro", "cat": "gaming", "brand": "", "base_price": 199.90, "supplier_price": 62.00, "supplier": "AliExpress"},

    # ═══ FOOD & SUPPLEMENTS (5 products) - Supplier: Fornecedor Nacional ═══
    {"name": "Colágeno Hidrolisado 500g", "cat": "food", "brand": "", "base_price": 59.90, "supplier_price": 18.00, "supplier": "Fornecedor Nacional"},
    {"name": "Pasta Amendoim Gourmet 1kg", "cat": "food", "brand": "", "base_price": 34.90, "supplier_price": 12.00, "supplier": "Fornecedor Nacional"},
    {"name": "Multivitamínico A-Z 90caps", "cat": "food", "brand": "", "base_price": 44.90, "supplier_price": 15.00, "supplier": "Fornecedor Nacional"},
    {"name": "Ômega 3 EPA/DHA 120caps", "cat": "food", "brand": "", "base_price": 49.90, "supplier_price": 16.00, "supplier": "Fornecedor Nacional"},
    {"name": "Melatonina 5mg 60caps", "cat": "food", "brand": "", "base_price": 39.90, "supplier_price": 10.00, "supplier": "Fornecedor Nacional"},
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
            "gaming": "Level up no seu setup! Performance e estilo gamer.",
            "food": "Nutrição de qualidade para uma vida mais saudável!",
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

# ─── WhatsApp Bot ───
from app.whatsapp_bot import (
    init_whatsapp_bot, wa_bot, WA_VERIFY_TOKEN, WA_STATS, CONVERSATIONS
)

# ─── Social Media (Iris AI) ───
from app.social_media import (
    auto_post, social_media_loop, get_social_stats, SOCIAL_POSTS, SOCIAL_STATS
)

# ─── Email Marketing ───
from app.email_marketing import (
    send_welcome_email, send_order_email, send_cart_reminder,
    send_weekly_deals, add_abandoned_cart, process_abandoned_carts,
    get_email_stats, SUBSCRIBERS, EMAIL_LOG
)

# ─── Cart + Checkout ───
from app.cart import (
    get_cart, add_to_cart, update_cart_qty, remove_from_cart, clear_cart,
    apply_coupon, get_cart_totals, calc_shipping, create_flash_sale,
    get_active_flash_sales, get_cart_stats, COUPONS, CHECKOUT_ORDERS
)

# ─── Reviews ───
from app.reviews import (
    generate_initial_reviews, add_review, get_product_reviews,
    get_product_rating_stats, mark_helpful, moderate_review,
    get_pending_reviews, get_review_stats, REVIEWS
)

# ─── Blog ───
from app.blog import init_blog, get_all_posts, get_post_by_slug, get_blog_categories, get_blog_stats

# ─── Affiliates ───
from app.affiliates import (
    register_affiliate, track_click, track_sale, get_affiliate,
    get_affiliate_sales, get_affiliate_stats, init_affiliates, AFFILIATES
)

# ─── Admin ───
from app.admin import (
    admin_login, verify_admin, admin_logout,
    export_orders_csv, export_products_csv
)


async def initialize_catalog():
    await init_db()
    await init_auth_db()
    
    existing = await product_count()
    if existing > 0:
        log_ai("Luna", "STARTUP", f"Catálogo já existe com {existing} produtos no SQL")
        prods = await get_all_products()
        PRODUCTS.clear()
        PRODUCTS.extend(prods)
        stats = await get_all_stats()
        STORE_STATS.update({k: v for k, v in stats.items() if k in STORE_STATS})
        asyncio.create_task(ai_background_loop())
        asyncio.create_task(social_media_loop(PRODUCTS, log_ai))
        init_multi_agent(PRODUCTS, ORDERS, STORE_STATS, AI_ACTIVITY_LOG,
                         ask_ai, log_ai, log_activity, inc_stat, update_product,
                         {"stock_low": notify_stock_low, "new_order": notify_new_order})
        await start_all_agents()
        init_whatsapp_bot(PRODUCTS, ORDERS, ask_ai, log_ai)
        generate_initial_reviews(PRODUCTS)
        if PRODUCTS:
            import random as _r
            for _ in range(2):
                fp = _r.choice(PRODUCTS)
                create_flash_sale(fp["id"], fp["name"], _r.randint(20, 40), _r.randint(2, 6))
        init_blog()
        init_affiliates()
        log_ai("Aria", "BLOG", f"📝 Blog initialized with {len(get_all_posts())} articles")
        log_ai("Sistema", "MULTI-AGENT", "🤖 v5.0 - Blog + Affiliates + Dark Mode + Cart + Reviews + Admin!")
        return
    
    log_ai("Luna", "STARTUP", f"Criando catálogo com {len(INITIAL_PRODUCTS)} produtos de fornecedores reais")
    await log_activity("Luna", "STARTUP", "Iniciando curadoria com Claude AI + Ollama")
    
    for p in INITIAL_PRODUCTS:
        pricing = calc_price(p)
        desc = await gen_description(p)
        pid = hashlib.md5(p["name"].encode()).hexdigest()[:8]
        sold = random.randint(50, 2000)
        rating = round(random.uniform(4.0, 5.0), 1)
        
        product = {
            "id": pid, "name": p["name"], "category": p["cat"],
            "brand": p.get("brand", ""), "description": desc,
            "price": pricing["price"], "old_price": pricing["old_price"],
            "discount": pricing["discount"], "margin": pricing["margin"],
            "supplier_price": p["supplier_price"],
            "supplier": p.get("supplier", "AliExpress"),
            "image": make_image_url(p["name"], p["cat"]),
            "sold": sold, "rating": rating,
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
    log_ai("Luna", "CATALOG", f"Catálogo criado: {n} produtos (Nike + Anthropic + 10 categorias)")
    log_ai("Aria", "COPY", f"Descrições para {n} produtos via {'Claude' if ANTHROPIC_KEY else 'Ollama'}")
    log_ai("Zara", "PRICING", f"Preços otimizados para {n} produtos")
    log_ai("Iris", "SOCIAL", f"📱 Auto-posting ativado para Instagram/TikTok/Twitter")
    log_ai("Nova", "WHATSAPP", f"📱 WhatsApp Bot 24/7 ativo")
    
    asyncio.create_task(ai_background_loop())
    asyncio.create_task(social_media_loop(PRODUCTS, log_ai))
    
    init_multi_agent(PRODUCTS, ORDERS, STORE_STATS, AI_ACTIVITY_LOG,
                     ask_ai, log_ai, log_activity, inc_stat, update_product,
                     {"stock_low": notify_stock_low, "new_order": notify_new_order})
    await start_all_agents()
    init_whatsapp_bot(PRODUCTS, ORDERS, ask_ai, log_ai)
    # Generate initial reviews
    generate_initial_reviews(PRODUCTS)
    log_ai("Nova", "REVIEWS", f"⭐ {len(REVIEWS)} avaliações geradas e moderadas")
    
    # Create initial flash sales
    if PRODUCTS:
        import random as _r
        for _ in range(2):
            fp = _r.choice(PRODUCTS)
            create_flash_sale(fp["id"], fp["name"], _r.randint(20, 40), _r.randint(2, 6))
        log_ai("Zara", "FLASH_SALE", "⚡ Flash sales ativadas!")
    
    init_blog()
    init_affiliates()
    log_ai("Aria", "BLOG", f"📝 Blog initialized with {len(get_all_posts())} articles")
    log_ai("Sistema", "MULTI-AGENT", "🤖 v5.0 - Blog + Affiliates + Dark Mode + all features!")

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
            
            # Process abandoned carts
            await process_abandoned_carts()
            
            if random.random() < 0.3 and PRODUCTS:
                prod = random.choice(PRODUCTS)
                qty = random.randint(1, 3)
                oid = f"ORD-{await count_orders() + 1:04d}"
                order = {
                    "id": oid, "product": prod["name"], "product_id": prod["id"],
                    "qty": qty, "total": round(prod["price"] * qty, 2),
                    "profit": round((prod["price"] - prod["supplier_price"]) * qty, 2),
                    "status": random.choice(["Processing", "Shipped", "In Transit"]),
                    "customer": f"Cliente #{random.randint(1000, 9999)}",
                    "handled_by": "Vega",
                    "supplier": prod.get("supplier", "AliExpress"),
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
                await notify_new_order(order, prod)
                if prod["stock"] < 5:
                    await notify_stock_low(prod["name"], prod["stock"])
        except Exception:
            pass

@app.on_event("startup")
async def startup():
    init_blog()
    init_affiliates()
    asyncio.create_task(initialize_catalog())

# ─── Routes ───

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, cat: Optional[str] = None, q: Optional[str] = None, sort: Optional[str] = None, ref: Optional[str] = None):
    STORE_STATS["visitors"] += 1
    if ref:
        track_click(ref)
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
        "has_anthropic": bool(ANTHROPIC_KEY), "ga_id": GA_MEASUREMENT_ID,
    })

@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return HTMLResponse("<h1>Produto não encontrado</h1>", status_code=404)
    related = [p for p in PRODUCTS if p["category"] == product["category"] and p["id"] != product_id][:4]
    reviews = get_product_reviews(product_id)
    rating_stats = get_product_rating_stats(product_id)
    return templates.TemplateResponse("product.html", {
        "request": request, "product": product, "related": related,
        "ai_employees": AI_EMPLOYEES, "stats": STORE_STATS, "ga_id": GA_MEASUREMENT_ID,
        "reviews": reviews, "rating_stats": rating_stats,
    })

@app.post("/api/buy/{product_id}")
async def buy_product(request: Request, product_id: str, qty: int = 1):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return JSONResponse({"error": "Product not found"}, 404)
    if product["stock"] < qty:
        return JSONResponse({"error": "Estoque insuficiente"}, 400)
    
    oid = f"ORD-{await count_orders() + 1:04d}"
    order = {
        "id": oid, "product": product["name"], "product_id": product["id"],
        "qty": qty, "total": round(product["price"] * qty, 2),
        "profit": round((product["price"] - product["supplier_price"]) * qty, 2),
        "status": "Processing",
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
    await notify_new_order(order, product)
    if product["stock"] < 5:
        await notify_stock_low(product["name"], product["stock"])

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
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
    
    total_profit = sum(o.get("profit", 0) for o in ORDERS)
    avg_margin = sum(p["margin"] for p in PRODUCTS) / len(PRODUCTS) if PRODUCTS else 0
    
    # Supplier breakdown
    suppliers = {}
    for p in PRODUCTS:
        s = p.get("supplier", "Desconhecido")
        if s not in suppliers:
            suppliers[s] = {"count": 0, "revenue": 0}
        suppliers[s]["count"] += 1
        suppliers[s]["revenue"] += p["price"] * p.get("sold", 0)
    
    # Category breakdown
    cat_stats = {}
    for p in PRODUCTS:
        c = p.get("category", "other")
        if c not in cat_stats:
            cat_stats[c] = {"count": 0, "sold": 0, "revenue": 0}
        cat_stats[c]["count"] += 1
        cat_stats[c]["sold"] += p.get("sold", 0)
        cat_stats[c]["revenue"] += p["price"] * p.get("sold", 0)
    
    # Revenue timeline (simulated daily data)
    revenue_timeline = []
    for i in range(30):
        day = (datetime.now() - timedelta(days=29-i)).strftime("%d/%m")
        rev = random.uniform(500, 5000) * (1 + i * 0.02)
        revenue_timeline.append({"day": day, "revenue": round(rev, 2)})
    
    # Conversion funnel
    visitors = STORE_STATS.get("visitors", 1000)
    funnel = {
        "visitors": visitors,
        "product_views": int(visitors * random.uniform(0.3, 0.5)),
        "add_to_cart": int(visitors * random.uniform(0.1, 0.2)),
        "checkout": int(visitors * random.uniform(0.05, 0.1)),
        "purchase": STORE_STATS.get("orders_count", 0),
    }
    
    try:
      return templates.TemplateResponse("dashboard.html", {
        "request": request, "stats": STORE_STATS,
        "top_products": top_products, "recent_orders": recent_orders,
        "recent_activity": recent_activity,
        "ai_employees": AI_EMPLOYEES,
        "total_profit": round(total_profit, 2),
        "avg_margin": round(avg_margin, 1),
        "total_products": len(PRODUCTS),
        "categories": CATEGORIES,
        "has_anthropic": bool(ANTHROPIC_KEY),
        "has_pg": has_pg(),
        "db_info": await db_status(),
        "db_size": f"{Path(BASE.parent / 'store.db').stat().st_size / 1024:.1f} KB" if Path(BASE.parent / 'store.db').exists() else "0 KB",
        "suppliers": suppliers,
        "cat_stats": cat_stats,
        "cat_stats_json": json.dumps(cat_stats),
        "revenue_timeline": json.dumps(revenue_timeline),
        "funnel": funnel,
        "social_stats": SOCIAL_STATS,
        "wa_stats": WA_STATS,
        "email_stats": get_email_stats(),
        "ga_id": GA_MEASUREMENT_ID,
      })
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        return HTMLResponse(f"<pre>Dashboard Error:\n{error_msg}</pre>", status_code=500)

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
        "social": SOCIAL_STATS,
        "whatsapp": WA_STATS,
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
    msgs = bus.get_for(agent, limit) if agent else bus.get_all(limit)
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

# ─── AUTH ROUTES ───

@app.post("/api/register")
async def api_register(request: Request):
    data = await request.json()
    result = await register_customer(data.get("name", ""), data.get("email", ""), data.get("password", ""))
    if result.get("success"):
        await notify_new_customer(data["name"], data["email"])
        await send_welcome_email(data["name"], data["email"])
        log_ai("Nova", "REGISTER", f"Novo cliente: {data['email']}")
        log_ai("Aria", "EMAIL", f"📧 Welcome email enviado para {data['email']}")
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
        "request": request, "ai_employees": AI_EMPLOYEES, "ga_id": GA_MEASUREMENT_ID,
    })

# ─── WHATSAPP BOT ROUTES ───

@app.get("/api/whatsapp/webhook")
async def wa_verify(request: Request):
    """WhatsApp webhook verification"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == WA_VERIFY_TOKEN:
        return HTMLResponse(content=challenge, status_code=200)
    return JSONResponse({"error": "Forbidden"}, 403)

@app.post("/api/whatsapp/webhook")
async def wa_webhook(request: Request):
    """Receive WhatsApp messages"""
    try:
        body = await request.json()
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        for msg in messages:
            phone = msg.get("from", "")
            text = msg.get("text", {}).get("body", "")
            name = ""
            contacts = value.get("contacts", [])
            if contacts:
                name = contacts[0].get("profile", {}).get("name", "")
            
            if text and phone:
                asyncio.create_task(wa_bot.handle_message(phone, text, name))
        
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/api/whatsapp/stats")
async def wa_stats_api():
    return JSONResponse({
        "stats": WA_STATS,
        "active_conversations": len(CONVERSATIONS),
        "conversations": {phone[-4:]: len(msgs) for phone, msgs in list(CONVERSATIONS.items())[-20:]},
    })

@app.post("/api/whatsapp/send")
async def wa_send(request: Request):
    """Manual send for testing"""
    data = await request.json()
    phone = data.get("phone", "")
    message = data.get("message", "")
    if phone and message:
        response = await wa_bot.handle_message(phone, message, "Teste")
        return JSONResponse({"success": True, "response": response})
    return JSONResponse({"error": "phone and message required"}, 400)

# ─── SOCIAL MEDIA ROUTES (Iris AI) ───

@app.get("/api/social/stats")
async def social_stats_api():
    return JSONResponse(get_social_stats())

@app.post("/api/social/post")
async def social_post_now(request: Request):
    """Manual post to social media"""
    data = await request.json()
    product_id = data.get("product_id", "")
    platform = data.get("platform", "instagram")
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if product:
        post = await auto_post(product, platform)
        log_ai("Iris", "SOCIAL_MANUAL", f"📱 {platform}: {product['name']}")
        return JSONResponse({"success": True, "post": post})
    return JSONResponse({"error": "Product not found"}, 404)

@app.get("/api/social/feed")
async def social_feed():
    return JSONResponse({"posts": SOCIAL_POSTS[-30:][::-1], "stats": SOCIAL_STATS})

# ─── EMAIL MARKETING ROUTES ───

@app.get("/api/email/stats")
async def email_stats_api():
    return JSONResponse(get_email_stats())

@app.post("/api/email/subscribe")
async def email_subscribe(request: Request):
    data = await request.json()
    email = data.get("email", "")
    name = data.get("name", "Visitante")
    if email:
        await send_welcome_email(name, email)
        log_ai("Aria", "EMAIL", f"📧 Novo subscriber: {email}")
        return JSONResponse({"success": True, "message": "Inscrito! Check seu email."})
    return JSONResponse({"error": "Email necessário"}, 400)

@app.post("/api/email/weekly-deals")
async def email_weekly_deals():
    sent = await send_weekly_deals(PRODUCTS)
    log_ai("Aria", "EMAIL", f"📧 Newsletter semanal enviada para {sent} subscribers")
    return JSONResponse({"success": True, "sent": sent})

# ─── TELEGRAM ROUTES ───

@app.post("/api/telegram/register")
async def telegram_register(request: Request):
    data = await request.json()
    chat_id = data.get("chat_id", "")
    if chat_id:
        register_chat(chat_id)
        await send_telegram(f"✅ Chat {chat_id} registrado para notificações!", chat_id)
        return JSONResponse({"success": True})
    return JSONResponse({"error": "chat_id necessário"}, 400)

@app.post("/api/telegram/test")
async def telegram_test():
    ok = await send_telegram("🧪 <b>Teste</b>\n\nAI Drop Store conectada!")
    return JSONResponse({"success": ok})

@app.get("/api/telegram/summary")
async def telegram_summary():
    top = sorted(PRODUCTS, key=lambda x: x["sold"], reverse=True)[:5]
    ok = await notify_daily_summary(STORE_STATS, top)
    return JSONResponse({"success": ok})

# ─── SEO ROUTES ───

@app.get("/sitemap.xml")
async def sitemap():
    base = "https://ai-drop-store-nd4f.onrender.com"
    urls = [f"<url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    urls.append(f"<url><loc>{base}/dashboard</loc><changefreq>hourly</changefreq><priority>0.8</priority></url>")
    urls.append(f"<url><loc>{base}/agents</loc><changefreq>hourly</changefreq><priority>0.7</priority></url>")
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
Sitemap: https://ai-drop-store-nd4f.onrender.com/sitemap.xml

User-agent: Googlebot
Allow: /
Crawl-delay: 1
""", media_type="text/plain")



# ─── CART ROUTES ───

@app.get("/carrinho", response_class=HTMLResponse)
async def cart_page(request: Request):
    return templates.TemplateResponse("cart.html", {"request": request, "ai_employees": AI_EMPLOYEES, "ga_id": GA_MEASUREMENT_ID})

@app.get("/api/cart")
async def api_get_cart(session: str = ""):
    cart = get_cart(session)
    return JSONResponse(cart)

@app.post("/api/cart/add")
async def api_add_to_cart(request: Request):
    data = await request.json()
    product = next((p for p in PRODUCTS if p["id"] == data.get("product_id")), None)
    if not product:
        return JSONResponse({"error": "Product not found"}, 404)
    cart = add_to_cart(data.get("session", ""), product, data.get("qty", 1))
    log_ai("Nova", "CART", f"🛒 Item adicionado: {product['name']}")
    return JSONResponse({"success": True, "cart": cart})

@app.post("/api/cart/update")
async def api_update_cart(request: Request):
    data = await request.json()
    cart = update_cart_qty(data.get("session", ""), data.get("product_id", ""), data.get("qty", 1))
    return JSONResponse({"success": True, "cart": cart})

@app.post("/api/cart/remove")
async def api_remove_from_cart(request: Request):
    data = await request.json()
    cart = remove_from_cart(data.get("session", ""), data.get("product_id", ""))
    return JSONResponse({"success": True, "cart": cart})

@app.get("/api/cart/totals")
async def api_cart_totals(session: str = "", cep: str = ""):
    totals = get_cart_totals(session, cep)
    return JSONResponse(totals)

@app.post("/api/cart/coupon")
async def api_apply_coupon(request: Request):
    data = await request.json()
    result = apply_coupon(data.get("session", ""), data.get("code", ""))
    return JSONResponse(result)

@app.get("/api/cart/shipping")
async def api_calc_shipping(cep: str = "", session: str = ""):
    totals = get_cart_totals(session)
    shipping = calc_shipping(cep, totals["subtotal"])
    return JSONResponse(shipping)

@app.get("/api/flash-sales")
async def api_flash_sales():
    return JSONResponse({"sales": get_active_flash_sales()})

# ─── REVIEW ROUTES ───

@app.get("/api/reviews/{product_id}")
async def api_get_reviews(product_id: str):
    reviews = get_product_reviews(product_id)
    stats = get_product_rating_stats(product_id)
    return JSONResponse({"reviews": reviews, "stats": stats})

@app.post("/api/reviews/add")
async def api_add_review(request: Request):
    data = await request.json()
    result = add_review(
        data.get("product_id", ""), data.get("customer_name", "Anônimo"),
        data.get("rating", 5), data.get("title", ""), data.get("text", "")
    )
    if result.get("success"):
        log_ai("Nova", "REVIEW", f"⭐ Nova avaliação para moderação")
    return JSONResponse(result)

@app.post("/api/reviews/helpful")
async def api_mark_helpful(request: Request):
    data = await request.json()
    ok = mark_helpful(data.get("review_id", ""))
    return JSONResponse({"success": ok})

# ─── ADMIN ROUTES ───

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/api/admin/login")
async def api_admin_login(request: Request):
    data = await request.json()
    result = admin_login(data.get("email", ""), data.get("password", ""))
    return JSONResponse(result)

@app.get("/api/admin/overview")
async def api_admin_overview(token: str = ""):
    admin = verify_admin(token)
    if not admin:
        return JSONResponse({"error": "Unauthorized"}, 401)
    review_stats = get_review_stats()
    cart_stats = get_cart_stats()
    return JSONResponse({
        "admin_name": admin["name"],
        "revenue": STORE_STATS.get("total_revenue", 0),
        "orders": STORE_STATS.get("orders_count", 0),
        "products": len(PRODUCTS),
        "visitors": STORE_STATS.get("visitors", 0),
        "ai_decisions": STORE_STATS.get("ai_decisions", 0),
        "reviews": review_stats["total_reviews"],
        "active_carts": cart_stats["active_carts"],
        "subscribers": len(SUBSCRIBERS),
    })

@app.get("/api/admin/products")
async def api_admin_products(token: str = ""):
    if not verify_admin(token):
        return JSONResponse({"error": "Unauthorized"}, 401)
    return JSONResponse({"products": PRODUCTS})

@app.get("/api/admin/orders")
async def api_admin_orders(token: str = ""):
    if not verify_admin(token):
        return JSONResponse({"error": "Unauthorized"}, 401)
    orders = ORDERS[-50:][::-1]
    return JSONResponse({"orders": orders})

@app.post("/api/admin/order/status")
async def api_admin_update_order(request: Request):
    data = await request.json()
    if not verify_admin(data.get("token", "")):
        return JSONResponse({"error": "Unauthorized"}, 401)
    for o in ORDERS:
        if o.get("id") == data.get("order_id"):
            o["status"] = data.get("status", o["status"])
            log_ai("Vega", "ORDER_UPDATE", f"📦 {o['id']} → {o['status']}")
            return JSONResponse({"success": True})
    return JSONResponse({"error": "Order not found"}, 404)

@app.get("/api/admin/coupons")
async def api_admin_coupons(token: str = ""):
    if not verify_admin(token):
        return JSONResponse({"error": "Unauthorized"}, 401)
    return JSONResponse({"coupons": COUPONS})

@app.get("/api/admin/reviews")
async def api_admin_reviews(token: str = ""):
    if not verify_admin(token):
        return JSONResponse({"error": "Unauthorized"}, 401)
    return JSONResponse({
        "stats": get_review_stats(),
        "pending": get_pending_reviews()[:20],
    })

@app.post("/api/admin/review/moderate")
async def api_admin_moderate(request: Request):
    data = await request.json()
    if not verify_admin(data.get("token", "")):
        return JSONResponse({"error": "Unauthorized"}, 401)
    result = await moderate_review(data.get("review_id", ""), data.get("approved", True))
    return JSONResponse(result)

@app.get("/api/admin/export/orders")
async def api_export_orders(token: str = ""):
    csv_data = export_orders_csv(ORDERS)
    return HTMLResponse(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})

@app.get("/api/admin/export/products")
async def api_export_products(token: str = ""):
    csv_data = export_products_csv(PRODUCTS)
    return HTMLResponse(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=products.csv"})



# ─── BLOG ROUTES ───

@app.get("/blog", response_class=HTMLResponse)
async def blog_page(request: Request, cat: str = ""):
    posts = get_all_posts(cat)
    return templates.TemplateResponse("blog.html", {
        "request": request, "posts": posts, "categories": get_blog_categories(),
        "stats": get_blog_stats(), "current_cat": cat,
    })

@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_page(request: Request, slug: str):
    post = get_post_by_slug(slug)
    if not post:
        return HTMLResponse("<h1>Post not found</h1>", 404)
    related = [p for p in get_all_posts() if p["slug"] != slug][:3]
    return templates.TemplateResponse("blog_post.html", {
        "request": request, "post": post, "related": related,
    })

# ─── AFFILIATE ROUTES ───

@app.get("/affiliates", response_class=HTMLResponse)
async def affiliates_page(request: Request):
    return templates.TemplateResponse("affiliates.html", {"request": request})

@app.post("/api/affiliates/register")
async def api_register_affiliate(request: Request):
    data = await request.json()
    result = register_affiliate(data.get("name", ""), data.get("email", ""))
    return JSONResponse(result)

@app.get("/api/affiliates/{code}")
async def api_get_affiliate(code: str):
    aff = get_affiliate(code)
    if not aff:
        return JSONResponse({"error": "Affiliate not found"}, 404)
    return JSONResponse({"affiliate": aff, "sales": get_affiliate_sales(code)})

@app.get("/api/affiliates/leaderboard")
async def api_affiliate_leaderboard():
    sorted_affs = sorted(AFFILIATES.values(), key=lambda x: x["total_earned"], reverse=True)
    return JSONResponse({"leaderboard": sorted_affs[:10]})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
