import google.generativeai as genai
import json
from typing import Dict, Any, Optional
from .prompts import SystemPrompts

class GeminiGenerator:
    """Handhabt alle LLM-Interaktionen mit Gemini"""
    
    def __init__(self, api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        self.model_name = model_name
    
    def _call_gemini(self, system_instruction: str, prompt: str) -> str:
        """Generischer Gemini API Call"""
        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=system_instruction
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON Response und entferne Markdown - sehr robust"""
        # Entferne Markdown Code Blocks
        cleaned = response.replace("```json", "").replace("```", "").strip()
        
        # Suche nach dem ersten { und finde das zugehörige schließende }
        start = cleaned.find('{')
        if start == -1:
            raise ValueError("Kein JSON-Objekt gefunden in Response")
        
        # Zähle geschweifte Klammern um das komplette erste JSON-Objekt zu finden
        brace_count = 0
        end = start
        in_string = False
        escape_next = False
        
        for i in range(start, len(cleaned)):
            char = cleaned[i]
            
            # String-Handling (um { und } in Strings zu ignorieren)
            if char == '"' and not escape_next:
                in_string = not in_string
            elif char == '\\' and not escape_next:
                escape_next = True
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            escape_next = False
        
        if brace_count != 0:
            raise ValueError(f"Unbalancierte geschweifte Klammern (count={brace_count})")
        
        json_str = cleaned[start:end]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON Parse Fehler: {str(e)}")
            print(f"📄 Extrahiertes JSON (erste 1000 Zeichen):\n{json_str[:1000]}\n")
            raise
    
    def check_ambiguity(self, question: str, schema: str, kb: str, meanings: str) -> Dict[str, Any]:
        """Prüft ob die Frage mehrdeutig ist"""
        prompt = f"""
DATENBANK SCHEMA:
{schema}

SPALTEN BEDEUTUNGEN:
{meanings}

DOMAIN WISSEN:
{kb}

NUTZER-FRAGE:
{question}

Analysiere die Frage auf Mehrdeutigkeit.
"""
        try:
            response = self._call_gemini(SystemPrompts.AMBIGUITY_DETECTION, prompt)
            return self._parse_json_response(response)
        except Exception as e:
            return {
                "is_ambiguous": False,
                "reason": f"Fehler bei Ambiguity Check: {str(e)}",
                "questions": []
            }
    
    def generate_sql(self, question: str, schema: str, kb: str, meanings: str) -> Dict[str, Any]:
        """Generiert SQL aus der Nutzer-Frage"""
        prompt = f"""
### DATENBANK SCHEMA & BEISPIELDATEN:
{schema}

### SPALTEN BEDEUTUNGEN:
{meanings}

### DOMAIN WISSEN & FORMELN (WICHTIG - EXAKT UMSETZEN!):
{kb}

### NUTZER-FRAGE:
{question}

Generiere die SQL-Query im JSON-Format.
"""
        try:
            response = self._call_gemini(SystemPrompts.SQL_GENERATION, prompt)
            print(f"📤 LLM Rohe Response (erste 800 Zeichen):")
            print(f"{response[:800]}\n")
            
            result = self._parse_json_response(response)
            
            # SQL säubern falls vorhanden
            if result.get("sql"):
                sql = result["sql"].replace("```sql", "").replace("```", "").strip()
                result["sql"] = sql
            
            return result
        except json.JSONDecodeError as e:
            return {
                "thought_process": "JSON Parse Error",
                "sql": None,
                "explanation": f"LLM gab kein valides JSON zurück: {str(e)}",
                "confidence": 0.0
            }
        except Exception as e:
            return {
                "thought_process": "",
                "sql": None,
                "explanation": f"Fehler bei SQL-Generierung: {str(e)}",
                "confidence": 0.0
            }
    
    def validate_sql(self, sql: str, schema: str) -> Dict[str, Any]:
        """Validiert die generierte SQL-Query"""
        prompt = f"""
DATENBANK SCHEMA:
{schema}

GENERIERTE SQL-QUERY:
{sql}

Validiere die Query.
"""
        try:
            response = self._call_gemini(SystemPrompts.SQL_VALIDATION, prompt)
            return self._parse_json_response(response)
        except Exception as e:
            return {
                "is_valid": True,  # Im Fehlerfall versuchen wir es trotzdem
                "errors": [f"Validation-Fehler: {str(e)}"],
                "severity": "low",
                "suggestions": []
            }