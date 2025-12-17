import json
import re
from typing import Dict, Any, Optional

from .prompts import SystemPrompts
from openai import (
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)


class OpenAIGenerator:
    """Handhabt alle LLM-Interaktionen mit OpenAI/ChatGPT"""

    def __init__(self, api_key: str, model_name: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def _call_openai(self, system_instruction: str, prompt: str) -> str:
        """Generischer OpenAI ChatCompletion Call"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            return content.strip()
        except RateLimitError as e:
            raise RuntimeError(
                "OpenAI-Kontingent oder Rate-Limit überschritten. Bitte Schlüssel, Plan "
                "oder Billing-Einstellungen prüfen."
            ) from e
        except AuthenticationError as e:
            raise RuntimeError(
                "OpenAI-Authentifizierung fehlgeschlagen – ist der API-Schlüssel gültig?"
            ) from e
        except APIStatusError as e:
            if e.status_code == 429:
                raise RuntimeError(
                    "OpenAI meldet 'Too Many Requests/Quota exceeded'. Bitte Kontingent "
                    "prüfen oder später erneut versuchen."
                ) from e
            raise

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON Response und entferne Markdown - sehr robust"""
        cleaned = response.replace("```json", "").replace("```", "").strip()

        start = cleaned.find('{')
        if start == -1:
            raise ValueError("Kein JSON-Objekt gefunden in Response")

        brace_count = 0
        end = start
        in_string = False
        escape_next = False

        for i in range(start, len(cleaned)):
            char = cleaned[i]

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

            # Versuche tolerant zu parsen (z. B. bei unescapten Newlines in Strings)
            try:
                return json.loads(json_str, strict=False)
            except json.JSONDecodeError:
                pass

            # Entferne Steuerzeichen als letzte Rettung
            sanitized = re.sub(r"[\x00-\x1f\x7f]", " ", json_str)
            if sanitized != json_str:
                try:
                    print("🧹 Entferne Steuerzeichen und versuche erneut zu parsen...")
                    return json.loads(sanitized, strict=False)
                except json.JSONDecodeError:
                    pass

            raise

    def _ensure_generation_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validiert, dass wichtige Felder in der SQL-Generierung vorhanden sind."""
        ensured = result.copy()
        ensured.setdefault("thought_process", "")
        ensured.setdefault("explanation", "")

        # confidence in Float casten, falls möglich
        try:
            ensured["confidence"] = float(ensured.get("confidence", 0.0))
        except (TypeError, ValueError):
            ensured["confidence"] = 0.0

        if "sql" not in ensured:
            ensured["sql"] = None

        return ensured
    
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
            response = self._call_openai(SystemPrompts.AMBIGUITY_DETECTION, prompt)
            return self._parse_json_response(response)
        except Exception as e:
            return {
                "is_ambiguous": False,
                "reason": f"Fehler bei Ambiguity Check: {str(e)}",
                "questions": []
            }
    
    def generate_sql(
        self,
        question: str,
        schema: str,
        kb: str,
        meanings: str,
    ) -> Dict[str, Any]:
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
            response = self._call_openai(SystemPrompts.SQL_GENERATION, prompt)
            print("📤 LLM Rohe Response (erste 800 Zeichen):")
            print(f"{response[:800]}\n")

            result = self._ensure_generation_fields(self._parse_json_response(response))

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
            response = self._call_openai(SystemPrompts.SQL_VALIDATION, prompt)
            return self._parse_json_response(response)
        except Exception as e:
            return {
                "is_valid": True,
                "errors": [f"Validation-Fehler: {str(e)}"],
                "severity": "low",
                "suggestions": []
            }

    def summarize_results(
        self,
        question: str,
        generated_sql: str,
        results: Any,
        row_count: int,
        notice: Optional[str] = None,
    ) -> str:
        """Erzeugt eine Kurz-Zusammenfassung der Abfrageergebnisse."""

        sample_rows = results[:3] if isinstance(results, list) else []
        prompt = f"""
NUTZER-FRAGE:
{question}

GENERIERTE SQL:
{generated_sql}

ANZAHL ZEILEN: {row_count}
HINWEIS: {notice or 'keiner'}

ERSTE ZEILEN (JSON):
{json.dumps(sample_rows, ensure_ascii=False)}

Fasse die wichtigsten Erkenntnisse kurz zusammen.
"""

        try:
            return self._call_openai(SystemPrompts.RESULT_SUMMARY, prompt)
        except Exception as e:
            print(f"⚠️  Zusammenfassung fehlgeschlagen: {str(e)}")
            raise
