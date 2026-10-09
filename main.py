import os
import json
import requests
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai

app = FastAPI(title="Purecept - Dalin Autonomous Design Intelligence Engine")

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
# 🧠 FIREBASE REST HAFIZA KATMANI (KALICI STÜDYO ÖĞRENME MOTORU)
# ==============================================================================
def save_to_purecept_memory(capsule_id: str, payload: dict):
    """Firestore REST API üzerinden doğrudan 'purecept_knowledge_base' koleksiyonuna yazar."""
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
        print(f"[FIREBASE KAYIT UYARISI]: {e}")

# ==============================================================================
# 🔍 EXA AI NEURAL SEARCH MOTORU (SEKTÖREL ANLAMSAL DERİN ARAMA)
# ==============================================================================
def exa_neural_search(query: str, num_results: int = 3) -> List[Dict]:
    """Exa AI üzerinden doğrudan tasarım standartları, pazar liderleri ve teknik makaleleri tarar."""
    if not exa_key:
        return []
    url = "https://api.exa.ai/search"
    headers = {
        "x-api-key": exa_key,
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "useAutoprompt": True,
        "numResults": num_results,
        "type": "neural",
        "contents": {
            "text": {"maxCharacters": 800}
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"[EXA AI ARAMA UYARISI]: {e}")
    return []

# ==============================================================================
# 🏛️ EVRENSEL ENDÜSTRİYEL SEKTÖR VE PAZAR LİDERLERİ BİLGİ GRAFİĞİ
# ==============================================================================
SECTOR_BENCHMARK_ECOSYSTEM = {
    "aviation": {
        "title": "Havacılık & In-Flight Servis Ekipmanları",
        "leaders": ["DeSter", "gategroup", "Kaelis", "Formia"],
        "core_constraints": "Galley fırın modülleri, türbülans kilitleri, ağırlık/yakıt tasarrufu, kompakt iç içe istif (nesting)."
    },
    "healthcare": {
        "title": "Medikal, Hastane & Bakım Evleri Porselen Sistemleri",
        "leaders": ["Bauscher Klinika", "Schönwald Healthcare", "WMF Professional"],
        "core_constraints": "Termal kapak sızdırmazlığı, 130°C buhar sterilizasyonu, gıda-tabak renk kontrastı, kaymaz taban."
    },
    "fine_dining": {
        "title": "Gastronomi & Degüstasyon Şef Tabaklaması",
        "leaders": ["Revol Porcelaine", "Hering Berlin", "Bernardaud", "J.L Coquet"],
        "core_constraints": "Merkez emülsiyon sos havuzu, negatif alan dengesi, çatal sesi kesen saten sır, şef cımbız ergonomisi."
    },
    "specialty_coffee": {
        "title": "3. Nesil Nitelikli Kahve & Barista Koleksiyonları",
        "leaders": ["ACME Cup (Evo/Roman)", "Loveramics (Egg/Bond)", "notNeutral (LINO/VERO)", "Origami Japan"],
        "core_constraints": "Parabolik latte art tabanı, termal kütle, inceltilmiş dudak payı, başparmak destekli mimari kulp."
    },
    "marine_superyacht": {
        "title": "Lüks Ağırlama, Süperyat & Marina Gastronomisi",
        "leaders": ["Dibbern", "Vista Alegre", "Narumi Fine Bone China"],
        "core_constraints": "Yüksek darbe ve çentik direnci, yalpa açısına karşı ağırlık merkezi dengesi, lüks dokunsal saten doku."
    }
}

# ==============================================================================
# 📐 DİNAMİK SUNUM VE PAFTA VERİ ŞEMALARI (SINIRSIZ SKU & TİPOLOJİ)
# ==============================================================================
class TrendCard(BaseModel):
    title: str = Field(description="Trend başlığı (Örn: Mat Mineral Sırlar veya Hafifletilmiş Petek Gövde)")
    desc: str = Field(description="Maksimum 2 cümlelik teknik ve operasyonel açıklama.")

class TrendColor(BaseModel):
    name: str = Field(description="Renk adı (Örn: Kalsine Taş Beji)")
    hex_code: str = Field(description="HEX formatında renk kodu (Örn: #D8CFC2)")
    role: str = Field(description="Uygulama yüzeyi (Örn: Dış Gövde Ham Sır)")

class BenchmarkAnalysisItem(BaseModel):
    brand: str = Field(description="Dünya lideri marka adı (Örn: ACME Cup, DeSter, Bauscher)")
    plus_points: List[str] = Field(description="Sektörel üstün yönleri (+)")
    minus_points: List[str] = Field(description="Operasyonel veya estetik açıkları (-)")

class DynamicProductPafta(BaseModel):
    pafta_code: str = Field(description="Pafta kodu (Örn: SKU 01 veya PARÇA A)")
    product_name: str = Field(description="Ürün tam adı (Örn: The Core // 75ml Parabolik Espresso Fincanı)")
    spec_dimension: str = Field(description="Boyut/Hacim/Çap (Örn: 75-85 ML veya Ø270 mm / H45 mm)")
    bullet_1: str = Field(description="Form ve geometri inovasyonu (Parabolik taban, istif kademesi vb.)")
    bullet_2: str = Field(description="Malzeme ve yüzey dili (Ham bisküvi, saten sır, cidar kalınlığı vb.)")
    bullet_3: str = Field(description="Kullanım ergonomisi ve operasyonel fayda (Şef servisi, barista akışı vb.)")
    benchmark_reference: str = Field(description="Referans alınan küresel pazar standardı (Örn: ACME Cup Evo / Loveramics Egg muadili)")
    image_url: Optional[str] = Field(default=None)

class LaunchVisionPillar(BaseModel):
    title: str = Field(description="Saha vizyon ilkesi başlığı (Örn: Görsel Heykelsilik)")
    desc: str = Field(description="Maksimum 2 satırlık saha ve operasyon açıklaması.")

class UniversalPresentationDeck(BaseModel):
    title: str = Field(default="STRATEJİ VE VİZYON RAPORU")
    collection_name: str = Field(description="Koleksiyon resmi proje adı")
    subtitle: str = Field(description="Alt başlık ve stratejik hedef tanımı")
    target_sector: str = Field(description="Hedef sektör (Barista, Fine-Dining, Medikal, Havacılık vb.)")
    
    # Slayt 2: Dinamikler & Renk
    trends_title: str = Field(default="Tüketim Dinamikleri & Pazar Trendleri")
    trends_subtitle: str = Field(default="Deneyimi şekillendiren mikro dinamikler ve renk kartelası.")
    trends: List[TrendCard] = Field(description="Tam 4 adet pazar trend kartı")
    trend_colors: List[TrendColor] = Field(description="Koleksiyon için 4 adet 2026/27 trend rengi")
    
    # Slayt 3: Benchmark & Konumlandırma
    benchmarks: List[BenchmarkAnalysisItem] = Field(description="Sektör lideri 3 küresel markanın analizi")
    strategic_positioning: str = Field(description="Tek paragraf vurucu stratejik konumlandırma tezi")
    
    # Slayt 4+: Dinamik SKU Paftaları (Kaç ürün gerekliyse o kadar)
    product_paftas: List[DynamicProductPafta] = Field(description="Dinamik ürün paftaları listesi")
    
    # Son Slayt: Lansman & Saha
    launch_title: str = Field(default="Saha Lansman ve Entegrasyon Vizyonu")
    launch_pillars: List[LaunchVisionPillar] = Field(description="3 adet operasyonel entegrasyon sütunu")
    launch_image_url: Optional[str] = Field(default=None)

class ChatRequest(BaseModel):
    message: str

# ==============================================================================
# 🧠 DALIN SYSTEM PROMPT
# ==============================================================================
DALIN_CORE_SYSTEM_PROMPT = """
Sen Purecept Design Studio'nun Kıdemli Marka, Ürün ve Trend Direktörü DALIN'sin.
Baş Tasarımcı Ahmet Osman Peker için dünya çapında pazar analizi ve editoryal ürün koleksiyonu stratejisi kurguluyorsun.

TEMEL PRENSİPLER:
1. ALAN VE TİPOLOJİ BAĞIMSIZLIĞI (DOMAIN AGNOSTIC):
   - Konu sadece kahve fincanı olmak zorunda değildir. Kullanıcı uçak içi porselen, hastane bakım evleri, fine-dining şef tabaklaması veya el yapımı zanaat serisi isteyebilir.
   - İlgili sektörün dünya liderlerini (Havacılıkta DeSter, Medikalde Bauscher, Fine-dining'de Revol, Baristada ACME & Loveramics) doğrudan bilerek strateji kuracaksın.
2. DİNAMİK ÜRÜN PAFTASI (ESNEK SKU):
   - Sabit 3 ürün kısıtlaması yoktur. Kullanıcının talebine ve koleksiyonun büyüklüğüne göre gereken sayıda (2, 3, 4, 5 veya daha fazla) eksiksiz 'DynamicProductPafta' üreteceksin.
3. EDİTORYAL DİL & HİTAP KURALI:
   - "Ahmet Bey" hitabını asla kullanma; vizyoner, sofistike ve kararlı bir iş ortağı dili kullan.
   - Cümleleri sağa taşmayacak, net ve vurucu tut.
"""

# Kaliteli ve güvenli editoryal görsel kitaplığı (Yazısız, filigransız, stüdyo kalitesi)
PRISTINE_CURATED_LIBRARY = [
    "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=1200&q=85",
    "https://images.unsplash.com/photo-1534778101976-62847782c213?auto=format&fit=crop&w=1200&q=85",
    "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=1200&q=85",
    "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=1200&q=85",
    "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=1200&q=85"
]

@app.get("/")
def root():
    return {
        "status": "online",
        "agent": "Dalin",
        "studio": "Purecept Design Studio",
        "search_engine": "Exa AI Neural Search Connected",
        "memory_storage": "Firebase Firestore Connected"
    }

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY yapılandırılmamış.")

    # 1. Aşama: Exa AI ile Sektörel Anlamsal İstihbarat Çekme
    neural_insights = exa_neural_search(f"industrial design technical specifications standards {request.message}", num_results=2)
    research_context = ""
    if neural_insights:
        research_context = "\n[EXA AI NEURAL SEKTÖREL İSTİHBARAT]:\n" + "\n".join([f"- {r.get('title')}: {r.get('text', '')[:300]}" for r in neural_insights])

    full_prompt = f"{DALIN_CORE_SYSTEM_PROMPT}\n{research_context}\n\nKULLANICI TALEBİ: {request.message}"

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=full_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": UniversalPresentationDeck,
                "temperature": 0.2
            }
        )
        data = json.loads(response.text)

        # 2. Aşama: Dinamik Pafta Görsellerini Eşleme
        paftas = data.get("product_paftas", [])
        for idx, pafta_data in enumerate(paftas):
            pafta_data["image_url"] = PRISTINE_CURATED_LIBRARY[idx % len(PRISTINE_CURATED_LIBRARY)]

        # Lansman Mekan Görseli (Saf mimari iç mekan)
        data["launch_image_url"] = "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=85"

        # 3. Aşama: Öğrenilen Bilgiyi Kalıcı Firestore Hafızasına Kaydetme
        try:
            safe_name = str(data.get("collection_name", "proje")).replace(" ", "_").lower()[:30]
            capsule_id = f"capsule-dalin-{safe_name}"
            save_to_purecept_memory(capsule_id, {
                "agentId": "dalin",
                "topic": str(data.get("collection_name", "")),
                "targetSector": str(data.get("target_sector", "")),
                "strategicPositioning": str(data.get("strategic_positioning", "")),
                "skuCount": len(paftas),
                "benchmarks": data.get("benchmarks", []),
                "source": "Exa AI Neural Search & Gemini 3.8 Flash"
            })
        except Exception as fb_err:
            print(f"[HAFIZA KAYIT HATASI]: {fb_err}")

        # 4. Aşama: Sohbet Ekranı İçin Temiz Yönetici Özeti
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
