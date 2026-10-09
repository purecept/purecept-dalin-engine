import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from tavily import TavilyClient

app = FastAPI(title="Purecept - Dalin Engine")

gemini_key = os.environ.get("GEMINI_API_KEY")
tavily_key = os.environ.get("TAVILY_API_KEY")

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None
tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None

DALIN_SYSTEM_PROMPT = (
    "Sen Purecept Design Studio bünyesinde Kıdemli Marka ve Ürün Yöneticisi olan 'Dalin'sin. "
    "Doğrudan Stüdyo Kurucusu Ahmet Osman Peker'e raporlama yapıyorsun. "
    "Görevlerin: Horeca porselen, stoneware, sofra üstü ürün koleksiyonları ve stüdyo projeleri için "
    "pazar analizi, marka stratejisi, ürün konumlandırma, katalog metinleri ve trend öngörüleri sunmaktır. "
    "Profesyonel, analitik, net, tasarım ve gastronomi terminolojisine hakim, operasyonel bir dille yanıt ver."
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "ok", "agent": "Dalin", "studio": "Purecept Design Studio"}

@app.post("/chat")
def chat(request: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY bulunamadı.")
    
    context = ""
    if tavily_client:
        try:
            search_res = tavily_client.search(query=request.message, max_results=2)
            context = "\nGüncel Pazar Verileri: " + str([r.get('content') for r in search_res.get('results', [])])
        except Exception:
            pass

    full_prompt = f"{DALIN_SYSTEM_PROMPT}\n{context}\n\nKullanıcı: {request.message}"
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        return {"reply": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
