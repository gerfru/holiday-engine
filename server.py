#!/usr/bin/env python3
import asyncio
import json
import os
from mcp.server import Server
from mcp.types import Tool, TextContent
from travel_api import search_flights_apify, search_hotels_apify

# MCP Server nutzt geteilte API Funktionen
server = Server("travel-search")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_flights",
            description="Sucht Flüge zwischen zwei Orten",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Startflughafen (IATA Code)"},
                    "destination": {"type": "string", "description": "Zielflughafen (IATA Code)"},
                    "date": {"type": "string", "description": "Abflugdatum (YYYY-MM-DD)"}
                },
                "required": ["origin", "destination", "date"]
            }
        ),
        Tool(
            name="search_hotels", 
            description="Sucht Hotels in einer Stadt",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Stadt oder Ort"},
                    "checkin": {"type": "string", "description": "Check-in Datum (YYYY-MM-DD)"},
                    "checkout": {"type": "string", "description": "Check-out Datum (YYYY-MM-DD)"}
                },
                "required": ["city", "checkin", "checkout"]
            }
        ),
        Tool(
            name="find_deals",
            description="Findet beste Flug+Hotel Kombinationen",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Startflughafen"},
                    "destination": {"type": "string", "description": "Zielflughafen"},
                    "date": {"type": "string", "description": "Abflugdatum"},
                    "return_date": {"type": "string", "description": "Rückflugdatum"}
                },
                "required": ["origin", "destination", "date", "return_date"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    print(f"🛠️  MCP Tool aufgerufen: {name} mit {arguments}")
    
    try:
        if name == "search_flights":
            result = await search_flights_apify(
                arguments["origin"],
                arguments["destination"], 
                arguments["date"]
            )
        elif name == "search_hotels":
            result = await search_hotels_apify(
                arguments["city"],
                arguments["checkin"],
                arguments["checkout"]
            )
        elif name == "find_deals":
            # Parallel suchen mit echten APIs
            flights = await search_flights_apify(
                arguments["origin"],
                arguments["destination"],
                arguments["date"]
            )
            hotels = await search_hotels_apify(
                arguments["destination"],
                arguments["date"],
                arguments["return_date"]
            )
            
            # Kombiniere zu Deals
            deals = []
            for flight in flights:
                for hotel in hotels:
                    total = flight["price"] + hotel["price"] * 2  # 2 Nächte
                    deals.append({
                        "flight": flight,
                        "hotel": hotel,
                        "total_price": total
                    })
            
            # Sortiere nach Preis
            deals.sort(key=lambda x: x["total_price"])
            result = {"deals": deals}
        else:
            result = {"error": f"Unbekanntes Tool: {name}"}
        
        print(f"✅ MCP Ergebnis: {len(result) if isinstance(result, list) else 'OK'}")
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        print(f"❌ MCP Fehler: {e}")
        return [TextContent(type="text", text=f"Fehler: {str(e)}")]

async def main():
    print("🚀 MCP Travel Server startet...")
    print(f"🔑 Apify Token: {'✅' if os.getenv('APIFY_TOKEN') else '❌ fehlt'}")
    
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())