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

# ==============================================================================
# 🔑 API VE HİZMET TANIMLARI
# ==============================================================================
gemini_key = os.environ.get("GEMINI_API_KEY")
exa_key = os.environ.get("EXA_API_KEY", "f1d719aa-2cb1-48ea-b346-d16f5d0871b4").strip()
hf_token = os.environ.get("HF_TOKEN", "").strip()

FIREBASE_PROJECT_ID = "purecept-studio"
FIREBASE_API_KEY = "AIzaSyCXW75WiHdylqW1gD7Ngw8dGlbU3rl-nHI"

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

# ==============================================================================
# 🌐 1. PLATFORM: OPENALEX API (ÜCRETSİZ & ANAHTARSIZ AKADEMİK ARŞİV)
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
        print(f"[OpenAlex Uyarısı]: {e}")
    return insights

# ==============================================================================
# 🌐 2. PLATFORM: ARXIV REST API (ÜCRETSİZ & ANAHTARSIZ MÜHENDİSLİK ARŞİVİ)
# ==============================================================================
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
        print(f"[ArXiv Uyarısı]: {e}")
    return insights

# ==============================================================================
# 🌐 3. PLATFORM: HUGGING FACE HUB API (AÇIK VERİ SETİ VE MODEL ONTOLOJİSİ)
# ==============================================================================
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
                desc = ds.get("description", "")[:150] if ds.get("description") else "Tasarım/Endüstri veri seti"
                if ds_id:
                    insights.append(f"• [HuggingFace Dataset]: {ds_id} - {desc}")
    except Exception as e:
        print(f"[HuggingFace Uyarısı]: {e}")
    return insights

# ==============================================================================
# 🧠 MEM0 MİMARİSİ: KALICI STÜDYO HAFIZASI (FIRESTORE REST)
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
        print(f"[HAFIZA OKUMA UYARISI]: {e}")
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
        print(f"[HAFIZA YAZMA UYARISI]: {e}")

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
        print(f"[EXA AI UYARISI]: {e}")
    return []

# ==============================================================================
# 🖼️ SAF PORSELEN VE EDİTORYAL ÜRÜN KÜTÜPHANESİ
# ==============================================================================
STUDIO_PORCELAIN_ASSETS = {
    "flat_plate": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=1200&q=85",
    "deep_bowl": "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=1200&q=85",
    "pedestal": "https://images.unsplash.com/photo-1615529182904-14819c35db37?auto=format&fit=crop&w=1200&q=85",
    "organic_plate": "https://images.unsplash.com/photo-1590736969955-71cc94801759?auto=format&fit=crop&w=1200&q=85",
    "dessert_coupelle": "https://images.unsplash.com/photo-1576020799627-aeac76d580dc?auto=format&fit=crop&w=1200&q=85",
    "oval_platter": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=1200&q=85",
    "coffee_cup": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=1200&q=85"
}

def resolve_pristine_tableware_image(sector: str, name: str, spec: str, idx: int) -> str:
    text = f"{sector} {name} {spec}".lower()
    if any(k in text for k in ["espresso", "cappuccino", "latte", "flat white", "barista", "fincan", "kupa"]):
        return STUDIO_PORCELAIN_ASSETS["coffee_cup"]
    if any(k in text for k in ["amuse", "pedestal", "kaide", "caviar", "kule", "monolitik"]):
        return STUDIO_PORCELAIN_ASSETS["pedestal"]
    if any(k in text for k in ["dessert", "tatlı", "coupelle", "finale", "sorbe", "cocoon"]):
        return STUDIO_PORCELAIN_ASSETS["dessert_coupelle"]
    if any(k in text for k in ["kase", "bowl", "infusion", "çorba", "derin kuyu", "deep well"]):
        return STUDIO_PORCELAIN_ASSETS["deep_bowl"]
    if any(k in text for k in ["platter", "paylaşım", "oval", "tepsi", "servis"]):
        return STUDIO_PORCELAIN_ASSETS["oval_platter"]
    if any(k in text for k in ["asymmetric", "asimetrik", "organik"]):
        return STUDIO_PORCELAIN_ASSETS["organic_plate"]
    if any(k in text for k in ["flat", "tabak", "plate", "starter", "ana yemek", "degüstasyon", "ayna"]):
        return STUDIO_PORCELAIN_ASSETS["flat_plate"]

    safe_rotation = [
        STUDIO_PORCELAIN_ASSETS["flat_plate"],
        STUDIO_PORCELAIN_ASSETS["deep_bowl"],
        STUDIO_PORCELAIN_ASSETS["pedestal"],
        STUDIO_PORCELAIN_ASSETS["dessert_coupelle"]
    ]
    return safe_rotation[idx % len(safe_rotation)]

# ==============================================================================
# 📐 DİNAMİK VERİ ŞEMALARI
# ==============================================================================
class TrendCard(BaseModel):
    title: str = Field(description="Trend başlığı")
    desc: str = Field(description="Maksimum 2 cümlelik teknik ve operasyonel açıklama.")

class TrendColor(BaseModel):
    name: str = Field(description="Renk adı")
    hex_code: str = Field(description="HEX renk kodu (Örn: #D8CFC2)")
    role: str = Field(description="Uygulama yüzeyi")

class BenchmarkAnalysisItem(BaseModel):
    brand: str = Field(description="Dünya lideri marka adı")
    plus_points: List[str] = Field(description="Sektörel üstün yönleri (+)")
    minus_points: List[str] = Field(description="Operasyonel veya estetik açıkları (-)")

class DynamicProductPafta(BaseModel):
    pafta_code: str = Field(description="Pafta kodu (Örn: SKU 01)")
    product_name: str = Field(description="Ürün tam adı")
    spec_dimension: str = Field(description="Boyut/Hacim/Çap")
    bullet_1: str = Field(description="Form ve geometri inovasyonu")
    bullet_2: str = Field(description="Malzeme ve yüzey dili")
    bullet_3: str = Field(description="Kullanım ergonomisi ve operasyonel fayda")
    benchmark_reference: str = Field(description="Referans alınan küresel pazar standardı")
    image_url: Optional[str] = Field(default=None)

class LaunchVisionPillar(BaseModel):
    title: str = Field(description="Saha vizyon ilkesi başlığı")
    desc: str = Field(description="Maksimum 2 satırlık saha ve operasyon açıklaması.")

class UniversalPresentationDeck(BaseModel):
    title: str = Field(default="STRATEJİ VE VİZYON RAPORU")
    collection_name: str = Field(description="Koleksiyon resmi proje adı")
    subtitle: str = Field(description="Alt başlık ve stratejik hedef tanımı")
    target_sector: str = Field(description="Hedef sektör")
    
    trends_title: str = Field(default="Tüketim Dinamikleri & Pazar Trendleri")
    trends_subtitle: str = Field(default="Deneyimi şekillendiren mikro dinamikler ve renk kartelası.")
    trends: List[TrendCard]
    trend_colors: List[TrendColor]
    
    benchmarks: List[BenchmarkAnalysisItem]
    strategic_positioning: str = Field(description="Tek paragraf vurucu stratejik konumlandırma tezi")
    
    product_paftas: List[DynamicProductPafta]
    
    launch_title: str = Field(default="Saha Lansman ve Entegrasyon Vizyonu")
    launch_pillars: List[LaunchVisionPillar]
    launch_image_url: Optional[str] = Field(default=None)

class ChatRequest(BaseModel):
    message: str

# ==============================================================================
# 🤖 ÇOKLU AJAN (MULTI-AGENT DEBATE)
# ==============================================================================
AGENT_DALIN_RESEARCHER = """
Sen Purecept Kıdemli Marka ve Ürün Direktörü DALIN'sin.
Görevin: Kullanıcının girdiği sektörü analiz etmek; Exa AI, OpenAlex, ArXiv ve Hugging Face bilgi havuzlarını sentezleyerek gerçek pazar liderlerini (Benchmark) tespit etmek.
Kural: Asla jenerik konuşma; havacılıkta DeSter, hastanede Bauscher, baristada ACME/Loveramics, fine-dining'de Revol/Bernardaud standartlarını esas al.
"""

AGENT_AUDITOR_FILTER = """
Sen Purecept Kıdemli Tasarım ve Ergonomi Denetçisisin.
Dalin'in analizini endüstriyel gerçeklik filtresinden geçirirsin:
- Formlar operasyonda kırılgan mı, istiflenebilir mi (stackable)?
- Yüzey dokusu çizilmeye ve lekeye dayanıklı mı?
- Ölçüler ve cidar kalınlıkları sektörün fiziksel standartlarıyla örtüşüyor mu?
Saçma veya tutarsız önerileri reddedip rafine hale getirirsin.
"""

@app.get("/")
def root():
    return {
        "status": "online",
        "agent": "Dalin (OpenAlex, ArXiv, HuggingFace & Exa AI Engine Connected)",
        "studio": "Purecept Design Studio"
    }

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY eksik.")

    # 1. Hafıza Taraması (Mem0)
    memory_context = retrieve_purecept_memory_context(request.message[:40])

    # 2. Exa AI Canlı Ticari Arama
    neural_insights = exa_neural_search(f"tableware ergonomics porcelain standards {request.message}", num_results=2)
    exa_context = ""
    if neural_insights:
        exa_context = "\n[EXA AI PAZAR İSTİHBARATI]:\n" + "\n".join([f"- {r.get('title')}: {r.get('text', '')[:300]}" for r in neural_insights])

    # 3. Üç Açık Bilgi Havuzu Sorgusu (OpenAlex + ArXiv + Hugging Face)
    openalex_res = fetch_openalex_insights(request.message[:30], max_results=2)
    arxiv_res = fetch_arxiv_insights(request.message[:30], max_results=2)
    hf_res = fetch_huggingface_insights(request.message[:30], max_results=2)
    
    academic_blocks = openalex_res + arxiv_res + hf_res
    academic_context = ""
    if academic_blocks:
        academic_context = "\n[AÇIK BİLGİ HAVUZLARI (OPENALEX + ARXIV + HUGGINGFACE)]:\n" + "\n".join(academic_blocks)

    # 4. Çoklu Ajan Konsensüsü
    orchestration_prompt = f"""
{AGENT_DALIN_RESEARCHER}

{AGENT_AUDITOR_FILTER}

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
            contents=orchestration_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": UniversalPresentationDeck,
                "temperature": 0.2
            }
        )
        data = json.loads(response.text)

        # 5. Saf Seramik Görsellerini Eşle
        paftas = data.get("product_paftas", [])
        sec = data.get("target_sector", "")
        for idx, pafta_data in enumerate(paftas):
            p_name = pafta_data.get("product_name", "")
            p_spec = pafta_data.get("spec_dimension", "")
            pafta_data["image_url"] = resolve_pristine_tableware_image(sec, p_name, p_spec, idx)

        # Lansman Mekanı
        sec_lower = str(sec).lower()
        if any(w in sec_lower for w in ["yat", "yacht", "marin", "marine", "deniz"]):
            data["launch_image_url"] = "https://images.unsplash.com/photo-1567899378494-47b22a2ae96a?auto=format&fit=crop&w=1200&q=85"
        elif any(w in sec_lower for w in ["hastane", "hospital", "sağlık", "medikal"]):
            data["launch_image_url"] = "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=1200&q=85"
        elif any(w in sec_lower for w in ["uçak", "aviation", "flight", "air"]):
            data["launch_image_url"] = "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=1200&q=85"
        elif any(w in sec_lower for w in ["fine-dining", "gastronomi", "şef", "chef", "restoran"]):
            data["launch_image_url"] = "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=1200&q=85"
        else:
            data["launch_image_url"] = "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=85"

        # 6. Hafıza Kaydı (Firestore REST)
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
                "memoryType": "Mem0_MultiPlatform_Learned_Knowledge"
            })
        except Exception as fb_err:
            print(f"[HAFIZA KAYIT HATASI]: {fb_err}")

        # Sohbet Ekranı İçin Temiz Yönetici Özeti
        reply = f"""### {data.get('collection_name')}
**{data.get('subtitle')}**

#### 🎯 Stratejik Konumlandırma
{data.get('strategic_positioning')}

#### 📐 Koleksiyon Pafta Mimarisi ({len(paftas)} Parça)
""" + "\n".join([f"- **{p.get('product_name')}** ({p.get('spec_dimension')}): {p.get('bullet_1')} *(Benchmark: {p.get('benchmark_reference')})*" for p in paftas])

        return {
            "status": "success",
            "reply": reply,
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
