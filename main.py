import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from tavily import TavilyClient

app = FastAPI(title="Purecept - Dalin Engine")

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

# --- GOLD STANDARD SLIDE SCHEMAS ---

class TrendCard(BaseModel):
    title: str = Field(description="Trend başlığı (Örn: Mat Yüzeyler)")
    desc: str = Field(description="Tek cümlelik açıklama (Örn: Dokunma duyusuna hitap eden sırlar.)")

class BenchmarkItem(BaseModel):
    brand: str = Field(description="Marka adı (Örn: Loveramics & Acme)")
    plus_points: List[str] = Field(description="Pozitif özellikler (+)")
    minus_points: List[str] = Field(description="Negatif/eksik yönler (-)")

class SkuSlide(BaseModel):
    volume_tag: str = Field(description="Büyük hacim etiketi (Örn: 75-90 ML)")
    sku_name: str = Field(description="SKU ismi (Örn: SKU 1: The Core)")
    bullet_1: str = Field(description="Örn: Krema Koruması: Hızlı ısı kaybını önleyen yapı.")
    bullet_2: str = Field(description="Örn: Derin Form: U şeklinde parabolik iç taban.")
    bullet_3: str = Field(description="Örn: Odak Noktası: Ev baristaları ve tadım etkinlikleri.")
    image_search_query: str = Field(description="Görsel arama terimi (Örn: cortado ceramic cup table)")
    image_url: Optional[str] = Field(default=None)

class LaunchPillar(BaseModel):
    title: str = Field(description="Saha vizyon başlığı (Örn: Görsel Kimlik)")
    desc: str = Field(description="Açıklama (Örn: Sosyal medya uyumlu, doğal ve sürdürülebilir toprak tonları.)")

class GoldStandardPresentation(BaseModel):
    title: str = Field(default="STRATEJİ VE VİZYON RAPORU")
    collection_name: str = Field(description="Örn: 3. Nesil Barista Fincanı Koleksiyonu")
    subtitle: str = Field(description="Örn: Rakip benchmark analizi, SKU optimizasyonu ve saha lansman öngörüleri.")
    
    # Slayt 2: Dinamikler
    trends_title: str = Field(default="Tüketim Dinamikleri")
    trends_subtitle: str = Field(default="Kahve deneyimini şekillendiren dört temel fiziksel beklenti.")
    trends: List[TrendCard]
    
    # Slayt 3: Benchmark
    benchmarks: List[BenchmarkItem]
    strategic_positioning: str = Field(description="Stratejik konumlandırma tek paragraf vurucu özet")
    
    # Slayt 4, 5, 6: 3 SKU Paftaları (Split Layout)
    sku_slides: List[SkuSlide]
    
    # Slayt 7: Saha Lansman
    launch_title: str = Field(default="Saha Lansman Vizyonu")
    launch_pillars: List[LaunchPillar]
    launch_image_url: Optional[str] = Field(default=None)

class ChatRequest(BaseModel):
    message: str

DALIN_SYSTEM_PROMPT = """
Sen Purecept Design Studio'nun Kıdemli Marka ve Ürün Yöneticisi Dalin'sin.
Ahmet Osman Peker için editoryal, lüks, minimalist bir endüstriyel tasarım sunumu hazırlıyorsun.

KURAL: Asla uzun roman veya bürokratik rapor yazma.
Tam olarak şu altın şablonu (Gold Standard) dolduracaksın:
1. Başlıklar net ve vurucu.
2. 4 Tüketim trendi (Mat Yüzeyler, Latte Art Formu, Isı Kontrolü, Ergonomi gibi).
3. 3 Rakip kıyaslaması (Loveramics, notNeutral, Fellow) ve tek cümlelik 'Stratejik Konumlandırma'.
4. Tam 3 SKU (The Core, The Canvas, The Comfort gibi) - her biri için büyük hacim etiketi ve 3 kısa madde.
5. Saha lansman vizyonu (Görsel Kimlik, Operasyonel Verimlilik, Duyusal Temas gibi 3 sütun).
"""

@app.get("/")
def root():
    return {"status": "ok", "agent": "Dalin", "studio": "Purecept Design Studio"}

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY bulunamadı.")
    
    full_prompt = f"{DALIN_SYSTEM_PROMPT}\n\nKullanıcı Talebi: {request.message}"
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=full_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": GoldStandardPresentation,
            }
        )
        data = json.loads(response.text)

        # Görselleri Tavily ile çekip doğrudan slaytlara gömüyoruz
        if tavily_client:
            # SKU Görselleri
            for sku in data.get("sku_slides", []):
                try:
                    q = sku.get("image_search_query", "ceramic coffee cup specialty cafe")
                    s_res = tavily_client.search(query=q, max_results=1, include_images=True)
                    imgs = s_res.get("images", [])
                    if imgs:
                        sku["image_url"] = imgs[0]
                except Exception:
                    pass
            
            # Lansman / Kafe Görseli
            try:
                s_res = tavily_client.search(query="modern specialty coffee shop cafe interior architecture", max_results=1, include_images=True)
                imgs = s_res.get("images", [])
                if imgs:
                    data["launch_image_url"] = imgs[0]
            except Exception:
                pass

        # Sohbet ekranı için özet
        reply = f"""### {data.get('collection_name')}
**{data.get('subtitle')}**

#### Stratejik Konumlandırma
{data.get('strategic_positioning')}

#### Önerilen Koleksiyon Mimarisi
""" + "\n".join([f"- **{s.get('sku_name')}** ({s.get('volume_tag')}): {s.get('bullet_1')}" for s in data.get('sku_slides', [])])

        return {
            "status": "success",
            "reply": reply,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
