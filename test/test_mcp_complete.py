# test/test_mcp_complete.py
"""
Teste den kompletten MCP Workflow
"""

import asyncio
import sys
import os

# Pfad zum Hauptverzeichnis hinzufügen
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import holiday_client

async def test_complete_mcp_workflow():
    """Teste den kompletten MCP Workflow"""
    
    print("🚀 Teste kompletten MCP Workflow...")
    
    query = "Romantische Reise nach Italien unter 1000€ im Dezember für 7-10 Tage"
    
    try:
        print(f"🤖 Query: {query}")
        
        result = await holiday_client.call_intelligent_search(query)
        
        print("🎯 MCP Ergebnis:")
        print(f"  Success: {result.get('success')}")
        print(f"  Method: {result.get('method')}")
        print(f"  Error: {result.get('error', 'None')}")
        
        if result.get('success'):
            # Query Analysis
            analysis = result.get('query_analysis', {})
            print(f"\n📝 OpenAI Analyse:")
            print(f"  Destination: {analysis.get('destination')}")
            print(f"  Budget: {analysis.get('budget_max')}€")
            print(f"  Reisetyp: {analysis.get('travel_type')}")
            print(f"  Dauer: {analysis.get('duration_days')} Tage")
            
            # Destination Resolution
            dest_resolved = result.get('destination_resolved', {})
            print(f"\n🗺️ Destination Resolution:")
            print(f"  Stadt: {dest_resolved.get('city')}")
            print(f"  IATA Code: {dest_resolved.get('iata_code')}")
            
            # Search Results
            search_results = result.get('search_results', {})
            flights = search_results.get('flights', {})
            hotels = search_results.get('hotels', [])
            
            print(f"\n🔍 Search Results:")
            print(f"  Hinflüge: {len(flights.get('outbound', []))}")
            print(f"  Rückflüge: {len(flights.get('inbound', []))}")
            print(f"  Hotels: {len(hotels)}")
            
            if hotels:
                print(f"  Top Hotel: {hotels[0].get('name', 'N/A')}")
            
            # AI Recommendations
            recommendations = result.get('ai_recommendations', '')
            if recommendations:
                print(f"\n💡 OpenAI Empfehlungen:")
                print(f"  {recommendations[:100]}...")
            
            print(f"\n✅ VOLLSTÄNDIGER ERFOLG!")
            print(f"✅ OpenAI + Apify Scraper + Intelligente Empfehlungen funktionieren!")
            
        else:
            print(f"\n❌ Workflow fehlgeschlagen: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Test Fehler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_mcp_workflow())