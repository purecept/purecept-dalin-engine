import os
import json
import requests
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai

app = FastAPI(title="Purecept - Dalin Autonomous Multi-Agent & Memory Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ve Servis Bilgileri
gemini_key = os.environ.get("GEMINI_API_KEY")
exa_key = os.environ.get("EXA_API_KEY", "f1d719aa-2cb1-48ea-b346-d16f5d0871b4").strip()

FIREBASE_PROJECT_ID = "purecept-studio"
FIREBASE_API_KEY = "AIzaSyCXW75WiHdylqW1gD7Ngw8dGlbU3rl-nHI"

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

# ==============================================================================
# 🧠 MEM0 MİMARİSİ: FIRESTORE REST HAFIZA KATMANI
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
        print(f"[HAFIZA OKUMA HATASI]: {e}")
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
        print(f"[HAFIZA YAZMA HATASI]: {e}")

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
        print(f"[EXA AI HATASI]: {e}")
    return []

# ==============================================================================
# 🖼️ SAF PORSELEN VE EDİTORYAL ÜRÜN KÜTÜPHANESİ (YEMEKSİZ & STÜDYO ÇEKİMİ)
# ==============================================================================
# Asla kaburga, et, patates veya vazo içermeyen doğrulanmış porselen/seramik ürünleri:
STUDIO_PORCELAIN_ASSETS = {
    # 1. Düz Şef Servis Aynası / Düz Tabak / Fine-Dining Platter
    "flat_plate": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=1200&q=85",
    # 2. Derin Kase / Infusion Kasesi / Çorba Haznesi
    "deep_bowl": "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=1200&q=85",
    # 3. Heykelsi Monolitik Kaide / Amuse-Bouche Pedestal / Tadım Tabağı
    "pedestal": "https://images.unsplash.com/photo-1615529182904-14819c35db37?auto=format&fit=crop&w=1200&q=85",
    # 4. Asimetrik Gurme Tabak / Organik Formlu Porselen
    "organic_plate": "https://images.unsplash.com/photo-1590736969955-71cc94801759?auto=format&fit=crop&w=1200&q=85",
    # 5. Pre-Dessert / Coupelle / Tatlı Kasesi
    "dessert_coupelle": "https://images.unsplash.com/photo-1576020799627-aeac76d580dc?auto=format&fit=crop&w=1200&q=85",
    # 6. Oval Paylaşım Platter'ı / Geniş Servis
    "oval_platter": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=1200&q=85",
    # 7. Barista / Kahve Fincanı (Sadece kahve istendiğinde)
    "coffee_cup": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=1200&q=85"
}

def resolve_pristine_tableware_image(sector: str, name: str, spec: str, idx: int) -> str:
    """Yemek/et fotoğraflarını engelleyen doğrudan saf porselen nesne seçici."""
    text = f"{sector} {name} {spec}".lower()
    
    # Kahve Fincaları (Sadece kahve projesiyse)
    if any(k in text for k in ["espresso", "cappuccino", "latte", "flat white", "barista", "fincan", "kupa"]):
        return STUDIO_PORCELAIN_ASSETS["coffee_cup"]

    # Amuse-Bouche / Kaide / Pedestal / Caviar
    if any(k in text for k in ["amuse", "pedestal", "kaide", "caviar", "kule", "monolitik"]):
        return STUDIO_PORCELAIN_ASSETS["pedestal"]
        
    # Pre-Dessert / Tatlı / Coupelle / Finale
    if any(k in text for k in ["dessert", "tatlı", "coupelle", "finale", "sorbe", "cocoon"]):
        return STUDIO_PORCELAIN_ASSETS["dessert_coupelle"]

    # Derin Kase / Çorba / Infusion / Kuyu
    if any(k in text for k in ["kase", "bowl", "infusion", "çorba", "derin kuyu", "deep well"]):
        return STUDIO_PORCELAIN_ASSETS["deep_bowl"]

    # Oval Platter / Paylaşım / Geniş Tepsi
    if any(k in text for k in ["platter", "paylaşım", "oval", "tepsi", "servis"]):
        return STUDIO_PORCELAIN_ASSETS["oval_platter"]

    # Asimetrik Düz Tabak / Degüstasyon / Şef Aynası
    if any(k in text for k in ["asymmetric", "asimetrik", "organik"]):
        return STUDIO_PORCELAIN_ASSETS["organic_plate"]

    # Standart Düz Tabak / Main Course / Flat Plate
    if any(k in text for k in ["flat", "tabak", "plate", "starter", "ana yemek", "degüstasyon", "ayna"]):
        return STUDIO_PORCELAIN_ASSETS["flat_plate"]

    # Döngüsel Güvenli Liste
    safe_rotation = [
        STUDIO_PORCELAIN_ASSETS["flat_plate"],
        STUDIO_PORCELAIN_ASSETS["deep_bowl"],
        STUDIO_PORCELAIN_ASSETS["pedestal"],
        STUDIO_PORCELAIN_ASSETS["dessert_coupelle"]
    ]
    return safe_rotation[idx % len(safe_rotation)]

# ==============================================================================
# 📐 DİNAMİK SUNUM VE PAFTA VERİ ŞEMALARI
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
Görevin: Kullanıcının girdiği sektörü analiz etmek, Exa AI pazar istihbaratını okumak ve bu sektörün dünyadaki gerçek pazar liderlerini (Benchmark) tespit ederek boşlukları çıkarmak.
Kural: Asla jenerik konuşma; havacılık ise DeSter/Kaelis, hastane ise Bauscher/Schönwald, barista ise ACME/Loveramics, fine-dining ise Revol/Bernardaud/Hering Berlin üzerinden git.
"""

AGENT_AUDITOR_FILTER = """
Sen Purecept Kıdemli Tasarım ve Ergonomi Denetçisisin.
Dalin'in pazar analizini endüstriyel gerçeklik filtresinden geçirirsin:
- Formlar operasyonda kırılgan mı, istiflenebilir mi (stackable)?
- Yüzey dokusu çizilmeye ve lekeye dayanıklı mı?
- Ölçüler ve cidar kalınlıkları sektörün fiziksel standartlarıyla örtüşüyor mu?
Saçma, uydurma veya tutarsız önerileri reddedip rafine hale getirirsin.
"""

@app.get("/")
def root():
    return {
        "status": "online",
        "agent": "Dalin (Multi-Agent Debate & Pristine Ceramic Assets)",
        "studio": "Purecept Design Studio"
    }

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY eksik.")

    # 1. Hafıza Taraması (Mem0)
    memory_context = retrieve_purecept_memory_context(request.message[:40])

    # 2. Exa AI Canlı Derin Pazar Araması
    neural_insights = exa_neural_search(f"tableware ergonomics porcelain standards {request.message}", num_results=2)
    research_context = ""
    if neural_insights:
        research_context = "\n[EXA AI CANLI SEKTÖREL İSTİHBARAT]:\n" + "\n".join([f"- {r.get('title')}: {r.get('text', '')[:300]}" for r in neural_insights])

    # 3. Orkestrasyon
    orchestration_prompt = f"""
{AGENT_DALIN_RESEARCHER}

{AGENT_AUDITOR_FILTER}

Sentez Kuralı:
Baş Tasarımcı Ahmet Osman Peker için eksiksiz, pazar lideri referanslı, lüks ve uygulanabilir bir 'UniversalPresentationDeck' oluşturun.
- Sabit SKU kısıtı yoktur; kullanıcının ihtiyacına göre dinamik sayıda 'DynamicProductPafta' üretin.
- 'Ahmet Bey' hitabını asla kullanmayın.

{memory_context}
{research_context}

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

        # 4. Saf Porselen Görsellerini Eşle (Fast-food/kaburga tamamen engellendi)
        paftas = data.get("product_paftas", [])
        sec = data.get("target_sector", "")
        for idx, pafta_data in enumerate(paftas):
            p_name = pafta_data.get("product_name", "")
            p_spec = pafta_data.get("spec_dimension", "")
            pafta_data["image_url"] = resolve_pristine_tableware_image(sec, p_name, p_spec, idx)

        # Lansman Mekanı: Sektöre uygun mimari alan
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

        # 5. Hafıza Kaydı (Firestore REST)
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
                "memoryType": "Mem0_MultiAgent_Verified_Knowledge"
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
