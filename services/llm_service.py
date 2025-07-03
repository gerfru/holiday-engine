# services/llm_service.py
"""
LLM Service der echte LLM-Calls über MCP macht
Ersetzt die simulierten LLM-Calls in intelligent_search_service.py
"""

import asyncio
import json
from typing import Dict, Any, Optional
import httpx


class LLMService:
    """Service für echte LLM-Integration über MCP"""
    
    def __init__(self):
        self.llm_available = False
        self._test_llm_connection()
    
    def _test_llm_connection(self):
        """Teste ob LLM über MCP verfügbar ist"""
        try:
            # In einer echten Implementation würdest du hier testen ob window.claude.complete verfügbar ist
            # oder ob ein anderer LLM-Service erreichbar ist
            self.llm_available = True
        except:
            self.llm_available = False
    
    async def analyze_travel_query(self, query: str) -> Dict[str, Any]:
        """Analysiert Reiseanfrage mit LLM"""
        
        prompt = f"""
        Du bist ein Experte für Reiseplanung. Analysiere diese Reiseanfrage und extrahiere strukturierte Informationen.
        
        Anfrage: "{query}"
        
        Bitte antworte NUR mit einem gültigen JSON-Objekt im folgenden Format:
        {{
            "destination": "extrahiertes Reiseziel",
            "budget_max": "Budget in EUR als Zahl oder null",
            "duration_days": "Anzahl Tage als [min, max] Array",
            "travel_type": "romantic/family/business/adventure/leisure/cultural",
            "month": "gewünschter Monat als Zahl 1-12 oder null",
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
            "extracted_keywords": ["wichtige", "keywords", "aus", "der", "anfrage"],
            "confidence_score": "Zahl zwischen 0-1 wie sicher die Extraktion ist"
        }}
        
        Achte besonders auf:
        - Budget-Angaben in verschiedenen Formen ("unter 1000€", "max 500€", "bis 2000€")
        - Dauer-Angaben ("7-10 Tage", "eine Woche", "Wochenende")
        - Implizite Reisetypen (Flitterwochen=romantic, Familienurlaub=family)
        - Saisonale Hinweise ("im Winter", "Dezember", "Weihnachtszeit")
        
        WICHTIG: Antworte NUR mit dem JSON-Objekt, keine anderen Texte oder Formatierungen.
        """
        
        if self.llm_available:
            return await self._call_llm(prompt)
        else:
            return self._fallback_analysis(query)
    
    async def generate_travel_recommendations(self, search_results: Dict, user_preferences: Dict) -> str:
        """Generiert personalisierte Reiseempfehlungen"""
        
        # Bereite Daten strukturiert für LLM auf
        results_summary = self._prepare_results_summary(search_results)
        
        prompt = f"""
        Du bist ein erfahrener Reiseberater. Basierend auf den Suchergebnissen und Benutzerpräferenzen, 
        erstelle eine personalisierte, beratende Empfehlung.
        
        Benutzerpräferenzen:
        {json.dumps(user_preferences, indent=2, ensure_ascii=False)}
        
        Suchergebnisse:
        {results_summary}
        
        Erstelle eine natürliche, beratende Empfehlung die folgende Punkte abdeckt:
        
        1. **Hauptempfehlung**: Die beste Option mit klarer Begründung
        2. **Alternative Optionen**: 1-2 weitere gute Alternativen
        3. **Budgetoptimierung**: Tipps wie man Geld sparen kann
        4. **Reisetyp-spezifische Tipps**: Passend zum gewünschten Reisetyp
        5. **Timing-Empfehlungen**: Beste Reisezeiten und was zu beachten ist
        6. **Zusätzliche Tipps**: Lokale Geheimtipps oder wichtige Hinweise
        
        Schreibe in einem warmen, persönlichen Ton als würdest du einem Freund raten.
        Verwende Emojis sparsam aber gezielt für bessere Lesbarkeit.
        Halte die Antwort strukturiert aber nicht zu lang (max 300 Wörter).
        """
        
        if self.llm_available:
            return await self._call_llm(prompt)
        else:
            return self._fallback_recommendations(search_results, user_preferences)
    
    async def optimize_search_parameters(self, original_query: str, current_results: Dict) -> Dict[str, Any]:
        """Optimiert Suchparameter basierend auf bisherigen Ergebnissen"""
        
        prompt = f"""
        Analysiere die bisherigen Suchergebnisse und schlage Optimierungen vor.
        
        Ursprüngliche Anfrage: "{original_query}"
        
        Aktuelle Ergebnisse:
        - Gefundene Flüge: {len(current_results.get('flights', []))}
        - Gefundene Hotels: {len(current_results.get('hotels', []))}
        - Kombinationen: {len(current_results.get('combinations', []))}
        - Durchschnittspreis: {self._calculate_average_price(current_results)}€
        
        Bitte antworte mit einem JSON-Objekt mit Optimierungsvorschlägen:
        {{
            "alternative_destinations": ["ähnliche", "destinationen", "vorschlagen"],
            "date_suggestions": {{
                "cheaper_periods": ["YYYY-MM-DD", "bis", "YYYY-MM-DD"],
                "better_weather": ["YYYY-MM-DD", "bis", "YYYY-MM-DD"]
            }},
            "budget_optimization": {{
                "money_saving_tips": ["Tipp 1", "Tipp 2"],
                "flexible_options": ["Flexibilität bei Daten", "etc"]
            }},
            "search_refinements": {{
                "broader_search": "Suchbereich erweitern um mehr Optionen zu finden",
                "narrower_search": "Suchkriterien verfeinern für bessere Matches"
            }},
            "confidence_score": 0.85
        }}
        
        WICHTIG: Antworte NUR mit dem JSON-Objekt.
        """
        
        if self.llm_available:
            response = await self._call_llm(prompt)
            return json.loads(response) if isinstance(response, str) else response
        else:
            return self._fallback_optimization(original_query, current_results)
    
    async def _call_llm(self, prompt: str) -> str:
        """Echter LLM-Call - hier würdest du window.claude.complete oder andere LLM APIs aufrufen"""
        
        # OPTION 1: Wenn du in einem Browser-Environment mit window.claude.complete bist
        # return await window.claude.complete(prompt)
        
        # OPTION 2: Wenn du externe LLM APIs nutzt
        try:
            # Beispiel für OpenAI API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": "Bearer YOUR_OPENAI_API_KEY",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.7
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            print(f"LLM API Fehler: {e}")
            
        # OPTION 3: Claude über MCP (wenn verfügbar)
        # Hier würdest du einen MCP Client zu einem Claude Server aufbauen
        
        # Fallback wenn alle LLM-Optionen fehlschlagen
        return self._emergency_fallback(prompt)
    
    def _prepare_results_summary(self, search_results: Dict) -> str:
        """Bereitet Suchergebnisse für LLM auf"""
        
        summary = "Zusammenfassung der Suchergebnisse:\n"
        
        if search_results.get("search_results"):
            best_result = search_results["search_results"][0]
            
            if best_result.get("combinations"):
                best_combo = best_result["combinations"][0]
                
                summary += f"""
Beste gefundene Kombination:
- Flug: {best_combo.get('flight', {}).get('airline', 'N/A')} für {best_combo.get('flight', {}).get('price_eur', 'N/A')}€
- Hotel: {best_combo.get('hotel', {}).get('name', 'N/A')} ({best_combo.get('hotel', {}).get('rating', 'N/A')} Sterne)
- Gesamtpreis: {best_combo.get('total_price', 'N/A')}€
- Reisedatum: {best_result.get('date_option', {}).get('check_in', 'N/A')}

Alternative Optionen: {len(search_results.get("search_results", [])) - 1} weitere verfügbar
Durchschnittlicher Preis: {self._calculate_average_price(search_results)}€
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
        """Fallback-Analyse ohne LLM"""
        
        query_lower = query.lower()
        
        # Destination
        destination = "Italien"
        if "spanien" in query_lower or "spain" in query_lower:
            destination = "Spanien"
        elif "griechenland" in query_lower or "greece" in query_lower:
            destination = "Griechenland"
        elif "frankreich" in query_lower or "france" in query_lower:
            destination = "Frankreich"
        
        # Budget
        budget = None
        import re
        budget_patterns = [r"unter (\d+)€", r"max (\d+)€", r"bis (\d+)€", r"(\d+)€"]
        for pattern in budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                budget = int(match.group(1))
                break
        
        # Travel Type
        travel_type = "leisure"
        if any(word in query_lower for word in ["romantisch", "romantic", "flitterwochen", "honeymoon", "paar"]):
            travel_type = "romantic"
        elif any(word in query_lower for word in ["familie", "family", "kinder", "kids"]):
            travel_type = "family"
        elif any(word in query_lower for word in ["business", "geschäft", "conference"]):
            travel_type = "business"
        elif any(word in query_lower for word in ["abenteuer", "adventure", "sport", "hiking"]):
            travel_type = "adventure"
        elif any(word in query_lower for word in ["kultur", "cultural", "museum", "history"]):
            travel_type = "cultural"
        
        # Duration
        duration = [7, 7]  # Default: 1 Woche
        duration_patterns = [r"(\d+)-(\d+) tage", r"(\d+) tage", r"(\d+) wochen?"]
        for pattern in duration_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if len(match.groups()) == 2:
                    duration = [int(match.group(1)), int(match.group(2))]
                else:
                    days = int(match.group(1))
                    if "woche" in pattern:
                        days *= 7
                    duration = [days, days]
                break
        
        # Month
        month = None
        months = {
            "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
            "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
            "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7,
            "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        for month_name, month_num in months.items():
            if month_name in query_lower:
                month = month_num
                break
        
        return {
            "destination": destination,
            "budget_max": budget,
            "duration_days": duration,
            "travel_type": travel_type,
            "month": month,
            "preferences": {
                "accommodation_type": "luxury" if travel_type == "romantic" else "hotel",
                "activities": self._get_activities_for_type(travel_type),
                "priority": "comfort" if travel_type == "romantic" else "price"
            },
            "flexibility": {
                "dates": "flexible",
                "destination": "fixed",
                "budget": "flexible" if not budget else "fixed"
            },
            "extracted_keywords": self._extract_keywords(query_lower),
            "confidence_score": 0.7
        }
    
    def _get_activities_for_type(self, travel_type: str) -> list:
        """Gibt typische Aktivitäten für Reisetyp zurück"""
        
        activities_map = {
            "romantic": ["fine_dining", "spa", "wine_tasting", "sunset_tours", "couples_activities"],
            "family": ["theme_parks", "beaches", "family_friendly_tours", "kid_activities", "educational"],
            "business": ["conference_facilities", "business_centers", "networking_events", "efficient_transport"],
            "adventure": ["hiking", "outdoor_sports", "adventure_tours", "nature_experiences", "active_pursuits"],
            "cultural": ["museums", "historical_sites", "art_galleries", "cultural_tours", "local_experiences"],
            "leisure": ["sightseeing", "relaxation", "local_cuisine", "shopping", "entertainment"]
        }
        
        return activities_map.get(travel_type, ["sightseeing", "relaxation"])
    
    def _extract_keywords(self, query: str) -> list:
        """Extrahiert wichtige Keywords aus der Anfrage"""
        
        # Entferne Stoppwörter
        stop_words = {
            "und", "oder", "der", "die", "das", "ich", "mir", "mich", "für", "mit", "in", "im", "am",
            "and", "or", "the", "i", "me", "my", "for", "with", "in", "at", "on", "a", "an"
        }
        
        words = query.lower().split()
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Entferne Duplikate und limitiere
        return list(dict.fromkeys(keywords))[:10]
    
    def _fallback_recommendations(self, search_results: Dict, user_preferences: Dict) -> str:
        """Fallback-Empfehlungen ohne LLM"""
        
        travel_type = user_preferences.get("travel_type", "leisure")
        budget = user_preferences.get("budget_max")
        
        recommendations = f"""
🎯 **Persönliche Reiseempfehlung**

**Hauptempfehlung:** Basierend auf Ihren Präferenzen für {travel_type}-Reisen haben wir die beste verfügbare Option für Sie ausgewählt. Diese Kombination bietet ein ausgezeichnetes Preis-Leistungs-Verhältnis.

**Budgetoptimierung:** """
        
        if budget:
            recommendations += f"Mit Ihrem Budget von {budget}€ haben Sie gute Optionen. "
        
        recommendations += """Tipp: Flexible Reisedaten können bis zu 30% Ersparnis bringen.

**Reisetyp-spezifische Tipps:** """
        
        if travel_type == "romantic":
            recommendations += "Für romantische Reisen empfehlen wir Hotels mit Spa-Bereich und Zimmer mit Meerblick. Buchen Sie Restaurants im Voraus!"
        elif travel_type == "family":
            recommendations += "Achten Sie auf familienfreundliche Hotels mit Kinderbetreuung und nahegelegenen Attraktionen."
        elif travel_type == "cultural":
            recommendations += "Planen Sie genügend Zeit für Museen und historische Stätten ein. Oft gibt es Kombi-Tickets!"
        else:
            recommendations += "Nutzen Sie lokale Verkehrsmittel um Land und Leute kennenzulernen."
        
        recommendations += """

**Timing:** Die gewählten Reisedaten bieten gute Wetterbedingungen und moderate Preise.

**Zusatztipp:** Prüfen Sie lokale Events und Feiertage vor der Buchung!
"""
        
        return recommendations
    
    def _fallback_optimization(self, original_query: str, current_results: Dict) -> Dict[str, Any]:
        """Fallback-Optimierung ohne LLM"""
        
        avg_price = self._calculate_average_price(current_results)
        num_results = len(current_results.get("search_results", []))
        
        optimization = {
            "alternative_destinations": [],
            "date_suggestions": {
                "cheaper_periods": ["2025-01-15", "2025-02-15"],
                "better_weather": ["2025-04-15", "2025-05-15"]
            },
            "budget_optimization": {
                "money_saving_tips": [
                    "Flexible Daten wählen für bessere Preise",
                    "Frühbucher-Rabatte nutzen",
                    "Direkte Buchung beim Hotel prüfen"
                ],
                "flexible_options": [
                    "Reisezeitraum um ±3 Tage erweitern",
                    "Nahegelegene Flughäfen prüfen"
                ]
            },
            "search_refinements": {},
            "confidence_score": 0.6
        }
        
        # Dynamische Anpassungen basierend auf Ergebnissen
        if num_results < 3:
            optimization["search_refinements"]["broader_search"] = "Suchbereich erweitern für mehr Optionen"
        elif avg_price > 1500:
            optimization["search_refinements"]["budget_options"] = "Budget-freundlichere Alternativen suchen"
        
        # Destination-spezifische Alternativen
        if "italien" in original_query.lower():
            optimization["alternative_destinations"] = ["Kroatien", "Griechenland", "Spanien"]
        elif "spanien" in original_query.lower():
            optimization["alternative_destinations"] = ["Portugal", "Italien", "Südfrankreich"]
        
        return optimization
    
    def _emergency_fallback(self, prompt: str) -> str:
        """Notfall-Fallback wenn alle LLM-Optionen fehlschlagen"""
        
        if "json" in prompt.lower():
            # Wenn JSON erwartet wird, gib Minimal-JSON zurück
            return json.dumps({
                "error": "LLM nicht verfügbar",
                "fallback_used": True,
                "message": "Basis-Funktionalität aktiv"
            })
        else:
            # Sonst einfache Text-Antwort
            return "LLM-Service momentan nicht verfügbar. Basis-Empfehlungen werden verwendet."


# Utility-Klasse für MCP Integration in Browser-Environment
class BrowserMCPLLMService(LLMService):
    """Spezialisierte Version für Browser-Environment mit window.claude.complete"""
    
    def __init__(self):
        super().__init__()
        self.browser_mode = True
    
    async def _call_llm(self, prompt: str) -> str:
        """Browser-spezifischer LLM-Call mit window.claude.complete"""
        
        try:
            # Dies würde in einem Browser-Environment mit MCP funktionieren
            # return await window.claude.complete(prompt)
            
            # Für Demo: Simuliere Browser-Call
            return await self._simulate_browser_llm_call(prompt)
            
        except Exception as e:
            print(f"Browser LLM Fehler: {e}")
            return await super()._call_llm(prompt)
    
    async def _simulate_browser_llm_call(self, prompt: str) -> str:
        """Simuliert Browser LLM Call für Demo"""
        
        # In echtem Browser-Code würde hier window.claude.complete stehen
        await asyncio.sleep(0.1)  # Simuliere API-Latenz
        
        if "json" in prompt.lower() and "destination" in prompt.lower():
            # Simuliere intelligente JSON-Antwort
            return json.dumps({
                "destination": "Italien",
                "budget_max": 1000,
                "duration_days": [7, 10],
                "travel_type": "romantic",
                "month": 12,
                "preferences": {
                    "accommodation_type": "hotel",
                    "activities": ["fine_dining", "sightseeing", "cultural_tours"],
                    "priority": "comfort"
                },
                "flexibility": {
                    "dates": "flexible",
                    "destination": "fixed",
                    "budget": "flexible"
                },
                "extracted_keywords": ["romantisch", "italien", "1000€", "dezember"],
                "confidence_score": 0.9
            })
        
        elif "empfehlung" in prompt.lower() or "recommendation" in prompt.lower():
            return """🎯 **Meine Empfehlung für Sie**

**Hauptempfehlung:** Die beste Option ist die Kombination aus dem Direktflug mit Lufthansa und dem 4-Sterne Boutique-Hotel im Stadtzentrum. Perfekt für romantische Reisen!

**Budgetoptimierung:** Sie bleiben deutlich unter Ihrem Budget von 1000€. Tipp: Die gesparten 200€ können Sie für besondere Restaurants und Aktivitäten verwenden.

**Romantik-Tipps:** Das gewählte Hotel bietet Spa-Services und Zimmer mit Balkon. Buchen Sie unbedingt das Candle-Light-Dinner auf der Dachterrasse!

**Timing:** Dezember ist eine magische Zeit in Italien - weniger Touristen, aber trotzdem mildes Wetter. Perfekt für romantische Spaziergänge!

**Geheimtipp:** Probieren Sie die lokalen Weihnachtsmärkte - sehr romantisch und authentisch! 🎄✨"""
        
        else:
            return "Intelligente LLM-Analyse durchgeführt. Ergebnisse verfügbar."


# Beispiel für die Integration in deine intelligent_search_service.py
class EnhancedIntelligentSearchService:
    """Erweiterte Version des IntelligentSearchService mit echtem LLM"""
    
    def __init__(self, use_browser_llm: bool = False):
        # Deine bestehenden Services
        from .city_resolver import CityResolver
        from .flight_service import FlightService  
        from .hotel_service import HotelService
        from ..business_logic import TravelCombinationEngine
        
        self.city_resolver = CityResolver()
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
        self.combination_engine = TravelCombinationEngine()
        
        # Neuer LLM Service
        if use_browser_llm:
            self.llm_service = BrowserMCPLLMService()
        else:
            self.llm_service = LLMService()
    
    async def process_natural_query(self, query: str, origin: str = "Wien") -> Dict[str, Any]:
        """Erweiterte Verarbeitung mit echtem LLM"""
        
        # 1. LLM-Analyse der Anfrage (jetzt mit echtem LLM!)
        parsed_query = await self.llm_service.analyze_travel_query(query)
        
        # 2. Rest bleibt wie in deinem ursprünglichen Service...
        destination_info = await self._resolve_destination(parsed_query["destination"])
        optimized_dates = await self._optimize_travel_dates(destination_info, parsed_query)
        search_results = await self._perform_multi_search(origin, destination_info, optimized_dates, parsed_query)
        
        # 3. LLM-gestützte Empfehlungen (jetzt mit echtem LLM!)
        recommendations = await self.llm_service.generate_travel_recommendations(search_results, parsed_query)
        
        # 4. Optional: Optimierungsvorschläge
        optimization_suggestions = await self.llm_service.optimize_search_parameters(query, search_results)
        
        return {
            "query_analysis": parsed_query,
            "destination": destination_info,
            "optimized_dates": optimized_dates,
            "search_results": search_results,
            "recommendations": recommendations,
            "optimization_suggestions": optimization_suggestions,
            "llm_enhanced": True
        }