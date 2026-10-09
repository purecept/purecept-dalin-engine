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
form ergonomisini, sır dokularını ve rakip kıyaslamalarını (Loveramics, Hasami, Fellow, Serax vb.)
operasyonel bir dille raporlamaktır.

KURAL: Raporlarında asla ASCII karakterleriyle çizim, ok şeması veya anlamsız metin grafikleri (|/\\|, +---+, (O)) üretme. Teknik parametreleri temiz markdown listeleri ve tablolar halinde ver.
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
    
    # 1. Pazar verisi taraması
    market_context = ""
    if tavily_client:
        try:
            s_res = tavily_client.search(query=f"{request.message} specialty coffee tableware horeca cup benchmark", max_results=3)
            market_context = "\nPazar Verileri: " + str([r.get('content') for r in s_res.get('results', [])])
        except Exception:
            pass

    # 2. Rapor metni
    prompt = f"{DALIN_SYSTEM_PROMPT}\n{market_context}\n\nKullanıcı Brifingi: {request.message}"
    try:
        report_resp = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        report_text = report_resp.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 3. Kıyaslanan rakiplerin gerçek ürün görsellerini nokta atışı çek
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

    return {
        "reply": report_text,
        "benchmark_images": benchmark_images
    }
