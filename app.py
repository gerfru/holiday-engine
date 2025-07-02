# app.py - Gradio GUI die direkt travel_api.py nutzt
import gradio as gr
import asyncio
from travel_api import search_flights_apify, search_hotels_apify

def format_flights(flights_data):
    """Formatiert Flugdaten für Gradio"""
    if isinstance(flights_data, dict) and "error" in flights_data:
        return f"❌ {flights_data['error']}"
    
    if not flights_data:
        return "Keine Flüge gefunden"
    
    formatted = "✈️ **Gefundene Flüge:**\n\n"
    for i, flight in enumerate(flights_data, 1):
        formatted += f"**{i}. {flight.get('airline', 'Unknown')}**\n"
        formatted += f"   • Abflug: {flight.get('time', 'Unknown')}\n"
        formatted += f"   • Dauer: {flight.get('duration', 'Unknown')}\n"
        formatted += f"   • Preis: {flight.get('price', 0)}€\n\n"
    
    return formatted

def format_hotels(hotels_data):
    """Formatiert Hoteldaten für Gradio"""
    if isinstance(hotels_data, dict) and "error" in hotels_data:
        return f"❌ {hotels_data['error']}"
    
    if not hotels_data:
        return "Keine Hotels gefunden"
    
    formatted = "🏨 **Gefundene Hotels:**\n\n"
    for i, hotel in enumerate(hotels_data, 1):
        stars = "⭐" * int(hotel.get('rating', 0))
        formatted += f"**{i}. {hotel.get('name', 'Unknown')}**\n"
        formatted += f"   • Rating: {stars} {hotel.get('rating', 0)}\n"
        formatted += f"   • Preis: {hotel.get('price', 0)}€/Nacht\n"
        formatted += f"   • Lage: {hotel.get('location', 'Unknown')}\n\n"
    
    return formatted

def format_deals(deals_data):
    """Formatiert Deal-Daten für Gradio"""
    if isinstance(deals_data, dict) and "error" in deals_data:
        return f"❌ {deals_data['error']}"
    
    if not deals_data or "deals" not in deals_data:
        return "Keine Deals gefunden"
    
    deals = deals_data["deals"]
    formatted = "🎯 **Beste Deals:**\n\n"
    
    for i, deal in enumerate(deals[:3], 1):  # Top 3
        formatted += f"**Deal {i}: {deal.get('total_price', 0)}€ Gesamt**\n\n"
        formatted += f"✈️ **Flug:** {deal['flight'].get('airline', 'Unknown')}\n"
        formatted += f"   • Abflug: {deal['flight'].get('time', 'Unknown')}\n"
        formatted += f"   • Preis: {deal['flight'].get('price', 0)}€\n\n"
        formatted += f"🏨 **Hotel:** {deal['hotel'].get('name', 'Unknown')}\n"
        formatted += f"   • Rating: {'⭐' * int(deal['hotel'].get('rating', 0))} {deal['hotel'].get('rating', 0)}\n"
        formatted += f"   • Preis: {deal['hotel'].get('price', 0)}€/Nacht\n"
        formatted += f"---\n\n"
    
    return formatted

def gradio_search_flights(origin, destination, date):
    """Gradio Wrapper für Flugsuche"""
    print(f"🔍 Gradio: Suche Flüge {origin} → {destination}")
    
    try:
        flights = asyncio.run(search_flights_apify(origin, destination, date))
        return format_flights(flights)
    except Exception as e:
        return f"❌ Fehler: {str(e)}"

def gradio_search_hotels(city, checkin, checkout):
    """Gradio Wrapper für Hotelsuche"""
    print(f"🏨 Gradio: Suche Hotels in {city}")
    
    try:
        hotels = asyncio.run(search_hotels_apify(city, checkin, checkout))
        return format_hotels(hotels)
    except Exception as e:
        return f"❌ Fehler: {str(e)}"

def gradio_find_deals(origin, destination, departure, return_date):
    """Gradio Wrapper für Deal-Suche"""
    print(f"🎯 Gradio: Suche Deals {origin} → {destination}")
    
    try:
        # Parallel suchen
        flights = asyncio.run(search_flights_apify(origin, destination, departure))
        hotels = asyncio.run(search_hotels_apify(destination, departure, return_date))
        
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
        
        return format_deals({"deals": deals})
    except Exception as e:
        return f"❌ Fehler: {str(e)}"

def create_interface():
    """Erstellt Gradio Interface"""
    
    with gr.Blocks(title="Travel Search", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🛫 Travel Search")
        gr.Markdown("Nutzt die gleichen APIs wie der MCP Server")
        
        with gr.Tab("✈️ Flüge"):
            with gr.Row():
                origin_input = gr.Textbox(label="Von (IATA Code)", placeholder="VIE", value="VIE")
                dest_input = gr.Textbox(label="Nach (IATA Code)", placeholder="BCN", value="BCN")
            
            date_input = gr.Textbox(label="Datum (YYYY-MM-DD)", placeholder="2025-08-15", value="2025-08-15")
            flight_btn = gr.Button("🔍 Flüge suchen", variant="primary")
            flight_output = gr.Markdown()
            
            flight_btn.click(
                fn=gradio_search_flights,
                inputs=[origin_input, dest_input, date_input],
                outputs=flight_output
            )
        
        with gr.Tab("🏨 Hotels"):
            city_input = gr.Textbox(label="Stadt", placeholder="Barcelona", value="Barcelona")
            with gr.Row():
                checkin_input = gr.Textbox(label="Check-in (YYYY-MM-DD)", placeholder="2025-08-15", value="2025-08-15")
                checkout_input = gr.Textbox(label="Check-out (YYYY-MM-DD)", placeholder="2025-08-17", value="2025-08-17")
            
            hotel_btn = gr.Button("🔍 Hotels suchen", variant="primary")
            hotel_output = gr.Markdown()
            
            hotel_btn.click(
                fn=gradio_search_hotels,
                inputs=[city_input, checkin_input, checkout_input],
                outputs=hotel_output
            )
        
        with gr.Tab("🎯 Deals"):
            with gr.Row():
                deal_origin = gr.Textbox(label="Von (IATA)", placeholder="VIE", value="VIE")
                deal_dest = gr.Textbox(label="Nach (IATA)", placeholder="BCN", value="BCN")
            
            with gr.Row():
                deal_departure = gr.Textbox(label="Hinflug (YYYY-MM-DD)", placeholder="2025-08-15", value="2025-08-15")
                deal_return = gr.Textbox(label="Rückflug (YYYY-MM-DD)", placeholder="2025-08-17", value="2025-08-17")
            
            deal_btn = gr.Button("🎯 Beste Deals finden", variant="primary")
            deal_output = gr.Markdown()
            
            deal_btn.click(
                fn=gradio_find_deals,
                inputs=[deal_origin, deal_dest, deal_departure, deal_return],
                outputs=deal_output
            )
        
        with gr.Tab("ℹ️ Info"):
            gr.Markdown("""
            ## Architektur:
            
            **Zwei parallele Interfaces:**
            1. **`server.py`** - MCP Server für Claude Desktop
            2. **`app.py`** - Gradio Web Interface (diese App)
            
            **Beide nutzen `travel_api.py`** für die gleichen APIs!
            
            ### IATA Codes zum Testen:
            - **VIE** - Wien
            - **BCN** - Barcelona  
            - **MUC** - München
            - **LHR** - London
            
            ### Starten:
            ```
            # MCP Server (für Claude Desktop)
            python server.py
            
            # Web Interface (für Browser)
            python app.py
            ```
            """)
    
    return app

if __name__ == "__main__":
    print("🚀 Starte Travel Search Gradio Interface...")
    print("💡 Nutzt travel_api.py direkt (parallel zu MCP Server)")
    
    app = create_interface()
    app.launch(
        server_name="localhost",
        server_port=7860,
        share=False,
        show_error=True
    )