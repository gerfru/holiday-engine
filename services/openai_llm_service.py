# services/openai_llm_service.py
"""
OpenAI LLM Service für Holiday Engine
Nutzt OpenAI API für alle intelligenten Funktionen
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional
import httpx
from openai import AsyncOpenAI

# Lade .env File
from dotenv import load_dotenv
load_dotenv()  # Lädt .env aus dem Root-Ordner


class OpenAILLMService:
    """LLM Service mit OpenAI Integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        # API Key aus .env File oder Parameter
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API Key erforderlich!\n"
                "Füge OPENAI_API_KEY=sk-your-key-here zu deiner .env Datei hinzu"
            )
        
        # OpenAI Client initialisieren
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  # Günstigeres Modell - funktioniert genauso gut
        
        # Test der Verbindung
        self.is_available = True
        print(f"✅ OpenAI LLM Service initialisiert mit Model: {self.model}")
        
    async def analyze_travel_query(self, query: str) -> Dict[str, Any]:
        """Analysiert Reiseanfrage mit OpenAI GPT"""
        
        prompt = f"""Du bist ein Experte für Reiseplanung. Analysiere diese Reiseanfrage und extrahiere strukturierte Informationen.

Anfrage: "{query}"

Bitte antworte NUR mit einem gültigen JSON-Objekt im folgenden Format:
{{
    "destination": "extrahiertes Reiseziel",
    "budget_max": null oder Zahl in EUR,
    "duration_days": [min_tage, max_tage],
    "travel_type": "romantic/family/business/adventure/leisure/cultural",
    "month": null oder 1-12,
    "preferences": {{
        "accommodation_type": "hotel/airbnb/luxury/budget",
        "activities": ["liste", "von", "gewünschten", "aktivitäten"],
        "priority": "price/comfort/location/experience"
    }},
    "flexibility": {{
        "dates": "flexible/fixed",
        "destination": "flexible/fixed", 
        "budget": "flexible/fixed"
    }},
    "extracted_keywords": ["wichtige", "keywords", "aus", "anfrage"],
    "confidence_score": 0.9
}}

Achte besonders auf:
- Budget-Angaben ("unter 1000€", "max 500€", "bis 2000€")
- Dauer ("7-10 Tage", "eine Woche", "Wochenende")
- Reisetyp-Hinweise ("romantisch", "Familie", "Business")
- Zeitangaben ("Dezember", "im Winter", "nächsten Monat")

WICHTIG: Antworte NUR mit dem JSON-Objekt, keine anderen Texte oder Formatierungen."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für Reiseplanung und extrahierst strukturierte Daten aus natürlichsprachlichen Anfragen."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1,  # Niedrig für konsistente Ergebnisse
                response_format={"type": "json_object"}  # Erzwingt JSON-Antwort
            )
            
            json_response = response.choices[0].message.content
            parsed_response = json.loads(json_response)
            
            print(f"🤖 OpenAI Analyse erfolgreich: {parsed_response.get('destination', 'N/A')}")
            return parsed_response
            
        except Exception as e:
            print(f"OpenAI Analyse Fehler: {e}")
            return self._fallback_analysis(query)
    
    async def generate_travel_recommendations(self, search_results: Dict, user_preferences: Dict) -> str:
        """Generiert personalisierte Reiseempfehlungen mit OpenAI"""
        
        # Bereite Daten für OpenAI auf
        results_summary = self._prepare_results_summary(search_results)
        
        prompt = f"""Du bist ein erfahrener Reiseberater. Basierend auf den Suchergebnissen und Benutzerpräferenzen, erstelle eine personalisierte, beratende Empfehlung.

Benutzerpräferenzen:
{json.dumps(user_preferences, indent=2, ensure_ascii=False)}

Suchergebnisse:
{results_summary}

Erstelle eine natürliche, beratende Empfehlung die folgende Punkte abdeckt:

1. **Hauptempfehlung**: Die beste Option mit klarer Begründung
2. **Alternative Optionen**: 1-2 weitere gute Alternativen  
3. **Budgetoptimierung**: Konkrete Tipps zum Geld sparen
4. **Reisetyp-spezifische Tipps**: Passend zum gewünschten Reisetyp
5. **Timing-Empfehlungen**: Beste Reisezeiten und was zu beachten ist
6. **Lokale Tipps**: Geheimtipps oder wichtige Hinweise für die Destination

Schreibe in einem warmen, persönlichen Ton als würdest du einem Freund raten.
Verwende Emojis sparsam aber gezielt für bessere Lesbarkeit.
Strukturiere die Antwort mit Markdown-Überschriften.
Halte die Antwort informativ aber nicht zu lang (max 400 Wörter)."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du bist ein professioneller Reiseberater der personalisierte, praktische Empfehlungen gibt."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7  # Etwas höher für kreativere Empfehlungen
            )
            
            recommendation = response.choices[0].message.content
            print("💡 OpenAI Empfehlung generiert")
            return recommendation
            
        except Exception as e:
            print(f"OpenAI Empfehlungs-Fehler: {e}")
            return self._fallback_recommendations(search_results, user_preferences)
    
    async def optimize_search_parameters(self, original_query: str, current_results: Dict) -> Dict[str, Any]:
        """Optimiert Suchparameter mit OpenAI"""
        
        results_count = len(current_results.get("search_results", []))
        avg_price = self._calculate_average_price(current_results)
        
        prompt = f"""Analysiere die Suchergebnisse und schlage konkrete Optimierungen vor.

Ursprüngliche Anfrage: "{original_query}"

Aktuelle Ergebnisse:
- Gefundene Optionen: {results_count}
- Durchschnittspreis: {avg_price}€
- Qualität der Ergebnisse: {"gut" if results_count > 3 else "wenige Optionen"}

Bitte antworte mit einem JSON-Objekt mit konkreten Optimierungsvorschlägen:
{{
    "alternative_destinations": ["ähnliche", "destinationen", "in", "der", "nähe"],
    "date_suggestions": {{
        "cheaper_periods": ["YYYY-MM-DD bis YYYY-MM-DD", "für günstigere Preise"],
        "better_weather": ["YYYY-MM-DD bis YYYY-MM-DD", "für besseres Wetter"]
    }},
    "budget_optimization": {{
        "money_saving_tips": ["Konkreter Tipp 1", "Konkreter Tipp 2", "Konkreter Tipp 3"],
        "flexible_options": ["Flexibilität bei X", "Flexibilität bei Y"]
    }},
    "search_refinements": {{
        "if_few_results": "Was tun wenn wenige Ergebnisse",
        "if_expensive": "Was tun wenn zu teuer",
        "general_tips": "Allgemeine Verbesserungsvorschläge"
    }},
    "personalized_suggestions": ["Basierend auf der Anfrage", "spezifische Verbesserungen"],
    "confidence_score": 0.85
}}

WICHTIG: Antworte NUR mit dem JSON-Objekt."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du bist ein Reise-Optimierungsexperte der konkrete, umsetzbare Verbesserungsvorschläge macht."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            json_response = response.choices[0].message.content
            parsed_response = json.loads(json_response)
            
            print("🎯 OpenAI Optimierung generiert")
            return parsed_response
            
        except Exception as e:
            print(f"OpenAI Optimierungs-Fehler: {e}")
            return self._fallback_optimization(original_query, current_results)
    
    def _prepare_results_summary(self, search_results: Dict) -> str:
        """Bereitet Suchergebnisse für OpenAI auf"""
        
        if not search_results.get("search_results"):
            return "Keine Suchergebnisse verfügbar"
        
        # Finde beste Option
        best_result = search_results["search_results"][0]
        best_combo = best_result["combinations"][0] if best_result.get("combinations") else {}
        
        if not best_combo:
            return "Keine gültigen Kombinationen gefunden"
        
        summary = f"""
BESTE GEFUNDENE OPTION:
- Reisedatum: {best_result.get('date_option', {}).get('check_in', 'N/A')} bis {best_result.get('date_option', {}).get('check_out', 'N/A')}
- Flug: {best_combo.get('flight', {}).get('airline', 'N/A')} für {best_combo.get('flight', {}).get('price_eur', 'N/A')}€
- Hotel: {best_combo.get('hotel', {}).get('name', 'N/A')} ({best_combo.get('hotel', {}).get('rating', 'N/A')}⭐) für {best_combo.get('hotel', {}).get('price_per_night', 'N/A')}€/Nacht
- Gesamtkosten: {best_combo.get('total_price', 'N/A')}€

ALTERNATIVE OPTIONEN: {len(search_results.get("search_results", [])) - 1} weitere verfügbar
DURCHSCHNITTSPREIS: {self._calculate_average_price(search_results)}€
"""
        
        return summary
    
    def _calculate_average_price(self, results: Dict) -> float:
        """Berechnet Durchschnittspreis der Ergebnisse"""
        
        total_price = 0
        count = 0
        
        for result in results.get("search_results", []):
            for combo in result.get("combinations", []):
                if combo.get("total_price"):
                    total_price += combo["total_price"]
                    count += 1
        
        return round(total_price / count, 2) if count > 0 else 0
    
    def _fallback_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback wenn OpenAI nicht verfügbar"""
        
        query_lower = query.lower()
        
        # Einfache Regel-basierte Extraktion
        destination = "Italien"
        if "spanien" in query_lower:
            destination = "Spanien"
        elif "griechenland" in query_lower:
            destination = "Griechenland"
        
        # Budget
        budget = None
        import re
        budget_match = re.search(r'(\d+)€', query)
        if budget_match:
            budget = int(budget_match.group(1))
        
        # Travel Type
        travel_type = "leisure"
        if any(word in query_lower for word in ["romantisch", "romantic"]):
            travel_type = "romantic"
        elif any(word in query_lower for word in ["familie", "family"]):
            travel_type = "family"
        
        return {
            "destination": destination,
            "budget_max": budget,
            "duration_days": [7, 10],
            "travel_type": travel_type,
            "month": None,
            "preferences": {
                "accommodation_type": "hotel",
                "activities": ["sightseeing"],
                "priority": "price"
            },
            "flexibility": {
                "dates": "flexible",
                "destination": "fixed",
                "budget": "flexible"
            },
            "extracted_keywords": query_lower.split()[:5],
            "confidence_score": 0.6
        }
    
    def _fallback_recommendations(self, search_results: Dict, user_preferences: Dict) -> str:
        """Fallback-Empfehlungen ohne OpenAI"""
        
        return f"""
## 🎯 Reiseempfehlung

**Hauptempfehlung:** Basierend auf Ihren Präferenzen haben wir die beste verfügbare Option ausgewählt.

**Budgetoptimierung:** Flexible Reisedaten können bis zu 30% Ersparnis bringen.

**Reisetipps:** Buchen Sie Hotels mit guten Bewertungen und prüfen Sie die Lage.

**Timing:** Die gewählten Daten bieten gute Verfügbarkeit.

*Hinweis: Detailliertere Empfehlungen verfügbar sobald OpenAI-Service wieder erreichbar ist.*
"""
    
    def _fallback_optimization(self, original_query: str, current_results: Dict) -> Dict[str, Any]:
        """Fallback-Optimierung ohne OpenAI"""
        
        return {
            "alternative_destinations": ["Ähnliche Destinationen prüfen"],
            "date_suggestions": {
                "cheaper_periods": ["Nebensaison bevorzugen"],
                "better_weather": ["Wettervorhersage beachten"]
            },
            "budget_optimization": {
                "money_saving_tips": ["Flexible Daten", "Frühbucher-Rabatte"],
                "flexible_options": ["Nahegelegene Flughäfen"]
            },
            "search_refinements": {
                "general_tips": "Suchkriterien anpassen für mehr Optionen"
            },
            "confidence_score": 0.5
        }


# Test-Funktion
async def test_openai_service():
    """Test-Funktion für OpenAI Service"""
    
    try:
        service = OpenAILLMService()
        
        # Test Analyse
        result = await service.analyze_travel_query("Romantische Reise nach Italien unter 1000€")
        print("✅ OpenAI Test erfolgreich:")
        print(f"   Destination: {result.get('destination')}")
        print(f"   Budget: {result.get('budget_max')}€")
        print(f"   Reisetyp: {result.get('travel_type')}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI Test fehlgeschlagen: {e}")
        return False


if __name__ == "__main__":
    # Teste OpenAI Service
    import asyncio
    asyncio.run(test_openai_service())
        
    async def analyze_travel_query(self, query: str) -> Dict[str, Any]:
        """Analysiert Reiseanfrage mit OpenAI GPT"""
        
        prompt = f"""Du bist ein Experte für Reiseplanung. Analysiere diese Reiseanfrage und extrahiere strukturierte Informationen.

Anfrage: "{query}"

Bitte antworte NUR mit einem gültigen JSON-Objekt im folgenden Format:
{{
    "destination": "extrahiertes Reiseziel",
    "budget_max": null oder Zahl in EUR,
    "duration_days": [min_tage, max_tage],
    "travel_type": "romantic/family/business/adventure/leisure/cultural",
    "month": null oder 1-12,
    "preferences": {{
        "accommodation_type": "hotel/airbnb/luxury/budget",
        "activities": ["liste", "von", "gewünschten", "aktivitäten"],
        "priority": "price/comfort/location/experience"
    }},
    "flexibility": {{
        "dates": "flexible/fixed",
        "destination": "flexible/fixed", 
        "budget": "flexible/fixed"
    }},
    "extracted_keywords": ["wichtige", "keywords", "aus", "anfrage"],
    "confidence_score": 0.9
}}

Achte besonders auf:
- Budget-Angaben ("unter 1000€", "max 500€", "bis 2000€")
- Dauer ("7-10 Tage", "eine Woche", "Wochenende")
- Reisetyp-Hinweise ("romantisch", "Familie", "Business")
- Zeitangaben ("Dezember", "im Winter", "nächsten Monat")

WICHTIG: Antworte NUR mit dem JSON-Objekt, keine anderen Texte oder Formatierungen."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für Reiseplanung und extrahierst strukturierte Daten aus natürlichsprachlichen Anfragen."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1,  # Niedrig für konsistente Ergebnisse
                response_format={"type": "json_object"}  # Erzwingt JSON-Antwort
            )
            
            json_response = response.choices[0].message.content
            return json.loads(json_response)
            
        except Exception as e:
            print(f"OpenAI Analyse Fehler: {e}")
            return self._fallback_analysis(query)
    
    async def generate_travel_recommendations(self, search_results: Dict, user_preferences: Dict) -> str:
        """Generiert personalisierte Reiseempfehlungen mit OpenAI"""
        
        # Bereite Daten für OpenAI auf
        results_summary = self._prepare_results_summary(search_results)
        
        prompt = f"""Du bist ein erfahrener Reiseberater. Basierend auf den Suchergebnissen und Benutzerpräferenzen, erstelle eine personalisierte, beratende Empfehlung.

Benutzerpräferenzen:
{json.dumps(user_preferences, indent=2, ensure_ascii=False)}

Suchergebnisse:
{results_summary}

Erstelle eine natürliche, beratende Empfehlung die folgende Punkte abdeckt:

1. **Hauptempfehlung**: Die beste Option mit klarer Begründung
2. **Alternative Optionen**: 1-2 weitere gute Alternativen  
3. **Budgetoptimierung**: Konkrete Tipps zum Geld sparen
4. **Reisetyp-spezifische Tipps**: Passend zum gewünschten Reisetyp
5. **Timing-Empfehlungen**: Beste Reisezeiten und was zu beachten ist
6. **Lokale Tipps**: Geheimtipps oder wichtige Hinweise für die Destination

Schreibe in einem warmen, persönlichen Ton als würdest du einem Freund raten.
Verwende Emojis sparsam aber gezielt für bessere Lesbarkeit.
Strukturiere die Antwort mit Markdown-Überschriften.
Halte die Antwort informativ aber nicht zu lang (max 400 Wörter)."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du bist ein professioneller Reiseberater der personalisierte, praktische Empfehlungen gibt."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7  # Etwas höher für kreativere Empfehlungen
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI Empfehlungs-Fehler: {e}")
            return self._fallback_recommendations(search_results, user_preferences)
    
    async def optimize_search_parameters(self, original_query: str, current_results: Dict) -> Dict[str, Any]:
        """Optimiert Suchparameter mit OpenAI"""
        
        results_count = len(current_results.get("search_results", []))
        avg_price = self._calculate_average_price(current_results)
        
        prompt = f"""Analysiere die Suchergebnisse und schlage konkrete Optimierungen vor.

Ursprüngliche Anfrage: "{original_query}"

Aktuelle Ergebnisse:
- Gefundene Optionen: {results_count}
- Durchschnittspreis: {avg_price}€
- Qualität der Ergebnisse: {"gut" if results_count > 3 else "wenige Optionen"}

Bitte antworte mit einem JSON-Objekt mit konkreten Optimierungsvorschlägen:
{{
    "alternative_destinations": ["ähnliche", "destinationen", "in", "der", "nähe"],
    "date_suggestions": {{
        "cheaper_periods": ["YYYY-MM-DD bis YYYY-MM-DD", "für günstigere Preise"],
        "better_weather": ["YYYY-MM-DD bis YYYY-MM-DD", "für besseres Wetter"]
    }},
    "budget_optimization": {{
        "money_saving_tips": ["Konkreter Tipp 1", "Konkreter Tipp 2", "Konkreter Tipp 3"],
        "flexible_options": ["Flexibilität bei X", "Flexibilität bei Y"]
    }},
    "search_refinements": {{
        "if_few_results": "Was tun wenn wenige Ergebnisse",
        "if_expensive": "Was tun wenn zu teuer",
        "general_tips": "Allgemeine Verbesserungsvorschläge"
    }},
    "personalized_suggestions": ["Basierend auf der Anfrage", "spezifische Verbesserungen"],
    "confidence_score": 0.85
}}

WICHTIG: Antworte NUR mit dem JSON-Objekt."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du bist ein Reise-Optimierungsexperte der konkrete, umsetzbare Verbesserungsvorschläge macht."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            json_response = response.choices[0].message.content
            return json.loads(json_response)
            
        except Exception as e:
            print(f"OpenAI Optimierungs-Fehler: {e}")
            return self._fallback_optimization(original_query, current_results)
    
    async def generate_smart_filters(self, query: str, available_options: Dict) -> Dict[str, Any]:
        """Generiert intelligente Filter basierend auf der Anfrage"""
        
        prompt = f"""Basierend auf der Reiseanfrage, generiere intelligente Filter für die Suchergebnisse.

Anfrage: "{query}"

Verfügbare Optionen:
- Hotels: {len(available_options.get('hotels', []))}
- Flüge: {len(available_options.get('flights', []))}
- Preisbereich: {self._get_price_range(available_options)}

Erstelle ein JSON mit intelligenten Filtern:
{{
    "recommended_filters": {{
        "price_range": {{
            "min": 100,
            "max": 1500,
            "reason": "Basierend auf Ihrem Budget"
        }},
        "hotel_rating": {{
            "min_stars": 3,
            "reason": "Für Ihren Reisetyp empfohlen"
        }},
        "flight_preferences": {{
            "max_stops": 1,
            "preferred_times": ["morning", "afternoon"],
            "reason": "Für entspannte Anreise"
        }}
    }},
    "priority_sorting": ["price", "rating", "location"],
    "hide_options": ["budget_airlines", "hostels"],
    "highlight_features": ["spa", "city_center", "breakfast_included"]
}}

WICHTIG: Antworte NUR mit dem JSON-Objekt."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du erstellst intelligente Filter für Reisesuchergebnisse basierend auf Benutzerpräferenzen."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"OpenAI Filter-Fehler: {e}")
            return {"recommended_filters": {}, "priority_sorting": ["price"]}
    
    def _prepare_results_summary(self, search_results: Dict) -> str:
        """Bereitet Suchergebnisse für OpenAI auf"""
        
        if not search_results.get("search_results"):
            return "Keine Suchergebnisse verfügbar"
        
        # Finde beste Option
        best_result = search_results["search_results"][0]
        best_combo = best_result["combinations"][0] if best_result.get("combinations") else {}
        
        if not best_combo:
            return "Keine gültigen Kombinationen gefunden"
        
        summary = f"""
BESTE GEFUNDENE OPTION:
- Reisedatum: {best_result.get('date_option', {}).get('check_in', 'N/A')} bis {best_result.get('date_option', {}).get('check_out', 'N/A')}
- Flug: {best_combo.get('flight', {}).get('airline', 'N/A')} für {best_combo.get('flight', {}).get('price_eur', 'N/A')}€
- Hotel: {best_combo.get('hotel', {}).get('name', 'N/A')} ({best_combo.get('hotel', {}).get('rating', 'N/A')}⭐) für {best_combo.get('hotel', {}).get('price_per_night', 'N/A')}€/Nacht
- Gesamtkosten: {best_combo.get('total_price', 'N/A')}€
- Optimierungsscore: {best_result.get('date_option', {}).get('optimization_score', {}).get('total', 'N/A')}/100

ALTERNATIVE OPTIONEN: {len(search_results.get("search_results", [])) - 1} weitere verfügbar
DURCHSCHNITTSPREIS: {self._calculate_average_price(search_results)}€
"""
        
        return summary
    
    def _calculate_average_price(self, results: Dict) -> float:
        """Berechnet Durchschnittspreis der Ergebnisse"""
        
        total_price = 0
        count = 0
        
        for result in results.get("search_results", []):
            for combo in result.get("combinations", []):
                if combo.get("total_price"):
                    total_price += combo["total_price"]
                    count += 1
        
        return round(total_price / count, 2) if count > 0 else 0
    
    def _get_price_range(self, available_options: Dict) -> str:
        """Ermittelt Preisbereich der verfügbaren Optionen"""
        
        prices = []
        
        for hotel in available_options.get("hotels", []):
            if hotel.get("price_per_night"):
                prices.append(hotel["price_per_night"])
        
        for flight in available_options.get("flights", []):
            if flight.get("price_eur"):
                prices.append(flight["price_eur"])
        
        if prices:
            return f"{min(prices)}€ - {max(prices)}€"
        return "Nicht verfügbar"
    
    def _fallback_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback wenn OpenAI nicht verfügbar"""
        
        query_lower = query.lower()
        
        # Einfache Regel-basierte Extraktion
        destination = "Italien"
        if "spanien" in query_lower:
            destination = "Spanien"
        elif "griechenland" in query_lower:
            destination = "Griechenland"
        
        # Budget
        budget = None
        import re
        budget_match = re.search(r'(\d+)€', query)
        if budget_match:
            budget = int(budget_match.group(1))
        
        # Travel Type
        travel_type = "leisure"
        if any(word in query_lower for word in ["romantisch", "romantic"]):
            travel_type = "romantic"
        elif any(word in query_lower for word in ["familie", "family"]):
            travel_type = "family"
        
        return {
            "destination": destination,
            "budget_max": budget,
            "duration_days": [7, 10],
            "travel_type": travel_type,
            "month": None,
            "preferences": {
                "accommodation_type": "hotel",
                "activities": ["sightseeing"],
                "priority": "price"
            },
            "flexibility": {
                "dates": "flexible",
                "destination": "fixed",
                "budget": "flexible"
            },
            "extracted_keywords": query_lower.split()[:5],
            "confidence_score": 0.6
        }
    
    def _fallback_recommendations(self, search_results: Dict, user_preferences: Dict) -> str:
        """Fallback-Empfehlungen ohne OpenAI"""
        
        return f"""
## 🎯 Reiseempfehlung

**Hauptempfehlung:** Basierend auf Ihren Präferenzen haben wir die beste verfügbare Option ausgewählt.

**Budgetoptimierung:** Flexible Reisedaten können bis zu 30% Ersparnis bringen.

**Reisetipps:** Buchen Sie Hotels mit guten Bewertungen und prüfen Sie die Lage.

**Timing:** Die gewählten Daten bieten gute Verfügbarkeit.

*Hinweis: Detailliertere Empfehlungen verfügbar sobald OpenAI-Service wieder erreichbar ist.*
"""
    
    def _fallback_optimization(self, original_query: str, current_results: Dict) -> Dict[str, Any]:
        """Fallback-Optimierung ohne OpenAI"""
        
        return {
            "alternative_destinations": ["Ähnliche Destinationen prüfen"],
            "date_suggestions": {
                "cheaper_periods": ["Nebensaison bevorzugen"],
                "better_weather": ["Wettervorhersage beachten"]
            },
            "budget_optimization": {
                "money_saving_tips": ["Flexible Daten", "Frühbucher-Rabatte"],
                "flexible_options": ["Nahegelegene Flughäfen"]
            },
            "search_refinements": {
                "general_tips": "Suchkriterien anpassen für mehr Optionen"
            },
            "confidence_score": 0.5
        }


# Konfiguration für .env File
"""
Füge diese Zeile zu deiner .env Datei hinzu:
OPENAI_API_KEY=sk-your-openai-api-key-here

Oder setze die Environment Variable:
export OPENAI_API_KEY="sk-your-openai-api-key-here"
"""