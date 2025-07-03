# chat_server.py
"""
AI Travel Chat Server mit Template
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import asyncio
import uvicorn
import traceback

# Deine OpenAI Integration
from mcp_server import holiday_client

app = FastAPI(title="AI Travel Chat", description="OpenAI + Apify Scraper Chat Interface")

# Templates
templates = Jinja2Templates(directory="templates")

class TravelQuery(BaseModel):
    query: str
    origin: str = "Wien"

@app.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Haupt-Chat-Interface"""
    return templates.TemplateResponse("chat_interface.html", {"request": request})

@app.post("/ai-search")
async def ai_travel_search(request: TravelQuery):
    """AI-gestützte Reisesuche für Chat"""
    
    print(f"🚀 Chat-Anfrage: {request.query}")
    
    try:
        # Vollständige AI-Suche
        result = await holiday_client.call_intelligent_search(request.query, request.origin)
        
        print(f"✅ Chat-Antwort: Success={result.get('success')}")
        return result
        
    except Exception as e:
        print(f"❌ Chat-Fehler: {e}")
        traceback.print_exc()
        return {
            "error": f"Entschuldigung, da ist ein Fehler aufgetreten: {str(e)}",
            "success": False
        }

@app.get("/health")
async def health():
    """Health Check"""
    return {"status": "Chat Server läuft!", "ai": "OpenAI bereit"}

if __name__ == "__main__":
    print("🚀 Starte AI Travel Chat Server...")
    print("💬 Chat Interface: http://localhost:8001")
    print("🤖 AI-Suche: http://localhost:8001/ai-search")
    
    uvicorn.run("chat_server:app", host="0.0.0.0", port=8001, reload=True)