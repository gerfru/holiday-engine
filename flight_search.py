#!/usr/bin/env python3
"""
Simple Flight Search Tool
Usage: python flight_search.py [config_file]
"""

import json
import csv
import requests
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

def load_config(config_file='flights.json'):
    """Lädt Flugsuchen aus JSON oder CSV"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        # Erstelle Beispiel-Config
        if config_file.endswith('.json'):
            example = {
                "searches": [
                    {
                        "name": "Barcelona Trip",
                        "from": "VIE",
                        "to": "BCN", 
                        "departure": "2025-08-15",
                        "return": "2025-08-22"
                    },
                    {
                        "name": "London One-Way",
                        "from": "VIE",
                        "to": "LHR",
                        "departure": "2025-09-01"
                    }
                ]
            }
            with open(config_file, 'w') as f:
                json.dump(example, f, indent=2)
        else:
            # CSV Beispiel
            with open(config_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['name', 'from', 'to', 'departure', 'return'])
                writer.writerow(['Barcelona Trip', 'VIE', 'BCN', '2025-08-15', '2025-08-22'])
                writer.writerow(['London One-Way', 'VIE', 'LHR', '2025-09-01', ''])
        
        print(f"📝 Beispiel-Config erstellt: {config_file}")
        print("Bearbeite die Datei und starte erneut.")
        return []
    
    # Lade Config
    if config_file.endswith('.json'):
        with open(config_file) as f:
            data = json.load(f)
            return data.get('searches', [])
    else:
        # CSV laden
        searches = []
        with open(config_file, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                search = {
                    'name': row['name'],
                    'from': row['from'],
                    'to': row['to'],
                    'departure': row['departure'],
                    'return': row.get('return', '').strip() or None
                }
                searches.append(search)
        return searches

def search_flights(search_config):
    """Sucht Flüge für eine Konfiguration"""
    token = os.getenv('APIFY_TOKEN')
    if not token:
        print("❌ APIFY_TOKEN nicht in .env gefunden!")
        return None
    
    # Normaler Run (nicht sync), dann Ergebnisse abrufen
    run_url = 'https://api.apify.com/v2/acts/jupri~skyscanner-flight/runs'
    
    # Input-Struktur
    if search_config.get('return'):
        payload = {
            "origin.0": search_config['from'],
            "target.0": search_config['to'],
            "depart.0": search_config['departure'],
            "origin.1": search_config['to'],
            "target.1": search_config['from'],
            "depart.1": search_config['return']
        }
    else:
        payload = {
            "origin.0": search_config['from'],
            "target.0": search_config['to'],
            "depart.0": search_config['departure']
        }
    
    try:
        print(f"🔍 {search_config['name']} ({search_config['from']} → {search_config['to']})...")
        
        # Starte Run - ohne 'input' wrapper
        response = requests.post(
            run_url,
            json=payload,  # Direkt das payload, nicht {'input': payload}
            headers={'Authorization': f'Bearer {token}'},
            timeout=30
        )
        
        if response.status_code != 201:
            print(f"   ❌ Start-Fehler {response.status_code}")
            return None
        
        run_id = response.json()['data']['id']
        print(f"   ⏳ Warte auf Ergebnisse... (Run: {run_id})")
        
        # Warte auf Abschluss - korrekte URL für Actor Runs
        status_url = f'https://api.apify.com/v2/acts/jupri~skyscanner-flight/runs/{run_id}'
        for i in range(60):  # Max 5 Minuten warten
            time.sleep(5)
            
            try:
                status_resp = requests.get(status_url, headers={'Authorization': f'Bearer {token}'})
                
                if status_resp.status_code != 200:
                    print(f"   ❌ Status-Fehler {status_resp.status_code}")
                    return None
                
                status_data = status_resp.json()
                
                if 'data' not in status_data:
                    print(f"   🔧 Status Response: {status_data}")
                    continue
                
                status = status_data['data']['status']
                
                if status == 'SUCCEEDED':
                    print("   🎉 Actor fertig, hole Daten...")
                    
                    # Korrekte Dataset URL - über die Run, nicht direkt
                    dataset_id = status_data['data'].get('defaultDatasetId')
                    if dataset_id:
                        results_url = f'https://api.apify.com/v2/datasets/{dataset_id}/items'
                    else:
                        # Fallback: über Run-ID
                        results_url = f'https://api.apify.com/v2/acts/jupri~skyscanner-flight/runs/{run_id}/dataset/items'
                    
                    print(f"   🔧 Dataset URL: {results_url}")
                    results_resp = requests.get(results_url, headers={'Authorization': f'Bearer {token}'})
                    
                    print(f"   🔧 Dataset Status: {results_resp.status_code}")
                    
                    if results_resp.status_code == 200:
                        flights = results_resp.json()
                        print(f"   🔧 Raw data length: {len(flights) if flights else 0}")
                        
                        if flights:
                            print(f"   🔧 Erste Zeile: {str(flights[0])[:100] if flights else 'Leer'}...")
                            print(f"   ✅ {len(flights)} Flüge gefunden")
                            return flights
                        else:
                            print("   ❌ Keine Daten im Dataset")
                            return []
                    else:
                        print(f"   ❌ Dataset-Fehler: {results_resp.text[:200]}")
                        return None
                        
                elif status == 'FAILED':
                    print("   ❌ Actor fehlgeschlagen")
                    return None
                elif status in ['RUNNING', 'READY']:
                    if i % 6 == 0:  # Alle 30 Sekunden
                        print("   ⏳ Läuft noch...")
                else:
                    print(f"   🔧 Status: {status}")
                    
            except Exception as e:
                print(f"   ❌ Status-Check Fehler: {e}")
                continue
        
        print("   ❌ Timeout")
        return None
                
    except Exception as e:
        print(f"   ❌ {e}")
        return None

def save_results(all_results, format_type='csv'):
    """Speichert alle Ergebnisse"""
    # Erstelle output Ordner falls er nicht existiert
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = output_dir / f"flight_results_{timestamp}.{format_type}"
    
    if format_type == 'csv':
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if not all_results:
                f.write('Keine Ergebnisse\n')
                return filename
            
            writer = csv.writer(f)
            writer.writerow([
                'search_name', 'price', 'currency', 'agent', 'score', 
                'departure_time', 'arrival_time', 'duration', 'stops', 'last_updated'
            ])
            
            for search_name, flights in all_results.items():
                for flight in flights:
                    # Korrekte Skyscanner-Hierarchie: cheapest_price statt pricing_options[0]
                    cheapest_price = flight.get('cheapest_price', {})
                    price = cheapest_price.get('amount', 'N/A')
                    
                    # Leg-Info für Zeiten
                    legs = flight.get('legs', [])
                    departure_time = legs[0].get('departure', 'N/A') if legs else 'N/A'
                    arrival_time = legs[-1].get('arrival', 'N/A') if legs else 'N/A'
                    
                    # Stops berechnen
                    total_stops = sum(leg.get('stop_count', 0) for leg in legs)
                    
                    # Günstigsten Agent finden
                    pricing_options = flight.get('pricing_options', [])
                    agent = pricing_options[0].get('agent_ids', ['Unknown'])[0] if pricing_options else 'Unknown'
                    
                    writer.writerow([
                        search_name,
                        price,
                        'USD',  # Skyscanner Standard
                        agent,
                        flight.get('score', 'N/A'),
                        departure_time,
                        arrival_time,
                        'N/A',  # Duration - müsste aus legs berechnet werden
                        total_stops,
                        cheapest_price.get('last_updated', 'N/A')
                    ])
    else:
        # JSON - speichere Rohdaten
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    return filename

def print_summary(all_results):
    """Zeigt eine kurze Zusammenfassung"""
    print("\n" + "="*60)
    print("📊 ZUSAMMENFASSUNG")
    print("="*60)
    
    for search_name, flights in all_results.items():
        if not flights:
            print(f"\n❌ {search_name}: Keine Flüge gefunden")
            continue
        
        print(f"\n✈️  {search_name}")
        print("-" * 40)
        
        # Top 5 günstigste mit korrekter Datenstruktur
        for i, flight in enumerate(flights[:5], 1):
            # Günstigster Preis aus cheapest_price
            cheapest_price = flight.get('cheapest_price', {})
            price = cheapest_price.get('amount', 'N/A')
            
            # Günstigster Agent
            pricing_options = flight.get('pricing_options', [])
            agent = pricing_options[0].get('agent_ids', ['Unknown'])[0] if pricing_options else 'Unknown'
            
            # Agent-Name aus _agents lookup
            agents_info = flight.get('_agents', {})
            agent_name = agents_info.get(agent, {}).get('name', agent)
            
            score = flight.get('score', 0)
            
            # Zeiten aus legs
            legs = flight.get('legs', [])
            departure = legs[0].get('departure', 'N/A')[:16] if legs else 'N/A'
            arrival = legs[-1].get('arrival', 'N/A')[:16] if legs else 'N/A'
            
            print(f"   {i}. ${price} | {agent_name} | Score: {score:.1f}")
            print(f"      {departure} → {arrival}")
            print()

def main():
    import sys
    
    print("🛫 Simple Flight Search Tool")
    print("-" * 40)
    
    # Config-Datei bestimmen
    config_file = 'flights.json'
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    # Lade Konfiguration
    searches = load_config(config_file)
    if not searches:
        return
    
    print(f"📖 Geladen: {len(searches)} Flugsuchen aus {config_file}")
    
    # Suche alle Flüge
    all_results = {}
    
    for search in searches:
        flights = search_flights(search)
        if flights:
            # Füge Metadaten hinzu
            for flight in flights:
                flight['from_code'] = search['from']
                flight['to_code'] = search['to']
            
            all_results[search['name']] = flights
        else:
            all_results[search['name']] = []
        
        # Kurze Pause zwischen Requests
        time.sleep(2)
    
    # Speichere Ergebnisse
    csv_file = save_results(all_results, 'csv')
    json_file = save_results(all_results, 'json')
    
    # Zeige Zusammenfassung
    print_summary(all_results)
    
    print(f"\n💾 Ergebnisse gespeichert:")
    print(f"   📄 {csv_file}")
    print(f"   📄 {json_file}")

if __name__ == '__main__':
    main()

"""
Installation:
pip install requests python-dotenv

.env Datei:
APIFY_TOKEN=dein_token_hier

Verwendung:
python flight_search.py                    # Nutzt flights.json
python flight_search.py my_trips.csv       # Nutzt CSV
python flight_search.py summer_trips.json  # Nutzt JSON

flights.json Beispiel:
{
  "searches": [
    {
      "name": "Barcelona Trip",
      "from": "VIE",
      "to": "BCN",
      "departure": "2025-08-15",
      "return": "2025-08-22"
    }
  ]
}

flights.csv Beispiel:
name,from,to,departure,return
Barcelona Trip,VIE,BCN,2025-08-15,2025-08-22
London One-Way,VIE,LHR,2025-09-01,
"""