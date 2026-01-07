import json
import re
from typing import Dict, Any, Optional

from .prompts import SystemPrompts
from config import Config
from openai import (
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from rag.schema_retriever import SchemaRetriever
from utils.context_loader import load_context_files
from database.manager import DatabaseManager


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

    def _ensure_routing_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validiert, dass wichtige Felder in der DB-Routing-Antwort vorhanden sind."""
        ensured = result.copy()
        ensured.setdefault("selected_database", None)
        ensured.setdefault("reason", "")
        try:
            ensured["confidence"] = float(ensured.get("confidence", 0.0))
        except (TypeError, ValueError):
            ensured["confidence"] = 0.0
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

    def route_database(
        self,
        question: str,
        profiles: list[dict[str, str]],
    ) -> Dict[str, Any]:
        """Wählt die passende Datenbank anhand der Profile aus."""
        profiles_text = "\n\n".join(
            [
                (
                    f"DATABASE: {profile['database']}\n"
                    f"SCHEMA SNIPPET:\n{profile['schema_snippet']}\n\n"
                    f"KB SNIPPET:\n{profile['kb_snippet']}\n\n"
                    f"MEANINGS SNIPPET:\n{profile['meanings_snippet']}"
                )
                for profile in profiles
            ]
        )

        prompt = f"""
USER QUESTION:
{question}

DATABASE PROFILES:
{profiles_text}
"""
        response = self._call_openai(SystemPrompts.DATABASE_ROUTING, prompt)
        return self._ensure_routing_fields(self._parse_json_response(response))

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
    
    def generate_sql_with_react_retrieval(
        self,
        question: str,
        db_path: str,
        database_name: str,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        ReAct-basierte SQL-Generierung mit gezieltem Schema/KB-Retrieval
        
        ReAct-Prozess:
        1. THINK: Analysiere Frage → identifiziere benötigte Tabellen/KB-Einträge
        2. ACT: Führe Retrieval durch basierend auf Suchanfragen
        3. OBSERVE: Erhalte relevante Schema-Teile/KB-Einträge
        4. REASON: Genug Info? → Ja: SQL generieren, Nein: weitere Suchen
        """
        
        retriever = SchemaRetriever(db_path)
        
        # KB/Meanings einmalig laden und indexieren (falls nötig)
        kb_text, meanings_text = load_context_files(database_name, Config.DATA_DIR)
        retriever.index_kb(kb_text)
        retriever.index_meanings(meanings_text)
        
        # ReAct-Loop
        collected_schema = []
        collected_kb = []
        collected_meanings = []
        all_search_queries = []
        
        for iteration in range(max_iterations):
            # THINK: Analysiere Frage und bestimme Suchanfragen
            if iteration == 0:
                reasoning_prompt = f"""NUTZER-FRAGE: {question}

Analysiere die Frage und identifiziere:
1. Welche Konzepte/Entitäten werden erwähnt? (z.B. "Kunden", "Kredite", "Einkommen")
2. Welche Tabellen könnten diese enthalten?
3. Welche Berechnungen/Formeln werden benötigt?
4. Welche Suchanfragen würden relevante Schema-Teile/KB-Einträge finden?

WICHTIG: Generiere 3-5 spezifische Suchanfragen die verschiedene Aspekte abdecken.

Antworte als JSON."""
            else:
                reasoning_prompt = f"""NUTZER-FRAGE: {question}

BEREITS GEFUNDEN:
- Schema-Chunks: {len(collected_schema)}
- KB-Einträge: {len(collected_kb)}
- Meanings: {len(collected_meanings)}
- Durchgeführte Suchen: {', '.join(all_search_queries)}

GEFUNDENE TABELLEN:
{', '.join(set([line.split()[0] for chunk in collected_schema for line in chunk.split('\n') if 'TABLE:' in line])) if collected_schema else 'Keine'}

Was fehlt noch? Welche weiteren Suchanfragen sind nötig?
Wenn genug Information vorhanden ist, setze "sufficient_info": true.

Antworte als JSON."""
            
            try:
                reasoning_result = self._call_openai(
                    SystemPrompts.REACT_REASONING,
                    reasoning_prompt
                )
                reasoning = self._parse_json_response(reasoning_result)
            except Exception as e:
                print(f"⚠️  Reasoning-Fehler: {str(e)}")
                reasoning = {
                    "search_queries": [question], 
                    "sufficient_info": iteration >= max_iterations - 1
                }
            
            # ACT: Führe Retrieval durch mit erhöhtem top_k
            search_queries = reasoning.get("search_queries", [])
            if not search_queries and iteration == 0:
                # Fallback: Nutze Frage direkt als Suchanfrage
                search_queries = [question]
            
            all_search_queries.extend(search_queries)
            
            # Erhöhte top_k Werte für besseres Retrieval
            schema_top_k = 6 if iteration == 0 else 4
            kb_top_k = 6 if iteration == 0 else 4
            meanings_top_k = 10 if iteration == 0 else 6
            
            for query in search_queries:
                # Schema Retrieval
                schema_chunk = retriever.retrieve_relevant_schema(query, top_k=schema_top_k)
                if schema_chunk and schema_chunk not in collected_schema:
                    collected_schema.append(schema_chunk)
                
                # KB Retrieval
                kb_chunk = retriever.retrieve_relevant_kb(query, top_k=kb_top_k)
                if kb_chunk and kb_chunk not in collected_kb:
                    collected_kb.append(kb_chunk)
                
                # Meanings Retrieval
                meanings_chunk = retriever.retrieve_relevant_meanings(query, top_k=meanings_top_k)
                if meanings_chunk and meanings_chunk not in collected_meanings:
                    collected_meanings.append(meanings_chunk)
            
            # OBSERVE: Prüfe ob genug Info vorhanden
            if reasoning.get("sufficient_info", False) or iteration >= max_iterations - 1:
                break
        
        # SQL Generation mit nur relevanten Informationen
        relevant_schema = "\n\n".join(collected_schema) if collected_schema else None
        relevant_kb = "\n".join(collected_kb) if collected_kb else ""
        relevant_meanings = "\n".join(collected_meanings) if collected_meanings else ""
        
        # NEUER ROBUSTNESS CHECK: Mindestanforderungen prüfen
        min_schema_chunks = 3
        min_kb_entries = 2
        
        print(f"📊 Retrieval Statistik: {len(collected_schema)} Schema-Chunks, "
              f"{len(collected_kb)} KB-Einträge, {len(collected_meanings)} Meanings")
        
        if (len(collected_schema) < min_schema_chunks or 
            len(collected_kb) < min_kb_entries):
            print(f"⚠️  Unzureichendes Retrieval - erweitere Suche mit breiten Anfragen...")
            
            # Zusätzliche breite Suchen
            broad_queries = [
                question,  # Die originale Frage
                " ".join(question.split()[:4]),  # Erste 4 Wörter
                " ".join(question.split()[-4:])  # Letzte 4 Wörter
            ]
            
            # Extrahiere Key-Begriffe aus der Frage
            key_terms = []
            financial_terms = ['financial', 'debt', 'income', 'asset', 'liability', 
                              'credit', 'vulnerability', 'hardship', 'net worth', 
                              'delinquency', 'payment', 'customer', 'segment',
                              'engagement', 'digital', 'cohort', 'tenure', 'investment',
                              'liquidity', 'score', 'ratio', 'balance']
            for term in financial_terms:
                if term.lower() in question.lower():
                    key_terms.append(term)
            
            if key_terms:
                broad_queries.extend(key_terms[:3])  # Top 3 gefundene Begriffe
            
            for query in broad_queries:
                schema_chunk = retriever.retrieve_relevant_schema(query, top_k=8)
                if schema_chunk and schema_chunk not in collected_schema:
                    collected_schema.append(schema_chunk)
                    print(f"  ✓ Zusätzlicher Schema-Chunk gefunden für: '{query}'")
                
                kb_chunk = retriever.retrieve_relevant_kb(query, top_k=8)
                if kb_chunk and kb_chunk not in collected_kb:
                    collected_kb.append(kb_chunk)
                    print(f"  ✓ Zusätzlicher KB-Eintrag gefunden für: '{query}'")
                
                meanings_chunk = retriever.retrieve_relevant_meanings(query, top_k=10)
                if meanings_chunk and meanings_chunk not in collected_meanings:
                    collected_meanings.append(meanings_chunk)
            
            relevant_schema = "\n\n".join(collected_schema) if collected_schema else None
            relevant_kb = "\n".join(collected_kb) if collected_kb else ""
            relevant_meanings = "\n".join(collected_meanings) if collected_meanings else ""
            
            print(f"📊 Nach Erweiterung: {len(collected_schema)} Schema-Chunks, "
                  f"{len(collected_kb)} KB-Einträge")
        
        # FALLBACK: Wenn IMMER NOCH nichts oder sehr wenig gefunden
        if not relevant_schema or len(collected_schema) < 2:
            print("⚠️  Kritisch wenig Information gefunden - verwende komplettes Schema als Fallback")
            db_manager = DatabaseManager(db_path)
            relevant_schema = db_manager.get_schema_and_sample()
            relevant_kb = kb_text
            relevant_meanings = meanings_text
            
            # Markiere als Fallback in Metadaten
            fallback_used = True
        else:
            fallback_used = False
        
        # Generiere SQL
        prompt = f"""### RELEVANTE DATENBANK SCHEMA-TEILE:
{relevant_schema}

### RELEVANTE SPALTEN BEDEUTUNGEN:
{relevant_meanings}

### RELEVANTE DOMAIN WISSEN & FORMELN:
{relevant_kb}

### NUTZER-FRAGE:
{question}

Generiere die SQL-Query im JSON-Format."""
        
        try:
            response = self._call_openai(SystemPrompts.REACT_SQL_GENERATION, prompt)
            result = self._ensure_generation_fields(self._parse_json_response(response))
            
            # Metadaten für Debugging und Monitoring
            result["retrieval_info"] = {
                "schema_chunks_used": len(collected_schema),
                "kb_entries_used": len(collected_kb),
                "meanings_entries_used": len(collected_meanings),
                "search_queries": all_search_queries,
                "iterations": iteration + 1,
                "fallback_to_full_schema": fallback_used
            }
            
            # SQL säubern
            if result.get("sql"):
                result["sql"] = result["sql"].replace("```sql", "").replace("```", "").strip()
            
            # Warnung wenn Fallback verwendet wurde
            if fallback_used and result.get("sql"):
                result["explanation"] += " [Hinweis: Vollständiges Schema als Fallback verwendet]"
            
            return result
            
        except Exception as e:
            return {
                "sql": None,
                "explanation": f"Fehler bei ReAct SQL-Generierung: {str(e)}",
                "confidence": 0.0,
                "retrieval_info": {
                    "schema_chunks_used": len(collected_schema),
                    "kb_entries_used": len(collected_kb),
                    "search_queries": all_search_queries,
                    "error": str(e)
                }
            }
    
    def generate_sql_with_correction(
        self,
        question: str,
        schema: str,
        kb: str,
        meanings: str,
        max_iterations: int = 2
    ) -> Dict[str, Any]:
        """Generate SQL with self-correction loop"""
        sql_result = None
        validation_result = None
        
        for iteration in range(max_iterations):
            # Generate or correct SQL
            if iteration == 0:
                # Initial generation
                sql_result = self.generate_sql(question, schema, kb, meanings)
            else:
                # Correction based on validation errors
                correction_prompt = f"""
VORHERIGE SQL (FEHLERHAFT):
{sql_result.get("sql")}

VALIDIERUNGS-FEHLER:
{chr(10).join(validation_result.get("errors", []))}

NUTZER-FRAGE:
{question}

DATENBANK SCHEMA:
{schema}

Korrigiere die SQL-Query basierend auf den Fehlern.
"""
                try:
                    response = self._call_openai(SystemPrompts.SQL_GENERATION, correction_prompt)
                    sql_result = self._ensure_generation_fields(self._parse_json_response(response))
                    if sql_result.get("sql"):
                        sql_result["sql"] = sql_result["sql"].replace("```sql", "").replace("```", "").strip()
                except Exception as e:
                    print(f"⚠️  SQL-Korrektur fehlgeschlagen: {str(e)}")
                    break
            
            if not sql_result or not sql_result.get("sql"):
                break
            
            # Validate
            validation_result = self.validate_sql(sql_result["sql"], schema)
            
            # If valid or only low severity, return
            if validation_result.get("is_valid") or validation_result.get("severity") != "high":
                sql_result["correction_iterations"] = iteration + 1
                return sql_result
        
        # Return best attempt even if not perfect
        if sql_result:
            sql_result["correction_iterations"] = max_iterations
            sql_result["validation_warnings"] = validation_result.get("errors", []) if validation_result else []
        
        return sql_result or {
            "sql": None,
            "explanation": "SQL-Generierung nach mehreren Versuchen fehlgeschlagen.",
            "confidence": 0.0
        }
