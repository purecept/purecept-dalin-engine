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

app = FastAPI(title="Purecept - Dalin Autonomous Live Intelligence Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 🔑 API VE HİZMET YAPILANDIRMASI
# ==============================================================================
gemini_key = os.environ.get("GEMINI_API_KEY")
exa_key = os.environ.get("EXA_API_KEY", "f1d719aa-2cb1-48ea-b346-d16f5d0871b4").strip()
SERPAPI_KEY = "a7d9ba3325d6f27d029c7a907e21d3495e424b0691e5027d0509a7f620f679bd"

FIREBASE_PROJECT_ID = "purecept-studio"
FIREBASE_API_KEY = "AIzaSyCXW75WiHdylqW1gD7Ngw8dGlbU3rl-nHI"

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

# ==============================================================================
# 🔍 SERPAPI: CANLI GOOGLE GÖRSELLER (BOT KALKANI VE ENGEL YOK)
# ==============================================================================
def search_serpapi_live_image(query: str) -> Optional[str]:
    """Google Images üzerinden bot kalkanına takılmadan doğrudan orijinal görsel URL'si çeker."""
    if not SERPAPI_KEY:
        return None
    try:
        # Sorguyu yemek tariflerini ve fast-food'u eleyecek şekilde filtrele
        refined_query = f"{query} tableware white background studio photography -food -recipe"
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_images",
            "q": refined_query,
            "api_key": SERPAPI_KEY,
            "num": 5
        }
        res = requests.get(url, params=params, timeout=6)
        if res.status_code == 200:
            data = res.json()
            images = data.get("images_results", [])
            for img in images:
                orig = img.get("original")
                if orig and any(orig.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    return orig
                elif orig:
                    return orig
    except Exception as e:
        print(f"[SerpApi Hatası]: {e}")
    return None

# ==============================================================================
# 🧠 MEM0 & PURECEPT FIREBASE KATALOG VE BELLEK KATMANI
# ==============================================================================
def retrieve_purecept_memory_context(sector_hint: str) -> str:
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/purecept_knowledge_base?key={FIREBASE_API_KEY}"
    try:
        res = requests.get(url, timeout=5)
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
                return "\n[PURECEPT STÜDYO VE KATALOG HAFIZASI]:\n" + "\n".join(memory_rules[:4])
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
        requests.patch(url, json={"fields": fields}, timeout=5)
    except Exception as e:
        print(f"[Hafıza Yazma]: {e}")

# ==============================================================================
# 🌐 AÇIK BİLGİ VE AKADEMİK PLATFORMLAR (OPENALEX + EXA AI)
# ==============================================================================
def fetch_openalex_insights(topic: str) -> List[str]:
    query = urllib.parse.quote_plus(f"{topic} ceramic porcelain ergonomics tableware")
    url = f"https://api.openalex.org/works?search={query}&per-page=2"
    insights = []
    try:
        res = requests.get(url, headers={"User-Agent": "PureceptDesignStudio/1.0"}, timeout=4)
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
        res = requests.post(url, headers=headers, json=payload, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"[Exa AI]: {e}")
    return []

# Güvenli yedek görsel havuzu
FALLBACK_PORCELAIN_VAULT = [
    "https://images.pexels.com/photos/4207892/pexels-photo-4207892.jpeg?auto=compress&cs=tinysrgb&w=800",
    "https://images.pexels.com/photos/4207791/pexels-photo-4207791.jpeg?auto=compress&cs=tinysrgb&w=800",
    "https://images.pexels.com/photos/4207788/pexels-photo-4207788.jpeg?auto=compress&cs=tinysrgb&w=800",
    "https://images.pexels.com/photos/4207794/pexels-photo-4207794.jpeg?auto=compress&cs=tinysrgb&w=800"
]

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
    benchmark_reference: str = Field(description="Referans alınan marka ve seri (Örn: Revol Caractère, Bernardaud Ecume)")
    image_search_query: str = Field(description="SerpApi için spesifik ürün arama sorgusu (Örn: Revol Caractere porcelain bowl studio)")
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
# 🤖 ÇOKLU AJAN VE ORKESTRASYON
# ==============================================================================
AGENT_DALIN = """
Sen Purecept Kıdemli Marka ve Ürün Direktörü DALIN'sin.
Görevin: Kullanıcının girdiği sektörü analiz etmek; Firebase stüdyo katalog arşivini, OpenAlex ve Exa AI verilerini sentezleyerek gerçek pazar liderlerini (Benchmark) tespit etmek.
Kural: Asla jenerik konuşma; havacılıkta DeSter, hastanede Bauscher, baristada ACME/Loveramics, fine-dining'de Revol/Bernardaud/Hering Berlin/Churchill standartlarını esas al.
Her pafta için 'image_search_query' alanına Google Görsellerde doğrudan o porseleni bulacak net İngilizce marka+ürün sorgusunu yaz.
"""

AGENT_AUDITOR = """
Sen Purecept Tasarım ve Ergonomi Denetçisisin.
Dalin'in analizini endüstriyel gerçeklik filtresinden geçirirsin:
- İstiflenebilirlik, cidar kalınlığı, salamander fırın direnci, mikronize sır sertliği.
Tutarsız veya amatör önerileri elersin.
"""

@app.get("/")
def root():
    return {
        "status": "online", 
        "engine": "Purecept Dalin SerpApi Live Engine",
        "serpapi_active": True
    }

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

        # SerpApi ile doğrudan canlı Google Images sorgusu yap
        paftas = data.get("product_paftas", [])
        for idx, pafta_data in enumerate(paftas):
            search_q = pafta_data.get("image_search_query") or f"{pafta_data.get('benchmark_reference', '')} {pafta_data.get('product_name', '')}"
            img_url = search_serpapi_live_image(search_q)
            pafta_data["image_url"] = img_url if img_url else FALLBACK_PORCELAIN_VAULT[idx % len(FALLBACK_PORCELAIN_VAULT)]

        # Lansman görseli
        launch_img = search_serpapi_live_image(f"{data.get('target_sector', '')} michelin restaurant interior luxury")
        data["launch_image_url"] = launch_img if launch_img else "https://images.pexels.com/photos/262978/pexels-photo-262978.jpeg?auto=compress&cs=tinysrgb&w=1200"

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
                "memoryType": "Purecept_SerpApi_Key_Connected"
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
