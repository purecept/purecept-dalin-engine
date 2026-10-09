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
# 🌐 3 AÇIK PLATFORM (OPENALEX + ARXIV + HUGGINGFACE)
# ==============================================================================
def fetch_openalex_insights(topic: str, max_results: int = 2) -> List[str]:
    query = urllib.parse.quote_plus(f"{topic} ceramic porcelain ergonomics tableware")
    url = f"https://api.openalex.org/works?search={query}&per-page={max_results}"
    insights = []
    try:
        res = requests.get(url, headers={"User-Agent": "PureceptDesignStudio/1.0"}, timeout=5)
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
        res = requests.get(url, timeout=5)
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
        res = requests.get(url, headers=headers, timeout=5)
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
# 🧠 MEM0: FIRESTORE REST HAFIZA
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
        requests.patch(url, json={"fields": fields}, timeout=6)
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
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"[Exa AI]: {e}")
    return []

# ==============================================================================
# 🎯 MUTLAK İZOLE PORSELEN HAVUZU (SAAT, OJE, VAZO, MOBİLYA VE CORS ENGELİ YOK)
# ==============================================================================
# Doğrudan test edilmiş, CORS serbest, saf stüdyo porselen ve seramik formları:
PREMIUM_CERAMIC_VAULT = {
    # 1. Heykelsi Amuse-Bouche Pedestal / Monolitik Lokma Kaidesi
    "pedestal": "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=1200&q=85",
    
    # 2. Düz Degüstasyon Sunum Aynası / Şef Tabağı
    "flat_plate": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=1200&q=85",
    
    # 3. Derin Consommé Kasesi / Termal Çanak
    "deep_bowl": "https://images.unsplash.com/photo-1534778101976-62847782c213?auto=format&fit=crop&w=1200&q=85",
    
    # 4. Pre-Dessert Kabı / Asimetrik Tadım Kasesi (Saat yerine saf seramik kase)
    "dessert_cup": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=1200&q=85",
    
    # 5. Paylaşım Platter'ı
    "platter": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=1200&q=85"
}

def resolve_pure_tableware_asset(product_name: str, spec: str, idx: int) -> str:
    """Ürünün tipolojisine göre saat/kol/vazo içermeyen garantili porselen döner."""
    t = f"{product_name} {spec}".lower()
    
    if any(k in t for k in ["pedestal", "kaide", "amuse", "stèle", "monolitik"]):
        return PREMIUM_CERAMIC_VAULT["pedestal"]
        
    if any(k in t for k in ["consomme", "consommé", "kase", "bowl", "cloche", "vortex"]):
        return PREMIUM_CERAMIC_VAULT["deep_bowl"]
        
    if any(k in t for k in ["ayna", "flat", "düz", "degüstasyon", "miroir", "tabak", "plate"]):
        return PREMIUM_CERAMIC_VAULT["flat_plate"]
        
    if any(k in t for k in ["dessert", "pre-dessert", "calix", "pod", "tatlı", "sorbe"]):
        return PREMIUM_CERAMIC_VAULT["dessert_cup"]

    fallback_list = [
        PREMIUM_CERAMIC_VAULT["pedestal"],
        PREMIUM_CERAMIC_VAULT["deep_bowl"],
        PREMIUM_CERAMIC_VAULT["flat_plate"],
        PREMIUM_CERAMIC_VAULT["dessert_cup"]
    ]
    return fallback_list[idx % len(fallback_list)]

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

        # Görselleri doğrudan saf porselen havuzundan eşle
        paftas = data.get("product_paftas", [])
        for idx, pafta_data in enumerate(paftas):
            p_name = pafta_data.get("product_name", "")
            p_spec = pafta_data.get("spec_dimension", "")
            pafta_data["image_url"] = resolve_pure_tableware_asset(p_name, p_spec, idx)

        # Lansman görseli
        data["launch_image_url"] = "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=1200&q=85"

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
                "memoryType": "Purecept_Bulletproof_Vault"
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
