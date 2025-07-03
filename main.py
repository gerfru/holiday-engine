# main.py - Saubere Version mit korrekten Klassennamen
"""
Erweitert deine bestehende Holiday Engine um intelligente MCP-fähige Endpoints
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import os

# Lade .env File
from dotenv import load_dotenv
load_dotenv()

# Deine bestehenden Imports mit korrekten Klassennamen
from services.city_resolver import CityResolverService
from services.flight_service import FlightService
from services.hotel_service import AccommodationService
from business_logic import TravelCombinationEngine
from config.settings import Settings

app = FastAPI(title="Holiday Engine", description="Intelligent Travel Search Platform")

# Deine bestehenden Services
city_resolver = CityResolverService()

# API Client für Services (aus deiner utils)
from utils.api_client import ApifyClient
api_token = os.getenv("APIFY_TOKEN", "demo_token")  # Aus .env oder Demo-Token
api_client = ApifyClient(api_token)

flight_service = FlightService(api_client)
hotel_service = AccommodationService(api_client)
combination_engine = TravelCombinationEngine()
settings = Settings()

# Templates für Web-UI (optional)
try:
    templates = Jinja2Templates(directory="templates")
    WEB_UI_AVAILABLE = True
except Exception:
    WEB_UI_AVAILABLE = False
    templates = None
    print("⚠️ Templates Ordner nicht gefunden - Web-UI deaktiviert")


# Pydantic Models für MCP Integration
class IntelligentSearchRequest(BaseModel):
    query: str
    origin: Optional[str] = "Wien"


class StandardSearchRequest(BaseModel):
    origin: str
    destination: str
    outbound_date: str
    return_date: str


class LLMAnalysisRequest(BaseModel):
    text: str
    analysis_type: Optional[str] = "travel_query"


# === MCP-FÄHIGE ENDPOINTS ===

@app.post("/api/intelligent-search")
async def intelligent_search_endpoint(request: IntelligentSearchRequest) -> Dict[str, Any]:
    """
    Intelligente Reisesuche mit natürlichsprachlicher Eingabe
    Dieser Endpoint wird vom MCP Server aufgerufen
    """
    return {"error": "Intelligente Suche nicht implementiert"}


@app.post("/api/llm-analysis")
async def llm_analysis_endpoint(request: LLMAnalysisRequest) -> Dict[str, Any]:
    """LLM-Analyse für verschiedene Texttypen"""
    return {"analysis": "LLM-Analyse nicht verfügbar", "type": request.analysis_type}


@app.get("/api/optimize-dates")
async def optimize_dates_endpoint(
    destination: str,
    travel_type: Optional[str] = "leisure",
    budget_max: Optional[int] = None,
    duration_days: Optional[str] = "7"
) -> Dict[str, Any]:
    """Datums-Optimierung basierend auf verschiedenen Faktoren"""
    return {
        "destination": {"city": destination},
        "optimized_dates": [],
        "note": "Datums-Optimierung nicht verfügbar - OpenAI API Key erforderlich"
    }


# === ERWEITERTE BESTEHENDE ENDPOINTS ===

@app.post("/api/search")
async def enhanced_search_endpoint(request: StandardSearchRequest) -> Dict[str, Any]:
    """
    Erweitert deinen bestehenden Search Endpoint um MCP-Kompatibilität
    """
    
    try:
        # Deine bestehende Suchlogik mit korrekten Parameter-Namen
        # Nutze search_round_trip für Hin- und Rückflug
        flight_results = await flight_service.search_round_trip(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.outbound_date,
            return_date=request.return_date
        )
        
        # search_round_trip gibt ein Dict zurück, extrahiere die Flüge
        flights = []
        if isinstance(flight_results, dict):
            flights.extend(flight_results.get('outbound', []))
            flights.extend(flight_results.get('inbound', []))
        else:
            flights = flight_results
        
        hotels = await hotel_service.search_hotels(
            destination=request.destination,
            check_in=request.outbound_date,
            check_out=request.return_date
        )
        
        # Deine bestehende Combination Logic
        combinations = await combination_engine.create_combinations(flights, hotels)
        
        # Zusätzliche Metadaten für MCP
        mcp_metadata = {
            "search_timestamp": "2025-07-03T12:00:00Z",
            "total_options": len(combinations),
            "best_score": combinations[0].get("score", 0) if combinations else 0,
            "mcp_compatible": True
        }
        
        return {
            "flights": flights,
            "hotels": hotels, 
            "combinations": combinations,
            "metadata": mcp_metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Suche: {str(e)}")


# === MCP STATUS ENDPOINTS ===

@app.get("/api/mcp/status")
async def mcp_status() -> Dict[str, Any]:
    """Status-Check für MCP Integration"""
    
    return {
        "mcp_enabled": True,
        "intelligent_search_available": False,
        "llm_integration": False,
        "services_status": {
            "city_resolver": "active",
            "flight_service": "active", 
            "hotel_service": "active",
            "intelligent_search": "unavailable"
        },
        "supported_features": [
            "basic_search",
            "standard_dates", 
            "rule_based_analysis",
            "basic_recommendations"
        ]
    }


@app.get("/api/mcp/tools")
async def mcp_tools_info() -> Dict[str, Any]:
    """Information über verfügbare MCP Tools"""
    
    return {
        "tools": [
            {
                "name": "intelligent_travel_search",
                "description": "Intelligente Reisesuche mit natürlichsprachlicher Eingabe",
                "endpoint": "/api/intelligent-search",
                "example_query": "Finde mir etwas Romantisches in Italien unter 1000€ im Dezember",
                "available": False
            },
            {
                "name": "standard_travel_search", 
                "description": "Standard strukturierte Reisesuche",
                "endpoint": "/api/search",
                "required_params": ["origin", "destination", "outbound_date", "return_date"],
                "available": True
            },
            {
                "name": "city_autocomplete",
                "description": "Stadtsuche mit Autocomplete",
                "endpoint": "/api/cities/autocomplete",
                "example_query": "Mala",
                "available": True
            },
            {
                "name": "optimize_dates",
                "description": "Datums-Optimierung für Reisen",
                "endpoint": "/api/optimize-dates",
                "parameters": ["destination", "travel_type", "budget_max", "duration_days"],
                "available": False
            }
        ],
        "mcp_server_command": "python mcp_server.py",
        "mcp_config_example": {
            "mcpServers": {
                "holiday-engine": {
                    "command": "python",
                    "args": ["/path/to/mcp_server.py"]
                }
            }
        }
    }


# === DEINE BESTEHENDEN ENDPOINTS ===

@app.get("/")
async def root(request: Request):
    """Homepage - nur wenn Templates verfügbar"""
    if not WEB_UI_AVAILABLE:
        return {"message": "Holiday Engine API", "docs": "/docs", "mcp_status": "/api/mcp/status"}
    
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Dein bestehender Health Check"""
    return {"status": "healthy", "mcp_enabled": True}


@app.get("/api/cities/autocomplete")
async def city_autocomplete(q: str):
    """City Autocomplete - angepasst an deine Service-Methoden"""
    try:
        # Dein CityResolver hat keine autocomplete_cities, also simulieren wir es
        # mit resolve_to_iata für bekannte Städte
        result = await city_resolver.resolve_to_iata(q)
        
        # Formatiere als Liste für Autocomplete - TUPLE KORREKT HANDHABEN
        if result and isinstance(result, tuple) and result[0]:
            iata_code = result[0]  # Erster Wert ist IATA
            city_name = result[1]  # Zweiter Wert ist Name
            return [{
                "name": city_name, 
                "iata_code": iata_code, 
                "display_name": f"{city_name} ({iata_code})"
            }]
        else:
            return []
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"City Autocomplete Fehler: {str(e)}")


@app.get("/api/cities/resolve")
async def resolve_city(city: str):
    """City Resolver - angepasst an deine Service-Methoden"""
    try:
        result = await city_resolver.resolve_to_iata(city)
        
        # TUPLE KORREKT HANDHABEN
        if result and isinstance(result, tuple) and result[0]:
            iata_code = result[0]  # Erster Wert ist IATA
            city_name = result[1]  # Zweiter Wert ist Name
            return {
                "city": city_name,
                "airport_code": iata_code,
                "success": True
            }
        else:
            return {
                "city": city,
                "airport_code": None,
                "success": False,
                "error": "No IATA code found"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"City Resolver Fehler: {str(e)}")


# === STARTUP EVENT ===

@app.on_event("startup")
async def startup_event():
    """Initialisierung beim App-Start"""
    
    print("🚀 Holiday Engine gestartet!")
    print("🧠 MCP Integration vorbereitet")
    print("💡 Für LLM-Features: services/intelligent_search_service.py und services/openai_llm_service.py hinzufügen")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )