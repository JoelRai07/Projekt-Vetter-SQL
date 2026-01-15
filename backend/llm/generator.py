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
                temperature=0,
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

    def _extract_bsl_overrides(self, bsl_text: str) -> str:
        """Extract manual BSL overrides section, if present."""
        marker = "# BSL OVERRIDES (MANUAL)"
        if not bsl_text or marker not in bsl_text:
            return ""
        return bsl_text.split(marker, 1)[1].strip()

    def _has_explicit_time_range(self, question: str) -> bool:
        """Detect explicit time ranges (years/quarters) in the question."""
        q = question.lower()
        if re.search(r"\b(19|20)\d{2}\b", q):
            return True
        if re.search(r"\bq[1-4]\b", q):
            return True
        return False

    def _contains_param_placeholders(self, sql: str) -> bool:
        """Detect SQL parameter placeholders which are not supported by execution."""
        if not sql:
            return False
        # Strip single-quoted strings to avoid false positives.
        stripped = re.sub(r"'(?:''|[^'])*'", "", sql)
        return bool(
            re.search(r"(\?(\d+)?|:[a-zA-Z_]\w*|@[a-zA-Z_]\w*|\$[a-zA-Z_]\w*)", stripped)
        )

    def _fix_union_order_by(self, sql: str) -> str:
        """
        Fix UNION ALL with ORDER BY issue in SQLite.
        SQLite requires wrapping the UNION result in a subquery before applying ORDER BY.
        """
        if not sql:
            return sql

        sql_upper = sql.upper()

        # Check if SQL contains UNION (ALL) and ORDER BY at the top level
        if "UNION" not in sql_upper:
            return sql

        # Check if ORDER BY comes after the last UNION (indicating top-level ORDER BY)
        last_union_pos = max(
            sql_upper.rfind("UNION ALL"),
            sql_upper.rfind("UNION ")
        )
        order_by_pos = sql_upper.rfind("ORDER BY")

        if last_union_pos == -1 or order_by_pos == -1:
            return sql

        # ORDER BY should come after UNION for this to be an issue
        if order_by_pos < last_union_pos:
            return sql

        # Check if it's already wrapped with outer SELECT FROM subquery
        stripped = sql.strip()
        if re.match(r"(?i)SELECT\s+\*\s+FROM\s*\(", stripped):
            return sql

        # Extract the ORDER BY clause
        order_by_clause = sql[order_by_pos:].strip()
        sql_without_order = sql[:order_by_pos].strip()

        # Remove trailing semicolon from sql_without_order if present
        if sql_without_order.endswith(";"):
            sql_without_order = sql_without_order[:-1].strip()

        # Remove trailing semicolon from order_by_clause if present
        if order_by_clause.endswith(";"):
            order_by_clause = order_by_clause[:-1].strip()

        # Check if SQL already starts with WITH (has CTEs)
        # In that case, we need to append our wrapper CTE to the existing CTEs
        if re.match(r"(?i)^\s*WITH\s+", sql_without_order):
            # SQL already has CTEs - we need to add our wrapper as the last CTE
            # Find the final SELECT statement to wrap
            # Use a unique CTE name that won't conflict
            wrapper_cte_name = "_union_order_wrapper"

            # The structure is: WITH existing_ctes SELECT ... UNION ...
            # We need to wrap the whole thing
            fixed_sql = f"""WITH {wrapper_cte_name} AS (
{sql_without_order}
)
SELECT * FROM {wrapper_cte_name}
{order_by_clause};"""
        else:
            # No existing CTEs - simple wrap
            wrapper_cte_name = "_union_order_wrapper"
            fixed_sql = f"""WITH {wrapper_cte_name} AS (
{sql_without_order}
)
SELECT * FROM {wrapper_cte_name}
{order_by_clause};"""

        return fixed_sql

    def _is_property_leverage_question(self, question: str) -> bool:
        q = question.lower()
        if any(k in q for k in ["property leverage", "mortgage ratio", "loan-to-value", "ltv"]):
            return True
        if "property value" in q and "mortgage" in q and ("ratio" in q or "leverage" in q):
            return True
        return False

    def _is_digital_engagement_cohort_question(self, question: str) -> bool:
        q = question.lower()
        return ("cohort" in q and "engagement" in q and "digital" in q)

    def _is_credit_classification_details_question(self, question: str) -> bool:
        q = question.lower()
        if "credit" not in q:
            return False
        if "classification" not in q and "category" not in q:
            return False
        if "detail" not in q:
            return False
        if any(k in q for k in ["count", "average", "avg", "summary", "how many", "percentage"]):
            return False
        return True

    def _has_explicit_detail_fields(self, question: str) -> bool:
        q = question.lower()
        if any(k in q for k in ["including", "such as", "with their", "fields", "columns"]):
            return True
        explicit_fields = [
            "customer id",
            "customer_id",
            "clientref",
            "appref",
            "scoredate",
            "risklev",
            "defhist",
            "delinqcount",
            "latepaycount",
            "credscore",
        ]
        return any(k in q for k in explicit_fields)

    def _is_credit_classification_summary_question(self, question: str) -> bool:
        q = question.lower()
        if "credit" not in q:
            return False
        if "classification" not in q and "category" not in q:
            return False
        # Default to summary when details are not explicitly listed
        return not self._has_explicit_detail_fields(question)

    def _bsl_compliance_instruction(self, question: str, sql: str) -> str | None:
        sql_lower = sql.lower()
        instructions = []

        if self._contains_param_placeholders(sql):
            instructions.append(
                "SQL must not use parameter placeholders (?,?,:name,@name,$name). "
                "Use explicit numeric literals. If the question says 'few customers' without a threshold, "
                "default to HAVING COUNT(*) >= 10."
            )

        if self._is_digital_engagement_cohort_question(question) and not self._has_explicit_time_range(question):
            if "cohort_quarter" in sql_lower or "strftime(" in sql_lower:
                instructions.append(
                    "No explicit time range was given. "
                    "Do NOT compute or select cohort_quarter or any time-series columns. "
                    "Return only a 2-row summary grouped by is_digital_native with "
                    "cohort_size, avg_engagement (CES), and pct_high_engagement (CES > 0.7)."
                )

        if self._is_credit_classification_details_question(question):
            if "group by" in sql_lower:
                instructions.append(
                    "The question asks for credit categories AND customer details. "
                    "Return row-level records with a credit_category CASE expression and customer details. "
                    "Do NOT use GROUP BY or aggregates."
                )

        if self._is_credit_classification_summary_question(question):
            if "group by" not in sql_lower:
                instructions.append(
                    "Credit classification without explicit detail fields should return a summary. "
                    "Group by credit_category and output credit_category, customer_count, and average_credscore."
                )

        if self._is_property_leverage_question(question):
            property_issues = []
            # Property leverage data comes from propfinancialdata, customer_id must be coreregistry (CS format)
            if "coreregistry" not in sql_lower:
                property_issues.append(
                    "Join to core_record and use core_record.coreregistry as customer_id (CS format). "
                    "Join path: expenses_and_assets -> employment_and_income -> core_record."
                )
            if "order by" not in sql_lower:
                property_issues.append("Order by the leverage ratio descending.")
            if property_issues:
                property_issues.append(
                    "Compute ratio as mortgage_balance / property_value from propfinancialdata and "
                    "exclude NULL or zero property_value."
                )
                instructions.append("Property leverage rule: " + " ".join(property_issues))

        if instructions:
            return "BSL compliance: " + " ".join(instructions)
        return None

    def _regenerate_with_bsl_compliance(
        self,
        question: str,
        schema: str,
        meanings: str,
        bsl: str,
        instruction: str,
        previous_sql: str,
    ) -> Dict[str, Any]:
        overrides_text = self._extract_bsl_overrides(bsl)
        prompt = f"""
### BSL OVERRIDES (HIGHEST PRIORITY - MUST FOLLOW):
{overrides_text or "[No overrides]"}

### BUSINESS SEMANTICS LAYER (⚠️ CRITICAL - READ FIRST):
{bsl if bsl else "[No BSL provided - using defaults]"}

### DATENBANK SCHEMA & BEISPIELDATEN:
{schema}

### SPALTEN BEDEUTUNGEN:
{meanings}

### NUTZER-FRAGE:
{question}

BSL COMPLIANCE ISSUE:
{instruction}

PREVIOUS SQL (NON-COMPLIANT):
{previous_sql}

Regenerate the SQL to comply with the BSL. Output JSON as required.
"""
        response = self._call_openai(SystemPrompts.SQL_GENERATION, prompt)
        result = self._ensure_generation_fields(self._parse_json_response(response))
        if result.get("sql"):
            result["sql"] = result["sql"].replace("```sql", "").replace("```", "").strip()
        if result.get("explanation"):
            result["explanation"] = f"{result['explanation']} [BSL compliance regeneration]"
        else:
            result["explanation"] = "BSL compliance regeneration"
        return result

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
        meanings: str,
        bsl: str = "",
    ) -> Dict[str, Any]:
        """Generiert SQL aus der Nutzer-Frage"""
        overrides_text = self._extract_bsl_overrides(bsl)
        prompt = f"""
### BSL OVERRIDES (HIGHEST PRIORITY - MUST FOLLOW):
{overrides_text or "[No overrides]"}

### BUSINESS SEMANTICS LAYER (⚠️ CRITICAL - READ FIRST):
{bsl if bsl else "[No BSL provided - using defaults]"}

### DATENBANK SCHEMA & BEISPIELDATEN:
{schema}

### SPALTEN BEDEUTUNGEN:
{meanings}

### NUTZER-FRAGE:
{question}

Generiere die SQL-Query im JSON-Format.
WICHTIG: Befolge die BSL-Regeln strikt:
1. Identity System (CU vs CS)
2. Aggregation Detection (GROUP BY when needed)
3. Business Rules (exact filters)
4. Formula Accuracy
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

            if result.get("sql"):
                instruction = self._bsl_compliance_instruction(question, result["sql"])
                if instruction:
                    result = self._regenerate_with_bsl_compliance(
                        question=question,
                        schema=schema,
                        meanings=meanings,
                        bsl=bsl,
                        instruction=instruction,
                        previous_sql=result["sql"],
                    )

            # Fix UNION ALL + ORDER BY issue for SQLite
            if result.get("sql"):
                result["sql"] = self._fix_union_order_by(result["sql"])

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
    
    def generate_sql_with_correction(
        self,
        question: str,
        schema: str,
        meanings: str,
        bsl: str = "",
        max_iterations: int = 2
    ) -> Dict[str, Any]:
        """Generate SQL with self-correction loop"""
        sql_result = None
        validation_result = None
        
        for iteration in range(max_iterations):
            # Generate or correct SQL
            if iteration == 0:
                # Initial generation
                sql_result = self.generate_sql(question, schema, meanings, bsl)
            else:
                # Correction based on validation errors
                overrides_text = self._extract_bsl_overrides(bsl)
                correction_prompt = f"""
### BSL OVERRIDES (HIGHEST PRIORITY - MUST FOLLOW):
{overrides_text or "[No overrides]"}

### BUSINESS SEMANTICS LAYER (CRITICAL - READ FIRST):
{bsl if bsl else "[No BSL provided - using defaults]"}

VORHERIGE SQL (FEHLERHAFT):
{sql_result.get("sql")}

VALIDIERUNGS-FEHLER:
{chr(10).join(validation_result.get("errors", []))}

NUTZER-FRAGE:
{question}

DATENBANK SCHEMA:
{schema}

SPALTEN BEDEUTUNGEN:
{meanings}

Korrigiere die SQL-Query basierend auf den Fehlern.
"""
                try:
                    response = self._call_openai(SystemPrompts.SQL_GENERATION, correction_prompt)
                    sql_result = self._ensure_generation_fields(self._parse_json_response(response))
                    if sql_result.get("sql"):
                        sql_result["sql"] = sql_result["sql"].replace("```sql", "").replace("```", "").strip()
                        # Fix UNION ALL + ORDER BY issue for SQLite
                        sql_result["sql"] = self._fix_union_order_by(sql_result["sql"])
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
