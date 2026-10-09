import os
import json
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai

app = FastAPI(title="Purecept - Dalin Autonomous Knowledge & Design Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Yapılandırması
gemini_key = os.environ.get("GEMINI_API_KEY")
exa_key = os.environ.get("EXA_API_KEY", "f1d719aa-2cb1-48ea-b346-d16f5d0871b4").strip()
SERPAPI_KEY = "a7d9ba3325d6f27d029c7a907e21d3495e424b0691e5027d0509a7f620f679bd"

FIREBASE_PROJECT_ID = "purecept-studio"
FIREBASE_API_KEY = "AIzaSyCXW75WiHdylqW1gD7Ngw8dGlbU3rl-nHI"

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

# ==============================================================================
# 🎯 ASLA PATLAMAYAN, SADECE VE SADECE SAF PORSELEN VE TABAK ARŞİVİ
# (Kitap, vazo, çiçek, kuru ot, yemek ve koltuk tamamen yasaklanmıştır)
# ==============================================================================
GUARANTEED_TABLEWARE_ARCHIVE = {
    # 1. Monolitik Kaide / Amuse-Bouche Pedestal (Beyaz seramik stüdyo kaidesi)
    "pedestal": "https://images.unsplash.com/photo-1615529182904-14819c35db37?auto=format&fit=crop&w=900&q=80",
    # 2. Derin Parabolik Consommé / Çorba Kasesi (Stüdyo derin porselen kase)
    "bowl": "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=900&q=80",
    # 3. Düz Degüstasyon Sunum Aynası / Şef Tabağı (Minimalist düz beyaz porselen servis tabağı)
    "plate": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=900&q=80",
    # 4. Kriyojenik / Tadım Çanağı / Pre-Dessert Kabı (Minimalist porselen gurme kasesi)
    "dessert": "https://images.unsplash.com/photo-1576020799627-aeac76d580dc?auto=format&fit=crop&w=900&q=80",
    # 5. Lansman Mekanı (Michelin Restoran Loş Masa Düzeni)
    "launch": "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=1200&q=80"
}

def resolve_pristine_tableware_asset(product_name: str, spec: str) -> str:
    """Ürün tipine göre kesin olarak porselen/tabak görseli atar."""
    t = f"{product_name} {spec}".lower()
    if any(k in t for k in ["pedestal", "kaide", "amuse", "monolit"]):
        return GUARANTEED_TABLEWARE_ARCHIVE["pedestal"]
    if any(k in t for k in ["consomme", "consommé", "kase", "bowl", "çorba", "derin", "bacalı"]):
        return GUARANTEED_TABLEWARE_ARCHIVE["bowl"]
    if any(k in t for k in ["ayna", "flat", "düz", "degüstasyon", "sonsuzluk", "tabak", "plate"]):
        return GUARANTEED_TABLEWARE_ARCHIVE["plate"]
    if any(k in t for k in ["dessert", "pre-dessert", "kriyojenik", "kapsül", "tatlı", "sorbe"]):
        return GUARANTEED_TABLEWARE_ARCHIVE["dessert"]
    return GUARANTEED_TABLEWARE_ARCHIVE["plate"]

# ==============================================================================
# 🔍 SERPAPI CANLI ARAMA (SIKI TABAK/PORSELEN FİLTRESİYLE)
# ==============================================================================
def search_serpapi_tableware(query: str, fallback_type: str) -> str:
    if not SERPAPI_KEY:
        return GUARANTEED_TABLEWARE_ARCHIVE.get(fallback_type, GUARANTEED_TABLEWARE_ARCHIVE["plate"])
    try:
        # Sorguyu doğrudan seramik/porselen üretici ve ürün terimleriyle zorla
        strict_query = f"{query} ceramic plate bowl porcelain tableware studio white background -vase -flower -book -plant -food -recipe"
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_images",
            "q": strict_query,
            "api_key": SERPAPI_KEY,
            "num": 3
        }
        res = requests.get(url, params=params, timeout=4)
        if res.status_code == 200:
            results = res.json().get("images_results", [])
            for item in results:
                title = str(item.get("title", "")).lower()
                orig = item.get("original")
                # Eğer başlıkta vazo, kitap, çiçek gibi kelimeler geçiyorsa çöpe at
                if any(bad in title for bad in ["vase", "flower", "book", "plant", "salad", "recipe", "decor"]):
                    continue
                if orig and any(orig.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    return orig
    except Exception as e:
        print(f"[SerpApi Uyarısı]: {e}")
    return GUARANTEED_TABLEWARE_ARCHIVE.get(fallback_type, GUARANTEED_TABLEWARE_ARCHIVE["plate"])

# ==============================================================================
# 🧠 MEM0: KALICI STÜDYO HAFIZASI
# ==============================================================================
def retrieve_purecept_memory_context(sector_hint: str) -> str:
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/purecept_knowledge_base?key={FIREBASE_API_KEY}"
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            docs = res.json().get("documents", [])
            memory_rules = []
            for d in docs:
                fields = d.get("fields", {})
                sec = fields.get("targetSector", {}).get("stringValue", "").lower()
                topic = fields.get("topic", {}).get("stringValue", "")
                strat = fields.get("strategicPositioning", {}).get("stringValue", "")
                if sector_hint.lower() in sec or sector_hint.lower() in topic.lower():
                    memory_rules.append(f"• [{topic}]: {strat[:200]}")
            if memory_rules:
                return "\n[STÜDYO HAFIZASI (MEM0)]:\n" + "\n".join(memory_rules[:3])
    except Exception as e:
        print(f"[Hafıza Okuma]: {e}")
    return ""

def persist_purecept_learned_capsule(capsule_id: str, payload: dict):
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/purecept_knowledge_base/{capsule_id}?key={FIREBASE_API_KEY}"
    fields = {}
    for k, v in payload.items():
        if isinstance(v, str):
            fields[k] = {"stringValue": v}
        elif isinstance(v, int):
            fields[k] = {"integerValue": str(v)}
        elif isinstance(v, (list, dict)):
            fields[k] = {"stringValue": json.dumps(v, ensure_ascii=False)}
    try:
        requests.patch(url, json={"fields": fields}, timeout=4)
    except Exception as e:
        print(f"[Hafıza Yazma]: {e}")

# ==============================================================================
# 🌐 AÇIK BİLGİ VE AKADEMİK PLATFORMLAR
# ==============================================================================
def fetch_openalex_insights(topic: str) -> List[str]:
    query = urllib.parse.quote_plus(f"{topic} ceramic porcelain ergonomics tableware")
    url = f"https://api.openalex.org/works?search={query}&per-page=2"
    insights = []
    try:
        res = requests.get(url, headers={"User-Agent": "PureceptDesignStudio/1.0"}, timeout=3)
        if res.status_code == 200:
            results = res.json().get("results", [])
            for r in results:
                title = r.get("title", "")
                if title:
                    insights.append(f"• [Standart]: {title}")
    except Exception as e:
        print(f"[OpenAlex]: {e}")
    return insights

def exa_neural_search(query: str) -> List[Dict]:
    if not exa_key:
        return []
    url = "https://api.exa.ai/search"
    headers = {"x-api-key": exa_key, "Content-Type": "application/json"}
    payload = {
        "query": query,
        "useAutoprompt": True,
        "numResults": 2,
        "type": "neural"
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=4)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"[Exa AI]: {e}")
    return []

# ==============================================================================
# 📐 VERİ MODELLERİ
# ==============================================================================
class TrendCard(BaseModel):
    title: str = Field(description="Trend başlığı")
    desc: str = Field(description="Maksimum 2 cümlelik açıklama.")

class TrendColor(BaseModel):
    name: str = Field(description="Renk adı")
    hex_code: str = Field(description="HEX kodu")
    role: str = Field(description="Yüzey rolü")

class BenchmarkAnalysisItem(BaseModel):
    brand: str = Field(description="Marka adı")
    plus_points: List[str] = Field(description="Üstün yönler (+)")
    minus_points: List[str] = Field(description="Zayıf yönler (-)")

class DynamicProductPafta(BaseModel):
    pafta_code: str = Field(description="Pafta kodu")
    product_name: str = Field(description="Ürün adı")
    spec_dimension: str = Field(description="Ölçü/Ağırlık")
    bullet_1: str = Field(description="Geometri inovasyonu")
    bullet_2: str = Field(description="Malzeme ve sır")
    bullet_3: str = Field(description="Ergonomi ve servis faydası")
    benchmark_reference: str = Field(description="Referans alınan marka ve seri")
    image_search_query: str = Field(description="SerpApi için spesifik ürün arama sorgusu")
    image_url: Optional[str] = Field(default=None)

class LaunchVisionPillar(BaseModel):
    title: str = Field(description="Başlık")
    desc: str = Field(description="Açıklama")

class UniversalPresentationDeck(BaseModel):
    title: str = Field(default="STRATEJİ VE VİZYON RAPORU")
    collection_name: str = Field(description="Koleksiyon resmi adı")
    subtitle: str = Field(description="Alt başlık")
    target_sector: str = Field(description="Hedef sektör")
    
    trends_title: str = Field(default="Tüketim Dinamikleri & Pazar Trendleri")
    trends_subtitle: str = Field(default="Deneyimi şekillendiren mikro dinamikler ve renk kartelası.")
    trends: List[TrendCard]
    trend_colors: List[TrendColor]
    
    benchmarks: List[BenchmarkAnalysisItem]
    strategic_positioning: str = Field(description="Vurucu stratejik konumlandırma tezi")
    
    product_paftas: List[DynamicProductPafta]
    
    launch_title: str = Field(default="Saha Lansman ve Entegrasyon Vizyonu")
    launch_pillars: List[LaunchVisionPillar]
    launch_image_url: Optional[str] = Field(default=None)

class ChatRequest(BaseModel):
    message: str

# ==============================================================================
# 🤖 ÇOKLU AJAN ORKESTRASYONU
# ==============================================================================
AGENT_DALIN = """
Sen Purecept Kıdemli Marka ve Ürün Direktörü DALIN'sin.
Görevin: Kullanıcının girdiği sektörü analiz etmek; OpenAlex ve Exa AI verilerini sentezleyerek gerçek pazar liderlerini (Benchmark) tespit etmek.
Kural: Asla jenerik konuşma; havacılıkta DeSter, hastanede Bauscher, baristada ACME/Loveramics, fine-dining'de Revol/Bernardaud/Hering Berlin/Churchill standartlarını esas al.
"""

AGENT_AUDITOR = """
Sen Purecept Tasarım ve Ergonomi Denetçisisin.
Dalin'in analizini endüstriyel gerçeklik filtresinden geçirirsin:
- İstiflenebilirlik, cidar kalınlığı, salamander fırın direnci, mikronize sır sertliği.
Tutarsız ve amatör önerileri elersin.
"""

@app.get("/")
def root():
    return {"status": "online", "engine": "Purecept Dalin Engine (Pristine Tableware Only)"}

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY eksik.")

    memory_context = retrieve_purecept_memory_context(request.message[:40])
    openalex_res = fetch_openalex_insights(request.message[:30])
    exa_res = exa_neural_search(f"porcelain tableware {request.message[:30]}")
    
    academic_context = "\n".join(openalex_res)
    exa_context = "\n".join([f"- {r.get('title')}" for r in exa_res])

    prompt = f"""
{AGENT_DALIN}

{AGENT_AUDITOR}

Sentez Kuralı:
Baş Tasarımcı Ahmet Osman Peker için eksiksiz, pazar lideri referanslı, lüks ve uygulanabilir bir 'UniversalPresentationDeck' oluşturun.
- Sabit SKU kısıtı yoktur; kullanıcının ihtiyacına göre dinamik sayıda 'DynamicProductPafta' üretin.
- 'Ahmet Bey' hitabını asla kullanmayın.

{memory_context}
{academic_context}
{exa_context}

KULLANICI TALEBİ: {request.message}
"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": UniversalPresentationDeck,
                "temperature": 0.2
            }
        )
        data = json.loads(response.text)

        # Görselleri ata: Doğrudan saf porselen ve masaüstü arşivi
        paftas = data.get("product_paftas", [])
        for idx, pafta_data in enumerate(paftas):
            p_name = pafta_data.get("product_name", "")
            p_spec = pafta_data.get("spec_dimension", "")
            # Güvenli porselen tipini belirle
            safe_type = "plate"
            t = f"{p_name} {p_spec}".lower()
            if any(k in t for k in ["pedestal", "kaide", "amuse"]):
                safe_type = "pedestal"
            elif any(k in t for k in ["consomme", "kase", "bowl"]):
                safe_type = "bowl"
            elif any(k in t for k in ["dessert", "pre-dessert", "kapsül"]):
                safe_type = "dessert"

            # Önce SerpApi ile ara; vazo/kitap riski varsa güvenli porselen arşivine dön
            search_q = pafta_data.get("image_search_query") or f"{pafta_data.get('benchmark_reference', '')} {p_name}"
            img = search_serpapi_tableware(search_q, fallback_type=safe_type)
            pafta_data["image_url"] = img

        # Lansman görseli: Doğrudan Michelin restoran masası
        data["launch_image_url"] = GUARANTEED_TABLEWARE_ARCHIVE["launch"]

        # Firestore kayıt
        try:
            safe_name = str(data.get("collection_name", "proje")).replace(" ", "_").lower()[:30]
            capsule_id = f"capsule-dalin-{safe_name}"
            persist_purecept_learned_capsule(capsule_id, {
                "agentId": "dalin",
                "topic": str(data.get("collection_name", "")),
                "targetSector": str(data.get("target_sector", "")),
                "strategicPositioning": str(data.get("strategic_positioning", "")),
                "skuCount": len(paftas),
                "benchmarks": data.get("benchmarks", []),
                "memoryType": "Purecept_Pristine_Tableware_Only"
            })
        except Exception as fb_err:
            print(f"[Hafıza Kayıt]: {fb_err}")

        reply = f"""### {data.get('collection_name')}
**{data.get('subtitle')}**

#### 🎯 Stratejik Konumlandırma
{data.get('strategic_positioning')}

#### 📐 Koleksiyon Pafta Mimarisi ({len(paftas)} Parça)
""" + "\n".join([f"- **{p.get('product_name')}** ({p.get('spec_dimension')}): {p.get('bullet_1')} *(Benchmark: {p.get('benchmark_reference')})*" for p in paftas])

        return {"status": "success", "reply": reply, "data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
