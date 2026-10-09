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

# --- GELİŞMİŞ EDİTORYAL ŞEMA ---

class TrendCard(BaseModel):
    title: str = Field(description="Trend başlığı (Örn: Mat ve Dokunsal Yüzeyler)")
    desc: str = Field(description="Maksimum 2 kısa cümlelik açıklama.")

class TrendColor(BaseModel):
    name: str = Field(description="Renk ismi (Örn: Kalsine Taş Beji)")
    hex_code: str = Field(description="HEX kodu (Örn: #D8CFC2)")
    role: str = Field(description="Kullanım alanı (Örn: Dış Gövde Ham Sır)")

class BenchmarkItem(BaseModel):
    brand: str = Field(description="Marka adı (Örn: Loveramics)")
    plus_points: List[str] = Field(description="2 adet pozitif özellik (+)")
    minus_points: List[str] = Field(description="2 adet eksik/zayıf yön (-)")

class SkuSlide(BaseModel):
    volume_tag: str = Field(description="Hacim etiketi (Örn: 75-90 ML)")
    sku_name: str = Field(description="SKU ismi (Örn: SKU 01: The Core // Espresso & Cortado)")
    bullet_1: str = Field(description="1. Teknik madde (Örn: Krema Koruması: Parabolik iç taban.)")
    bullet_2: str = Field(description="2. Malzeme/Ergonomi maddesi")
    bullet_3: str = Field(description="3. Hedef kullanım senaryosu")
    image_search_query: str = Field(description="Spesifik ürün arama sorgusu")
    image_url: Optional[str] = Field(default=None)

class LaunchPillar(BaseModel):
    title: str = Field(description="Saha vizyon başlığı (Örn: Görsel & Kimliksel Güç)")
    desc: str = Field(description="Kısa açıklama (Maksimum 2 satır)")

class GoldStandardPresentation(BaseModel):
    title: str = Field(default="STRATEJİ VE VİZYON RAPORU")
    collection_name: str = Field(description="Örn: Purecept Artisan: 3. Nesil Barista Koleksiyonu")
    subtitle: str = Field(description="Örn: Rakip benchmark analizi, SKU optimizasyonu ve saha lansman vizyonu.")
    
    # Slayt 2: Dinamikler ve Renk Paleti
    trends_title: str = Field(default="2026 Tüketim Dinamikleri & Trendler")
    trends_subtitle: str = Field(default="Nitelikli kahve deneyimini şekillendiren mikro dinamikler ve renk paleti.")
    trends: List[TrendCard]
    trend_colors: List[TrendColor] = Field(description="Koleksiyon için 4 adet editoryal trend renk")
    
    # Slayt 3: Benchmark
    benchmarks: List[BenchmarkItem]
    strategic_positioning: str = Field(description="Stratejik konumlandırma tek paragraf net özet")
    
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
Kurucu ve Baş Tasarımcı Ahmet Osman Peker için editoryal, lüks, minimalist bir Horeca/Barista sunumu hazırlıyorsun.

KESİN KURALLAR:
1. Başlıklar ve metinler sağa taşmayacak şekilde net ve vurucu olacak. Asla roman yazma.
2. 4 Trend kartı ve koleksiyon için 4 adet 2026/27 Trend Rengi (Kalsine Bej, Mineral Adaçayı, Bazalt Antrasit, Terracotta gibi gerçek HEX kodlarıyla) belirle.
3. 3 Rakip (Loveramics, notNeutral, Fellow) için ikişer maddelik net kıyaslama yap.
4. Tam 3 SKU (The Core: Espresso/Cortado, The Canvas: Flat White/Latte Art, The Comfort: Büyük Kupa/Filtre) tanımla.
5. Saha lansmanı için 3 operasyonel ilke belirle.
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

        # Görselleri Tavily ile katı filtreli olarak çekiyoruz (Cam, filigran, poster ve afiş YASAK)
        if tavily_client:
            sku_clean_queries = [
                "handcrafted ceramic espresso cup stoneware matte glaze studio photography -glass -transparent -watermark -text -stock",
                "ceramic cappuccino cup latte art tulip specialty coffee photography -glass -clear -watermark -text -logo",
                "modern minimalist ceramic coffee mug tactile stoneware table photography -glass -watermark -text -poster"
            ]
            
            for idx, sku in enumerate(data.get("sku_slides", [])):
                try:
                    q = sku_clean_queries[idx % len(sku_clean_queries)]
                    s_res = tavily_client.search(query=q, max_results=5, include_images=True)
                    raw_imgs = s_res.get("images", [])
                    clean_imgs = [
                        img for img in raw_imgs 
                        if not any(bad in img.lower() for bad in ["glass", "transparent", "watermark", "dreamstime", "shutterstock", "banner", "poster", "logo"])
                    ]
                    if clean_imgs:
                        sku["image_url"] = clean_imgs[0]
                    elif raw_imgs:
                        sku["image_url"] = raw_imgs[0]
                except Exception:
                    pass
            
            try:
                q_cafe = "japandi minimalist specialty coffee shop architecture interior photography -sign -text -words -poster"
                s_res = tavily_client.search(query=q_cafe, max_results=5, include_images=True)
                raw_imgs = s_res.get("images", [])
                clean_imgs = [
                    img for img in raw_imgs 
                    if not any(bad in img.lower() for bad in ["sign", "signboard", "neon", "poster", "banner", "watermark", "text"])
                ]
                if clean_imgs:
                    data["launch_image_url"] = clean_imgs[0]
                elif raw_imgs:
                    data["launch_image_url"] = raw_imgs[0]
            except Exception:
                pass

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
