import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
Ahmet Osman Peker'e doğrudan stratejik ve operasyonel ürün yönetimi raporlaması yapıyorsun.

GÖREVİN:
Horeca porselen, barista fincan/kupa ve sofra üstü trendlerini analiz etmek; pazar boşluklarını,
form ergonomisini, sır dokularını ve rakip kıyaslamalarını (Loveramics, Hasami, Serax vb.)
operasyonel bir dille raporlamaktır.
"""

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
    
    # 1. Ön Pazar Taraması
    market_context = ""
    if tavily_client:
        try:
            s_res = tavily_client.search(query=f"{request.message} tableware horeca ceramic coffee cup", max_results=3)
            market_context = "\nPazar Verileri: " + str([r.get('content') for r in s_res.get('results', [])])
        except Exception:
            pass

    # 2. Raporun Yazılması
    prompt = f"{DALIN_SYSTEM_PROMPT}\n{market_context}\n\nKullanıcı Brifingi: {request.message}"
    try:
        report_resp = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        report_text = report_resp.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 3. Spesifik ve Sadece Ürün Odaklı Arama Terimleri Üretme
    image_queries = []
    if tavily_client:
        image_prompt = f"""
        Aşağıdaki raporu incele. Raporda bahsedilen fincan, kupa ve porselenleri görselleştirmek için
        3 adet çok spesifik İngilizce ürün arama terimi üret.
        KRİTİK KURAL: Aramanın sonuna mutlaka 'product photography isolated neutral background tableware' ekle.
        Asla yemek, yiyecek, restoran veya masa araması yapma. Sadece tekil porselen ürününü hedefle.
        Örnek format: ["Loveramics egg cup product photography neutral background", "Hasami porcelain mug isolated tableware", "matte ceramic coffee cup minimalist product"]
        
        Sadece JSON dizi olarak yanıt ver: ["sorgu 1", "sorgu 2", "sorgu 3"]
        
        Rapor:
        {report_text[:1200]}
        """
        try:
            query_resp = gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=image_prompt,
            )
            raw_text = query_resp.text.replace("```json", "").replace("```", "").strip()
            image_queries = json.loads(raw_text)
        except Exception:
            image_queries = [
                "Loveramics egg cup coffee product photography",
                "Hasami porcelain mug stackable tableware product",
                "matte ceramic specialty coffee cup design product"
            ]

    # 4. Görselleri Çekme
    curated_images = []
    if tavily_client and image_queries:
        for q in image_queries[:3]:
            try:
                t_img = tavily_client.search(query=q, max_results=1, include_images=True)
                imgs = t_img.get("images", [])
                if imgs:
                    curated_images.append({
                        "query": q,
                        "url": imgs[0]
                    })
            except Exception:
                pass

    return {
        "reply": report_text,
        "curated_images": curated_images
    }
