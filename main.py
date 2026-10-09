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

# API Bilgileri
gemini_key = os.environ.get("GEMINI_API_KEY")
exa_key = os.environ.get("EXA_API_KEY", "f1d719aa-2cb1-48ea-b346-d16f5d0871b4").strip()
hf_token = os.environ.get("HF_TOKEN", "").strip()

FIREBASE_PROJECT_ID = "purecept-studio"
FIREBASE_API_KEY = "AIzaSyCXW75WiHdylqW1gD7Ngw8dGlbU3rl-nHI"

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

# ==============================================================================
# 🌐 3 AÇIK BİLGİ PLATFORMU (OPENALEX + ARXIV + HUGGINGFACE)
# ==============================================================================
def fetch_openalex_insights(topic: str, max_results: int = 2) -> List[str]:
    query = urllib.parse.quote_plus(f"{topic} ceramic porcelain ergonomics tableware")
    url = f"https://api.openalex.org/works?search={query}&per-page={max_results}"
    insights = []
    try:
        res = requests.get(url, headers={"User-Agent": "PureceptDesignStudio/1.0"}, timeout=4)
        if res.status_code == 200:
            results = res.json().get("results", [])
            for r in results:
                title = r.get("title", "")
                inv_abs = r.get("abstract_inverted_index")
                abstract = ""
                if inv_abs:
                    words = sorted([(pos, w) for w, positions in inv_abs.items() for pos in positions])
                    abstract = " ".join([w for _, w in words])[:200]
                if title:
                    insights.append(f"• [OpenAlex]: {title} - {abstract}")
    except Exception as e:
        print(f"[OpenAlex]: {e}")
    return insights

def fetch_arxiv_insights(topic: str, max_results: int = 2) -> List[str]:
    query = urllib.parse.quote_plus(f"all:{topic} AND (all:ceramic OR all:ergonomics OR all:design)")
    url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={max_results}"
    insights = []
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            root = ET.fromstring(res.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                t_text = title.text.strip().replace("\n", " ") if title is not None else ""
                s_text = summary.text.strip().replace("\n", " ")[:200] if summary is not None else ""
                if t_text:
                    insights.append(f"• [ArXiv]: {t_text} - {s_text}")
    except Exception as e:
        print(f"[ArXiv]: {e}")
    return insights

def fetch_huggingface_insights(topic: str, max_results: int = 2) -> List[str]:
    query = urllib.parse.quote_plus(topic)
    url = f"https://huggingface.co/api/datasets?search={query}&limit={max_results}"
    insights = []
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200:
            datasets = res.json()
            for ds in datasets:
                ds_id = ds.get("id", "")
                desc = ds.get("description", "")[:150] if ds.get("description") else "Tasarım normu"
                if ds_id:
                    insights.append(f"• [HuggingFace]: {ds_id} - {desc}")
    except Exception as e:
        print(f"[HuggingFace]: {e}")
    return insights

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
# 🔍 EXA AI NEURAL SEARCH
# ==============================================================================
def exa_neural_search(query: str, num_results: int = 3) -> List[Dict]:
    if not exa_key:
        return []
    url = "https://api.exa.ai/search"
    headers = {"x-api-key": exa_key, "Content-Type": "application/json"}
    payload = {
        "query": query,
        "useAutoprompt": True,
        "numResults": num_results,
        "type": "neural",
        "contents": {"text": {"maxCharacters": 800}}
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"[Exa AI]: {e}")
    return []

# ==============================================================================
# 📐 DETERMINISTIK VEKTÖREL PAFTA MOTORU (HARİCİ STOK FOTOĞRAFLARA TAM VEDA)
# ==============================================================================
def generate_deterministic_ceramic_svg(product_name: str, spec: str, pafta_code: str) -> str:
    """Ürünün tipolojisine göre kusursuz, stüdyo kalitesinde vektörel kesit üretir."""
    t = f"{product_name} {spec}".lower()
    
    # 1. Heykelsi Monolit Kaide (Amuse-Bouche)
    if any(k in t for k in ["pedestal", "kaide", "amuse", "stèle", "monolit"]):
        svg_content = f'''<svg xmlns="http://www.w3.org/2005/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <rect width="800" height="800" fill="#18191B"/>
  <circle cx="400" cy="400" r="320" fill="none" stroke="#2A2C30" stroke-width="1.5" stroke-dasharray="4,8"/>
  <path d="M 280 620 L 320 280 Q 400 240 480 280 L 520 620 Z" fill="#E6E2DC" stroke="#C5BFB5" stroke-width="2"/>
  <ellipse cx="400" cy="280" rx="80" ry="24" fill="#D4CDC3" stroke="#B0A89B" stroke-width="2"/>
  <ellipse cx="400" cy="275" rx="35" ry="10" fill="#18191B" opacity="0.35"/>
  <text x="400" y="710" text-anchor="middle" fill="#8E8B82" font-family="monospace" font-size="20" letter-spacing="4">{pafta_code} // MONOLITHIC PEDESTAL</text>
  <text x="400" y="745" text-anchor="middle" fill="#5F5D56" font-family="sans-serif" font-size="14">{spec}</text>
</svg>'''

    # 2. Parabolik Derin Kuyu Kase (Consommé)
    elif any(k in t for k in ["consomme", "consommé", "kase", "bowl", "cloche", "vortex", "çorba"]):
        svg_content = f'''<svg xmlns="http://www.w3.org/2005/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <rect width="800" height="800" fill="#18191B"/>
  <circle cx="400" cy="400" r="320" fill="none" stroke="#2A2C30" stroke-width="1.5" stroke-dasharray="4,8"/>
  <ellipse cx="400" cy="380" rx="300" ry="85" fill="#E6E2DC" stroke="#C5BFB5" stroke-width="2"/>
  <ellipse cx="400" cy="380" rx="140" ry="42" fill="#CEC7BC" stroke="#B0A89B" stroke-width="2"/>
  <path d="M 260 380 Q 400 580 540 380 Z" fill="#B5ADA0" opacity="0.45"/>
  <text x="400" y="710" text-anchor="middle" fill="#8E8B82" font-family="monospace" font-size="20" letter-spacing="4">{pafta_code} // DEEP PARABOLIC BOWL</text>
  <text x="400" y="745" text-anchor="middle" fill="#5F5D56" font-family="sans-serif" font-size="14">{spec}</text>
</svg>'''

    # 3. Pre-Dessert Kabı / İzotermal Coupelle
    elif any(k in t for k in ["dessert", "pre-dessert", "calix", "pod", "tatlı", "sorbe"]):
        svg_content = f'''<svg xmlns="http://www.w3.org/2005/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <rect width="800" height="800" fill="#18191B"/>
  <circle cx="400" cy="400" r="320" fill="none" stroke="#2A2C30" stroke-width="1.5" stroke-dasharray="4,8"/>
  <path d="M 310 560 C 260 400 300 280 400 280 C 500 280 540 400 490 560 Z" fill="#E6E2DC" stroke="#C5BFB5" stroke-width="2"/>
  <ellipse cx="400" cy="310" rx="75" ry="25" fill="#CEC7BC" stroke="#B0A89B" stroke-width="2"/>
  <ellipse cx="400" cy="560" rx="45" ry="12" fill="#A8A093"/>
  <text x="400" y="710" text-anchor="middle" fill="#8E8B82" font-family="monospace" font-size="20" letter-spacing="4">{pafta_code} // ISOTHERMAL COUPELLE</text>
  <text x="400" y="745" text-anchor="middle" fill="#5F5D56" font-family="sans-serif" font-size="14">{spec}</text>
</svg>'''

    # 4. Ultra Düz Degüstasyon Sunum Aynası (Varsayılan & Düz Tabaklar)
    else:
        svg_content = f'''<svg xmlns="http://www.w3.org/2005/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <rect width="800" height="800" fill="#18191B"/>
  <circle cx="400" cy="400" r="320" fill="none" stroke="#2A2C30" stroke-width="1.5" stroke-dasharray="4,8"/>
  <ellipse cx="400" cy="400" rx="330" ry="105" fill="#E6E2DC" stroke="#C5BFB5" stroke-width="2"/>
  <ellipse cx="400" cy="400" rx="275" ry="85" fill="#F4F2EE" stroke="#DDD8CF" stroke-width="1.5"/>
  <ellipse cx="400" cy="400" rx="190" ry="58" fill="none" stroke="#D1CBC0" stroke-width="1" stroke-dasharray="3,6"/>
  <text x="400" y="710" text-anchor="middle" fill="#8E8B82" font-family="monospace" font-size="20" letter-spacing="4">{pafta_code} // RIMLESS TASTING MIRROR</text>
  <text x="400" y="745" text-anchor="middle" fill="#5F5D56" font-family="sans-serif" font-size="14">{spec}</text>
</svg>'''

    encoded = urllib.parse.quote(svg_content)
    return f"data:image/svg+xml;utf8,{encoded}"

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
    benchmark_reference: str = Field(description="Referans standart")
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
Görevin: Kullanıcının girdiği sektörü analiz etmek; Exa AI, OpenAlex, ArXiv ve Hugging Face arşivlerini sentezleyerek gerçek pazar liderlerini (Benchmark) tespit etmek.
Kural: Asla jenerik konuşma; havacılıkta DeSter, hastanede Bauscher, baristada ACME/Loveramics, fine-dining'de Revol/Bernardaud/Hering Berlin standartlarını esas al.
"""

AGENT_AUDITOR = """
Sen Purecept Tasarım ve Ergonomi Denetçisisin.
Dalin'in analizini endüstriyel gerçeklik filtresinden geçirirsin:
- İstiflenebilirlik, cidar kalınlığı, salamander fırın direnci, mikronize sır sertliği.
Tutarsız veya amatör önerileri elersin.
"""

@app.get("/")
def root():
    return {"status": "online", "studio": "Purecept Design Studio"}

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY eksik.")

    memory_context = retrieve_purecept_memory_context(request.message[:40])
    
    neural_insights = exa_neural_search(f"tableware ergonomics porcelain standards {request.message}", num_results=2)
    exa_context = ""
    if neural_insights:
        exa_context = "\n[EXA AI PAZAR İSTİHBARATI]:\n" + "\n".join([f"- {r.get('title')}: {r.get('text', '')[:300]}" for r in neural_insights])

    openalex_res = fetch_openalex_insights(request.message[:30], max_results=2)
    arxiv_res = fetch_arxiv_insights(request.message[:30], max_results=2)
    hf_res = fetch_huggingface_insights(request.message[:30], max_results=2)
    academic_context = "\n".join(openalex_res + arxiv_res + hf_res)
    if academic_context:
        academic_context = "\n[AÇIK BİLGİ PLATFORMLARI]:\n" + academic_context

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

        # Görselleri artık ASLA rastgele fotoğraflardan çekmiyoruz; deterministik SVG pafta üretiyoruz:
        paftas = data.get("product_paftas", [])
        for idx, pafta_data in enumerate(paftas):
            p_code = pafta_data.get("pafta_code", f"SKU 0{idx+1}")
            p_name = pafta_data.get("product_name", "")
            p_spec = pafta_data.get("spec_dimension", "")
            pafta_data["image_url"] = generate_deterministic_ceramic_svg(p_name, p_spec, p_code)

        # Lansman görseli için garantili saf minimalist salon SVG'si
        launch_svg = '''<svg xmlns="http://www.w3.org/2005/svg" viewBox="0 0 1200 675" width="100%" height="100%">
  <rect width="1200" height="675" fill="#141517"/>
  <rect x="200" y="380" width="800" height="15" fill="#EAE6DF" rx="4"/>
  <rect x="280" y="395" width="20" height="200" fill="#242528"/>
  <rect x="900" y="395" width="20" height="200" fill="#242528"/>
  <ellipse cx="600" cy="350" rx="140" ry="32" fill="#E6E2DC" stroke="#C5BFB5" stroke-width="1.5"/>
  <ellipse cx="600" cy="350" rx="90" ry="20" fill="#CEC7BC"/>
  <circle cx="600" cy="180" r="1.5" fill="#FFF" opacity="0.8"/>
  <path d="M 600 0 L 600 260" stroke="#4F5157" stroke-width="1.5"/>
  <path d="M 570 260 L 630 260 L 615 285 L 585 285 Z" fill="#D4AF37"/>
  <polygon points="600,285 450,380 750,380" fill="url(#coneGrad)" opacity="0.08"/>
  <defs>
    <linearGradient id="coneGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FFF"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <text x="600" y="620" text-anchor="middle" fill="#8E8B82" font-family="monospace" font-size="16" letter-spacing="6">MICHELIN OPERATIONAL ARCHITECTURE // FIELD DEPLOYMENT</text>
</svg>'''
        data["launch_image_url"] = f"data:image/svg+xml;utf8,{urllib.parse.quote(launch_svg)}"

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
                "memoryType": "Purecept_ZeroStock_Deterministic_Engine"
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
