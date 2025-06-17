import requests
import json
from dotenv import load_dotenv
import os
import pandas as pd

# .env einlesen
load_dotenv()

# API-Keys aus Umgebungsvariablen holen
RAPIDAPI_KEY = os.getenv('X_RAPIDAPI_KEY')
RAPIDAPI_HOST = os.getenv('X_RAPIDAPI_HOST')

url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip"

querystring = {"source":"Country:AT, City:Graz_AT, City:Vienna_AT",
               "destination":"City:rhodes_gr",
               "currency":"eur",
               "locale":"en",
               "adults":"1",
               "children":"0",
               "infants":"0",
               "handbags":"1",
               "holdbags":"0",
               "cabinClass":"ECONOMY",
               "sortBy":"QUALITY",
               "sortOrder":"ASCENDING",
               "applyMixedClasses":"true",
               "allowReturnFromDifferentCity":"true",
               "allowChangeInboundDestination":"true",
               "allowChangeInboundSource":"true",
               "allowDifferentStationConnection":"true",
               "enableSelfTransfer":"true",
               "allowOvernightStopover":"false",
               "enableTrueHiddenCity":"true",
               "enableThrowAwayTicketing":"true",
               "outbound":"SUNDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY,MONDAY,TUESDAY",
               "transportTypes":"FLIGHT",
               #"contentProviders":"FLIXBUS_DIRECTS,FRESH,KAYAK,KIWI",
               "inboundDepartureDateStart":"2025-06-23T00:00:00",
               "inboundDepartureDateEnd":"2025-06-30T23:59:59",
               #"maxStopsCount":"0",
               "limit":"20"}

headers = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}
response = requests.get(url, headers=headers, params=querystring)
data = response.json()

#with open('output/api_response.json', 'w', encoding='utf-8') as f:
#    json.dump(data, f, ensure_ascii=False, indent=2)
#print("Response als api_response.json gespeichert.")

def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Liste von Dicts flach machen
            if v and isinstance(v[0], dict):
                for i, item in enumerate(v):
                    items.extend(flatten_dict(item, f"{new_key}.{i}", sep=sep).items())
            else:
                items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)

rows = [flatten_dict(x) for x in data.get('itineraries', [])]

# DataFrame bauen und als Excel speichern
df = pd.DataFrame(rows)
df.to_excel('output/flights_dynamic.xlsx', index=False)

print("Excel mit dynamisch generierten Spalten wurde erstellt: output/flights_rhodes_dynamic.xlsx")
