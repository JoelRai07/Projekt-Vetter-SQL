import re
from typing import Dict, List, Optional


def enforce_safety(sql: str) -> Optional[str]:
    """Basale Sicherheits-Checks vor der Ausführung."""
    if not sql or not isinstance(sql, str):
        return "Keine SQL-Query vorhanden."

    trimmed = sql.strip().lower()

    # Keine mehrfache Statements zulassen
    semicolons = [pos for pos, ch in enumerate(sql) if ch == ";"]
    if len(semicolons) > 1:
        return "Mehrere SQL-Statements erkannt; nur ein SELECT erlaubt."

    # Nur SELECT/CTE erlauben
    if not (trimmed.startswith("select") or trimmed.startswith("with")):
        return "Nur SELECT-Statements sind erlaubt."

    forbidden_keywords = ["insert", "update", "delete", "drop", "alter", "attach", "pragma", "replace", "truncate"]
    if any(re.search(rf"\b{kw}\b", trimmed) for kw in forbidden_keywords):
        return "Gefährliche SQL-Operation erkannt."

    return None


def enforce_known_tables(sql: str, table_columns: Dict[str, List[str]]) -> Optional[str]:
    """Stellt sicher, dass nur bekannte Tabellen referenziert werden."""
    table_names = set(table_columns.keys())
    found_tables = set()

    # Ermittele CTE-Namen, damit sie nicht fälschlicherweise als unbekannte Tabellen markiert werden
    cte_names = set()
    for match in re.finditer(r"\bwith\s+\"?([a-zA-Z_][\w]*)\"?\s+as\b", sql, flags=re.IGNORECASE):
        cte_names.add(match.group(1))
    for match in re.finditer(r",\s*\"?([a-zA-Z_][\w]*)\"?\s+as\b", sql, flags=re.IGNORECASE):
        cte_names.add(match.group(1))

    # Einfache Regex für FROM/JOIN
    for match in re.finditer(r"\bfrom\s+([\w\"\.]+)|\bjoin\s+([\w\"\.]+)", sql, flags=re.IGNORECASE):
        table = match.group(1) or match.group(2)
        if table:
            found_tables.add(table.replace('"', ''))

    unknown = [tbl for tbl in found_tables if tbl not in table_names and tbl not in cte_names]
    if unknown:
        return f"Unbekannte Tabellen im SQL: {', '.join(sorted(unknown))}"

    return None


def enforce_semantic_guardrails(question: str, sql: str) -> List[str]:
    """Einfache Heuristiken, die typische semantische Fehler abfangen."""
    if not question or not sql:
        return []

    q = question.lower()
    s = sql.lower()
    errors: List[str] = []

    aggregate_triggers = [
        " by ",
        " per ",
        " each ",
        " breakdown",
        " category",
        " segment",
        " cohort",
        " distribution",
        " grouped",
    ]
    if any(trigger in q for trigger in aggregate_triggers) and "group by" not in s:
        errors.append(
            "Aggregation erwartet (Frage verlangt Gruppierung/Kategorien), aber SQL enthält kein GROUP BY."
        )

    if "cohort" in q and "group by" not in s:
        errors.append(
            "Cohort-Frage erkannt, aber SQL enthält keine Aggregation/GROUP BY."
        )

    if "fsi" in q or "financial stress" in q or "financial stability" in q:
        if "fsi" not in s:
            errors.append(
                "FSI in der Frage erwähnt, aber SQL enthält keine FSI-Spalte/Berechnung."
            )

    if re.search(r"\bcs\b", q) or "core registry" in q:
        if "coreregistry" not in s:
            errors.append(
                "CS/Core-Registry-ID in der Frage erwähnt, aber SQL nutzt kein coreregistry."
            )

    if re.search(r"\bcu\b", q):
        if "clientref" not in s:
            errors.append(
                "CU/Customer-ID in der Frage erwähnt, aber SQL nutzt kein clientref."
            )

    return errors
