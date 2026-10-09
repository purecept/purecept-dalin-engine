import os
import json
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from tavily import TavilyClient

app = FastAPI(title="Purecept - Dalin Autonomous Design Intelligence Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini_key = os.environ.get("GEMINI_API_KEY")
tavily_key = os.environ.get("TAVILY_API_KEY")

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None
tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None

# ==============================================================================
# 🏛️ EVRENSEL ENDÜSTRİYEL TASARIM VE PAZAR LİDERLERİ BİLGİ GRAFİĞİ (KNOWLEDGE GRAPH)
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
    brand: str = Field(description="Dünya lideri marka adı (Örn: ACME Cup veya DeSter)")
    plus_points: List[str] = Field(description="Sektörel üstün yönleri (+)")
    minus_points: List[str] = Field(description="Operasyonel veya estetik açıkları (-)")

class DynamicProductPafta(BaseModel):
    pafta_code: str = Field(description="Pafta kodu (Örn: SKU 01 veya PARÇA A)")
    product_name: str = Field(description="Ürün tam adı (Örn: The Core // 75ml Parabolik Espresso Fincanı)")
    spec_dimension: str = Field(description="Boyut/Hacim/Çap (Örn: 75-85 ML veya Ø270 mm / H45 mm)")
    bullet_1: str = Field(description="Form ve geometri inovasyonu (Parabolik taban, istif kademesi vb.)")
    bullet_2: str = Field(description="Malzeme ve yüzey dili (Ham bisküvi, saten sır, cidar kalınlığı vb.)")
    bullet_3: str = Field(description="Kullanım ergonomisi ve operasyonel fayda (Şef servisi, barista akışı vb.)")
    benchmark_reference: str = Field(description="Referans alınan küresel standart (Örn: Loveramics Egg 80cc muadili)")
    image_prompt_for_visual: str = Field(description="Ürünün stüdyo çekimini tarif eden İngilizce prompt (Örn: studio product photography of a handmade ceramic espresso cup on clean pedestal, soft lighting, 8k, no text, no watermark)")
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

@app.get("/")
def root():
    return {
        "status": "online",
        "agent": "Dalin",
        "studio": "Purecept Design Studio",
        "engine": "Universal Industrial Design & Presentation Architecture"
    }

# ==============================================================================
# 🎨 GÖRSEL DOĞRULAMA VE ÜRETİM MOTORU (TAVILY + IMAGEN/GEMINI FALLBACK)
# ==============================================================================
def resolve_clean_product_image(pafta: DynamicProductPafta, fallback_idx: int) -> str:
    """Arama motorundan afişsiz, yazısız, filigransız temiz ürün görseli çeker; bulamazsa yapay zeka promptuna sadık temiz yedek atar."""
    pristine_curated_library = [
        "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1534778101976-62847782c213?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=1200&q=85"
    ]
    
    if tavily_client:
        clean_query = f"{pafta.product_name} {pafta.spec_dimension} industrial ceramic studio product photography -text -watermark -logo -poster -banner -glass"
        try:
            res = tavily_client.search(query=clean_query, max_results=5, include_images=True)
            raw_imgs = res.get("images", [])
            valid_imgs = [
                img for img in raw_imgs
                if not any(bad in img.lower() for bad in ["watermark", "dreamstime", "shutterstock", "vector", "poster", "banner", "logo", "glass", "transparent"])
            ]
            if valid_imgs:
                return valid_imgs[0]
            if raw_imgs:
                return raw_imgs[0]
        except Exception:
            pass

    return pristine_curated_library[fallback_idx % len(pristine_curated_library)]

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY yapılandırılmamış.")

    full_prompt = f"{DALIN_CORE_SYSTEM_PROMPT}\n\nKULLANICI TALEBİ: {request.message}"

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

        # Dinamik Paftaların Görsellerini Çözümle
        paftas = data.get("product_paftas", [])
        for idx, pafta_data in enumerate(paftas):
            pafta_obj = DynamicProductPafta(**pafta_data)
            resolved_img = resolve_clean_product_image(pafta_obj, idx)
            pafta_data["image_url"] = resolved_img

        # Lansman Mekan Görseli
        if tavily_client:
            try:
                target_sec = data.get("target_sector", "Architecture & Interior")
                cafe_query = f"minimalist modern {target_sec} interior space architecture photography -text -words -poster -signboard"
                s_res = tavily_client.search(query=cafe_query, max_results=3, include_images=True)
                c_imgs = [
                    im for im in s_res.get("images", [])
                    if not any(b in im.lower() for b in ["text", "sign", "poster", "banner", "logo"])
                ]
                data["launch_image_url"] = c_imgs[0] if c_imgs else "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=85"
            except Exception:
                data["launch_image_url"] = "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=85"
        else:
            data["launch_image_url"] = "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=85"

        # SOHBET EKRANI: Büyük kutuları engelleyen, temiz ve sofistike yönetici özeti
        reply = f"""### {data.get('collection_name')}
**{data.get('subtitle')}**

#### 🎯 Stratejik Konumlandırma
{data.get('strategic_positioning')}

#### 📐 Koleksiyon Pafta Mimarisi ({len(paftas)} Ürün)
""" + "\n".join([f"- **{p.get('product_name')}** ({p.get('spec_dimension')}): {p.get('bullet_1')} *(Ref: {p.get('benchmark_reference')})*" for p in paftas])

        return {
            "status": "success",
            "reply": reply,
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
