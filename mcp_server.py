# mcp_server.py
"""
MCP Server für Holiday Engine - Mit OpenAI Integration
"""

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, CallToolResult
import asyncio
import httpx
import json
import os
from typing import Dict, Any
import sys

# Für lokale Entwicklung - Pfad zu deiner Holiday Engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Lade .env File
from dotenv import load_dotenv
load_dotenv()

# OpenAI LLM Service importieren
from services.openai_llm_service import OpenAILLMService

# MCP Server initialisieren
server = Server("holiday-engine-intelligent")

class HolidayEngineMCPClient:
    """MCP Client der mit deiner bestehenden Holiday Engine kommuniziert"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # OpenAI LLM Service initialisieren
        try:
            self.llm_service = OpenAILLMService()
            print("✅ OpenAI LLM Service erfolgreich initialisiert")
        except Exception as e:
            print(f"❌ OpenAI Initialisierung fehlgeschlagen: {e}")
            self.llm_service = None
    
    async def call_intelligent_search_with_openai(self, query: str, origin: str = "Wien") -> Dict[str, Any]:
        """Führt intelligente Suche mit OpenAI LLM durch"""
        
        if not self.llm_service:
            return {"error": "OpenAI LLM Service nicht verfügbar"}
        
        try:
            # 1. OpenAI analysiert die Anfrage
            print(f"🤖 Analysiere Anfrage mit OpenAI: '{query}'")
            query_analysis = await self.llm_service.analyze_travel_query(query)
            
            # 2. Nutze die Analyse für deine Standard-Suche
            destination = query_analysis.get("destination", "Italien")
            duration = query_analysis.get("duration_days", [7, 7])
            
            # Sichere Datums-Generierung
            from datetime import datetime, timedelta
            if isinstance(duration, list) and len(duration) >= 2:
                duration_days = duration[0] if duration[0] is not None else 7
            elif isinstance(duration, list) and len(duration) == 1:
                duration_days = duration[0] if duration[0] is not None else 7
            else:
                duration_days = 7  # Default
            
            check_in = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            check_out = (datetime.now() + timedelta(days=30 + duration_days)).strftime("%Y-%m-%d")
            
            # 3. Rufe deine Holiday Engine auf
            print(f"🔍 Suche in Holiday Engine: {origin} → {destination}")
            search_results = await self.call_standard_search(origin, destination, check_in, check_out)
            
            if "error" in search_results:
                return search_results
            
            # 4. OpenAI generiert intelligente Empfehlungen
            print("💡 Generiere Empfehlungen mit OpenAI...")
            recommendations = await self.llm_service.generate_travel_recommendations(
                {"search_results": [{"combinations": [{"flight": search_results.get("flights", [{}])[0] if search_results.get("flights") else {}, 
                                                      "hotel": search_results.get("hotels", [{}])[0] if search_results.get("hotels") else {},
                                                      "total_price": 1000}]}]}, 
                query_analysis
            )
            
            # 5. Optional: Optimierungsvorschläge
            optimizations = await self.llm_service.optimize_search_parameters(query, search_results)
            
            return {
                "query_analysis": query_analysis,
                "search_results": search_results,
                "ai_recommendations": recommendations,
                "optimizations": optimizations,
                "llm_used": "OpenAI GPT-4",
                "success": True
            }
            
        except Exception as e:
            return {"error": f"Intelligente Suche fehlgeschlagen: {str(e)}"}
    
    async def call_intelligent_search(self, query: str, origin: str = "Wien") -> Dict[str, Any]:
        """Wrapper für intelligente Suche"""
        
        if self.llm_service:
            return await self.call_intelligent_search_with_openai(query, origin)
        else:
            return await self.call_standard_search_fallback(query, origin)
    
    async def call_standard_search(self, origin: str, destination: str, 
                                 outbound_date: str, return_date: str) -> Dict[str, Any]:
        """Fallback: Nutze deine bestehende Standard-Suche"""
        
        try:
            # Erst City Resolution
            city_response = await self.client.get(
                f"{self.base_url}/api/cities/resolve",
                params={"city": destination}
            )
            
            if city_response.status_code == 200:
                city_data = city_response.json()
                
                # Dann Standard-Suche
                search_response = await self.client.post(
                    f"{self.base_url}/api/search",
                    json={
                        "origin": origin,
                        "destination": city_data.get("airport_code", destination),
                        "outbound_date": outbound_date,
                        "return_date": return_date
                    }
                )
                
                if search_response.status_code == 200:
                    return search_response.json()
            
            return {"error": "Search failed"}
            
        except Exception as e:
            return {"error": f"Search error: {str(e)}"}
    
    async def call_standard_search_fallback(self, query: str, origin: str) -> Dict[str, Any]:
        """Fallback-Suche ohne LLM - einfache Regel-basierte Analyse"""
        
        # Einfache Destination-Extraktion
        query_lower = query.lower()
        destination = "Italien"  # Default
        
        if "spanien" in query_lower or "spain" in query_lower:
            destination = "Spanien"
        elif "griechenland" in query_lower or "greece" in query_lower:
            destination = "Griechenland"
        elif "frankreich" in query_lower or "france" in query_lower:
            destination = "Frankreich"
        
        # Standarddaten generieren
        from datetime import datetime, timedelta
        check_in = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")
        
        # Standard-Suche aufrufen
        results = await self.call_standard_search(origin, destination, check_in, check_out)
        
        if "error" not in results:
            results["fallback_mode"] = True
            results["note"] = "Suchergebnisse ohne LLM-Analyse - für intelligente Empfehlungen OpenAI API Key setzen"
        
        return results

# Globaler Client
holiday_client = HolidayEngineMCPClient()

@server.call_tool()
async def intelligent_travel_search(arguments: dict) -> CallToolResult:
    """
    Intelligente Reisesuche mit natürlichsprachlicher Eingabe
    
    Args:
        query: Natürlichsprachliche Reiseanfrage (z.B. "Finde mir etwas Romantisches in Italien unter 1000€")
        origin: Abflugort (optional, Standard: Wien)
    """
    
    query = arguments.get("query", "")
    origin = arguments.get("origin", "Wien")
    
    if not query:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="❌ Bitte geben Sie eine Reiseanfrage ein."
            )]
        )
    
    # Rufe intelligente Suche auf
    results = await holiday_client.call_intelligent_search(query, origin)
    
    if "error" in results:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Fehler bei der Suche: {results['error']}"
            )]
        )
    
    # Formatiere Antwort
    response_text = format_intelligent_search_response(results, query)
    
    return CallToolResult(
        content=[TextContent(type="text", text=response_text)]
    )


@server.call_tool()
async def standard_travel_search(arguments: dict) -> CallToolResult:
    """
    Standard Reisesuche mit strukturierten Parametern
    
    Args:
        origin: Abflugort
        destination: Reiseziel
        outbound_date: Hinflugdatum (YYYY-MM-DD)
        return_date: Rückflugdatum (YYYY-MM-DD)
    """
    
    origin = arguments.get("origin", "")
    destination = arguments.get("destination", "")
    outbound_date = arguments.get("outbound_date", "")
    return_date = arguments.get("return_date", "")
    
    if not all([origin, destination, outbound_date, return_date]):
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="❌ Bitte alle Parameter angeben: origin, destination, outbound_date, return_date"
            )]
        )
    
    # Rufe Standard-Suche auf
    results = await holiday_client.call_standard_search(
        origin, destination, outbound_date, return_date
    )
    
    if "error" in results:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Fehler bei der Suche: {results['error']}"
            )]
        )
    
    # Formatiere Antwort
    response_text = format_standard_search_response(results, origin, destination)
    
    return CallToolResult(
        content=[TextContent(type="text", text=response_text)]
    )


@server.call_tool()
async def city_autocomplete(arguments: dict) -> CallToolResult:
    """
    City Autocomplete - nutzt deinen bestehenden Service
    
    Args:
        query: Stadtname für Autocomplete
    """
    
    query = arguments.get("query", "")
    
    if not query:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="❌ Bitte geben Sie einen Stadtnamen ein."
            )]
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{holiday_client.base_url}/api/cities/autocomplete",
                params={"q": query}
            )
            
            if response.status_code == 200:
                cities = response.json()
                
                if cities:
                    city_list = "\n".join([
                        f"🌍 {city.get('display_name', city.get('name', 'Unknown'))} "
                        f"({city.get('country', 'Unknown')})"
                        for city in cities[:10]  # Top 10
                    ])
                    
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"🔍 Gefundene Städte für '{query}':\n\n{city_list}"
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Keine Städte gefunden für '{query}'"
                        )]
                    )
            
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Fehler bei der Stadtsuche: {str(e)}"
            )]
        )


def format_intelligent_search_response(results: Dict[str, Any], original_query: str) -> str:
    """Formatiert die Antwort der intelligenten Suche"""
    
    response = f"""🎯 **Intelligente Reisesuche**

**Ihre Anfrage:** "{original_query}"

"""
    
    # Query Analysis
    if "query_analysis" in results:
        analysis = results["query_analysis"]
        response += f"""**🔍 Analyse Ihrer Anfrage:**
📍 Destination: {analysis.get('destination', 'N/A')}
💰 Budget: {analysis.get('budget_max', 'Flexibel')}€
📅 Dauer: {analysis.get('duration_days', 'N/A')} Tage
🎭 Reisetyp: {analysis.get('travel_type', 'N/A')}

"""
    
    # Best Recommendations
    if "search_results" in results and results["search_results"].get("search_results"):
        best_result = results["search_results"]["search_results"][0]
        
        if best_result.get("combinations"):
            best_combo = best_result["combinations"][0]
            
            response += f"""**🏆 Beste Empfehlung:**
✈️ **Flug:** {best_combo.get('flight', {}).get('airline', 'N/A')} - {best_combo.get('flight', {}).get('price_eur', 'N/A')}€
🏨 **Hotel:** {best_combo.get('hotel', {}).get('name', 'N/A')} ({best_combo.get('hotel', {}).get('rating', 'N/A')}⭐)
📅 **Reisedatum:** {best_result.get('date_option', {}).get('check_in', 'N/A')} bis {best_result.get('date_option', {}).get('check_out', 'N/A')}
💰 **Gesamtkosten:** {best_combo.get('total_price', 'N/A')}€
📊 **Optimierungsscore:** {best_result.get('date_option', {}).get('optimization_score', {}).get('total', 'N/A')}/100

"""
        
        # Alternative Options
        if len(results["search_results"]["search_results"]) > 1:
            response += "**🔄 Alternative Optionen:**\n"
            for i, result in enumerate(results["search_results"]["search_results"][1:3], 2):
                if result.get("combinations"):
                    combo = result["combinations"][0]
                    response += f"""
**Option {i}:**
✈️ {combo.get('flight', {}).get('airline', 'N/A')} - {combo.get('flight', {}).get('price_eur', 'N/A')}€
🏨 {combo.get('hotel', {}).get('name', 'N/A')} ({combo.get('hotel', {}).get('rating', 'N/A')}⭐)
📅 {result.get('date_option', {}).get('check_in', 'N/A')} bis {result.get('date_option', {}).get('check_out', 'N/A')}
💰 {combo.get('total_price', 'N/A')}€
"""
    
    # Recommendations
    if "recommendations" in results:
        recommendations = results["recommendations"]
        if isinstance(recommendations.get("llm_recommendations"), str):
            response += f"\n**💡 Persönliche Empfehlungen:**\n{recommendations['llm_recommendations']}"
        else:
            response += f"""
**💡 Persönliche Empfehlungen:**
• {recommendations.get('best_option', 'Beste Option verfügbar')}
• {recommendations.get('alternatives', 'Alternative Daten prüfen')}
• {recommendations.get('tips', 'Weitere Tipps verfügbar')}
"""
    
    response += f"""

📞 **Nächste Schritte:**
• Prüfen Sie die Buchungslinks für Flug und Hotel
• Vergleichen Sie die verschiedenen Datumoptionen
• Bei Fragen zur Buchung stehe ich gerne zur Verfügung
"""
    
    return response


def format_standard_search_response(results: Dict[str, Any], origin: str, destination: str) -> str:
    """Formatiert die Antwort der Standard-Suche"""
    
    response = f"""🔍 **Suchergebnisse: {origin} → {destination}**

"""
    
    # Flights
    flights = results.get("flights", [])
    if flights:
        response += f"✈️ **Flüge gefunden:** {len(flights)}\n"
        
        # Top 3 Flüge
        for i, flight in enumerate(flights[:3], 1):
            response += f"""
**Flug {i}:**
🛫 {flight.get('airline', 'N/A')} - {flight.get('price_eur', 'N/A')}€
⏰ Abflug: {flight.get('departure_time', 'N/A')} → Ankunft: {flight.get('arrival_time', 'N/A')}
🔄 Stops: {flight.get('stops', 'N/A')}
"""
    
    # Hotels
    hotels = results.get("hotels", [])
    if hotels:
        response += f"\n🏨 **Hotels gefunden:** {len(hotels)}\n"
        
        # Top 3 Hotels
        for i, hotel in enumerate(hotels[:3], 1):
            response += f"""
**Hotel {i}:**
🏨 {hotel.get('name', 'N/A')} ({hotel.get('rating', 'N/A')}⭐)
💰 {hotel.get('price_per_night', 'N/A')}€/Nacht
📍 {hotel.get('location', 'N/A')}
"""
    
    # Combinations
    combinations = results.get("combinations", [])
    if combinations:
        response += f"\n🎯 **Optimierte Pakete:** {len(combinations)}\n"
        
        best_combo = combinations[0]
        response += f"""
**🏆 Beste Kombination:**
💰 Gesamtpreis: {best_combo.get('total_price', 'N/A')}€
⭐ Bewertung: {best_combo.get('score', 'N/A')}/100
💡 Empfehlung: {best_combo.get('recommendation_reason', 'Gutes Preis-Leistungs-Verhältnis')}
"""
    
    if not flights and not hotels:
        response += "❌ Keine Ergebnisse gefunden. Versuchen Sie andere Daten oder Destinationen."
    
    return response


# Tool Definitions für bessere Dokumentation
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Liste aller verfügbaren Tools"""
    
    return [
        Tool(
            name="intelligent_travel_search",
            description="Intelligente Reisesuche mit natürlichsprachlicher Eingabe. Nutzt LLM für Analyse und Optimierung.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natürlichsprachliche Reiseanfrage (z.B. 'Finde mir etwas Romantisches in Italien unter 1000€ im Dezember')"
                    },
                    "origin": {
                        "type": "string", 
                        "description": "Abflugort (optional, Standard: Wien)",
                        "default": "Wien"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="standard_travel_search",
            description="Standard Reisesuche mit strukturierten Parametern",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Abflugort"
                    },
                    "destination": {
                        "type": "string", 
                        "description": "Reiseziel"
                    },
                    "outbound_date": {
                        "type": "string",
                        "description": "Hinflugdatum im Format YYYY-MM-DD"
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Rückflugdatum im Format YYYY-MM-DD"
                    }
                },
                "required": ["origin", "destination", "outbound_date", "return_date"]
            }
        ),
        Tool(
            name="city_autocomplete",
            description="Stadtsuche mit Autocomplete - findet Städte weltweit",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Stadtname oder Teilname für die Suche"
                    }
                },
                "required": ["query"]
            }
        )
    ]


async def main():
    """Startet den MCP Server"""
    
    # Server-Konfiguration
    print("🚀 Holiday Engine MCP Server gestartet...")
    print("📡 Verfügbare Tools:")
    print("  • intelligent_travel_search - Intelligente natürlichsprachliche Suche")
    print("  • standard_travel_search - Standard strukturierte Suche") 
    print("  • city_autocomplete - Stadtsuche")
    print("🔗 Verbindung zur Holiday Engine: http://localhost:8000")
    
    # MCP Server über stdio
    try:
        from mcp.server.stdio import stdio_server
        async with stdio_server() as streams:
            # Neuer Syntax für MCP mit initialization_options
            from mcp.server.models import InitializationOptions
            init_options = InitializationOptions(
                server_name="holiday-engine-intelligent",
                server_version="1.0.0"
            )
            await server.run(*streams, init_options)
    except Exception as e:
        print(f"❌ MCP Server Fehler: {e}")
        print("🔧 Versuche alternativen Start...")
        try:
            # Fallback für ältere MCP Versionen
            await server.run()
        except Exception as e2:
            print(f"❌ Auch Fallback fehlgeschlagen: {e2}")
            print("💡 MCP Version Problem - versuche: pip install --upgrade mcp")


if __name__ == "__main__":
    asyncio.run(main())