import os
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

GÖREVLERİN:
1. Küresel gastronomi, Horeca porselen, barista kupa/fincan ve sofra üstü trendlerini araştırmak.
2. Sahadaki boşlukları (operasyonel dayanım, şeflerin tabaklama ergonomisi, istiflenebilirlik, pazar doygunluğu) tespit etmek.
3. Rakipleri (Churchill, Steelite, 1616 Arita, Serax, Loveramics, Kinto vb.) analiz edip Purecept için konumlandırma stratejisi ve SKU mimarisi çıkarmak.
4. Raporlarında kullandığın argümanları doğrulamak için gerçek pazar ve ürün referanslarını kullanmak.

KURAL: Raporlarında asla sıradan yemek tarifleri veya alakasız restoran stok görselleri referans verme; odak noktan her zaman endüstriyel sofra üstü ürünleri, porselen tipolojisi, sır dokusu ve sunum ergonomisidir.
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
    
    context = ""
    found_images = []
    
    if tavily_client:
        try:
            # Sektörel pazar araması ve doğrudan ürün görsellerini toplama
            search_res = tavily_client.search(
                query=f"{request.message} tableware porcelain horeca design benchmark", 
                max_results=4,
                include_images=True
            )
            context = "\nSektörel Pazar Verileri: " + str([r.get('content') for r in search_res.get('results', [])])
            found_images = search_res.get('images', [])[:4]
        except Exception:
            pass

    full_prompt = f"{DALIN_SYSTEM_PROMPT}\n{context}\n\nKullanıcı Talebi: {request.message}"
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=full_prompt,
        )
        return {
            "reply": response.text,
            "reference_images": found_images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
