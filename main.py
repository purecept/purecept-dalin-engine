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

DALIN_SYSTEM_PROMPT = """
Sen Purecept Design Studio'nun Kıdemli Marka ve Ürün Yöneticisi olan 'Dalin'sin.
Ahmet Osman Peker'e doğrudan stratejik ürün yönetimi ve pazar konumlandırma raporlaması yapıyorsun.

GÖREVİN:
1. Pazardaki trendleri ve Horeca açıklarını belirlemek.
2. Rakipleri (Loveramics, Hasami, Fellow, notNeutral vb.) tasarım ve saha kullanımı açısından kıyaslamak.
3. Purecept için stratejik 3 SKU'luk koleksiyon mimarisi ve renk/yüzey önerilerini sunmak.

KURAL: Asla ASCII karakterleriyle görsel veya şekil çizmeye çalışma. Metinleri kısa, vurucu ve profesyonel bir ürün yöneticisi diliyle kurgula.
"""

# PDF Şablonuna Birebir Oturacak Veri Yapısı (Pydantic Schema)
class BenchmarkItem(BaseModel):
    brand: str = Field(description="Rakip marka ve koleksiyon adı")
    strengths: str = Field(description="Güçlü yönleri")
    weaknesses: str = Field(description="Operasyonel açığı veya pazar boşluğu")
    purecept_opportunity: str = Field(description="Purecept'in yakalayacağı fırsat")
    product_image_url: Optional[str] = Field(default=None, description="Resmi ürün görseli linki")

class SkuItem(BaseModel):
    name: str = Field(description="SKU Adı (Örn: SKU-01 Cortado & Espresso)")
    volume: str = Field(description="Hacim (Örn: 90 ml)")
    diameter: str = Field(description="Ölçü veya form karakteri")
    target_usage: str = Field(description="Kullanım amacı ve barista ergonomisi")

class DalinReportSchema(BaseModel):
    executive_summary: str = Field(description="Yönetici özeti ve pazar tezi")
    market_gaps: List[str] = Field(description="Tespit edilen 3 kritik pazar boşluğu")
    benchmarks: List[BenchmarkItem] = Field(description="Rakip ürün kıyaslama matrisi")
    sku_architecture: List[SkuItem] = Field(description="Önerilen 3 SKU koleksiyon kurgusu")
    glaze_palette_notes: str = Field(description="Sır, renk ve doku önerileri")
    next_steps: List[str] = Field(description="Sonraki operasyonel adımlar")

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "ok", "agent": "Dalin", "studio": "Purecept Design Studio"}

@app.options("/{full_path:path}")
def preflight_handler():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY bulunamadı.")
    
    # 1. Pazar Araması
    market_context = ""
    if tavily_client:
        try:
            s_res = tavily_client.search(query=f"{request.message} specialty coffee tableware horeca cup benchmark", max_results=3)
            market_context = "\nPazar Verileri: " + str([r.get('content') for r in s_res.get('results', [])])
        except Exception:
            pass

    # 2. Benchmark Görsellerini Toplama
    benchmark_images = {}
    competitors = {
        "Loveramics": "Loveramics Egg coffee cup official product tableware",
        "Hasami": "Hasami porcelain mug stackable official product",
        "Fellow": "Fellow Monty milk art cup ceramic product",
        "notNeutral": "notNeutral Lino coffee cup product photography"
    }
    if tavily_client:
        for brand, q in competitors.items():
            try:
                t_img = tavily_client.search(query=q, max_results=1, include_images=True)
                imgs = t_img.get("images", [])
                if imgs:
                    benchmark_images[brand] = imgs[0]
            except Exception:
                pass

    # 3. Gemini ile Yapılandırılmış Çıktı Üretimi
    full_prompt = f"{DALIN_SYSTEM_PROMPT}\n{market_context}\n\nKullanıcı Talebi: {request.message}"
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=full_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": DalinReportSchema,
            }
        )
        report_data = json.loads(response.text)

        # Bulunan görselleri benchmark objelerine eşle
        for item in report_data.get("benchmarks", []):
            brand_name = item.get("brand", "")
            for key, url in benchmark_images.items():
                if key.lower() in brand_name.lower():
                    item["product_image_url"] = url
                    break

        return {
            "status": "success",
            "data": report_data,
            "benchmark_images": benchmark_images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
