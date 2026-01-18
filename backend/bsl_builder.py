"""
Business Semantics Layer (BSL) Builder

Converts implicit knowledge from KB/schema into explicit, LLM-friendly rules.
This ensures Text2SQL systems understand business logic, not just schema.

Default usage (always Credit DB):
    python bsl_builder.py

Custom output:
    python bsl_builder.py --output bsl_credit.txt

Advanced usage (custom paths):
    python bsl_builder.py --kb <kb.jsonl> --meanings <meanings.json> --schema <schema.sql|schema.sqlite> --output <out.txt>
"""

import json
import argparse
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


# ---------------------------
# Path helpers (robust)
# ---------------------------

def find_repo_root(start: Path) -> Path:
    """
    Walk upwards until we find a folder containing 'mini-interact'.
    Falls back to start if not found.
    """
    start = start.resolve()
    for p in [start] + list(start.parents):
        if (p / "mini-interact").is_dir():
            return p
    return start


def default_credit_paths() -> Tuple[str, str, str]:
    """
    Always credit DB. Automatically picks a schema source:
    - prefer credit_schema.sql if exists
    - else prefer credit.sqlite / credit.db if exists
    - else fall back to credit_schema.sql (even if missing; builder will just show unknown types)
    """
    here = Path(__file__).resolve().parent
    root = find_repo_root(here)

    base = root / "mini-interact" / "credit"
    kb = base / "credit_kb.jsonl"
    meanings = base / "credit_column_meaning_base.json"

    # schema candidates (ordered)
    candidates = [
        base / "credit_schema.sql",
        base / "credit_schema.sqlite",
        base / "credit.sqlite",
        base / "credit.db",
    ]
    schema = next((c for c in candidates if c.exists()), candidates[0])

    return str(kb), str(meanings), str(schema)


# ---------------------------
# Builder
# ---------------------------

class BSLBuilder:
    """
    Builds a Business Semantics Layer from KB and Schema.

    IMPORTANT DESIGN:
    - Part A is the "true BSL": business terms, definitions, rules.
      It is technology-agnostic and should remain stable even if schema changes.
    - Part B is "Semantic-to-Schema Mapping": how concepts map to tables/columns.
    - Part C is "SQL Generation Policy" (annex): dialect / query-building patterns.
    """

    def __init__(self, kb_path: str, meanings_path: str, schema_path: str):
        self.kb_path = kb_path
        self.meanings_path = meanings_path
        self.schema_path = schema_path
        self.schema_types = self._load_schema_types(schema_path)

    # ---------------------------
    # Loaders
    # ---------------------------

    def load_kb(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        with open(self.kb_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(json.loads(line))
        return entries

    def load_meanings(self) -> Dict[str, Any]:
        with open(self.meanings_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_schema_types(self, schema_path: str) -> Dict[Tuple[str, str], str]:
        """
        Loads declared column types either from:
        - SQL schema file (CREATE TABLE ...)
        - SQLite database file (PRAGMA table_info)
        """
        p = Path(schema_path)
        if not p.exists():
            return {}

        ext = p.suffix.lower()
        if ext in {".sqlite", ".db"}:
            return self._load_schema_types_from_sqlite(p)
        else:
            return self._load_schema_types_from_sql(p)

    def _load_schema_types_from_sqlite(self, db_path: Path) -> Dict[Tuple[str, str], str]:
        types: Dict[Tuple[str, str], str] = {}
        try:
            con = sqlite3.connect(str(db_path))
            cur = con.cursor()

            # list tables
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]

            for t in tables:
                # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
                cur.execute(f"PRAGMA table_info('{t}')")
                for _, col, ctype, *_ in cur.fetchall():
                    if col:
                        types[(t, col)] = ctype or ""
            con.close()
        except Exception:
            # If schema parsing fails, just return empty -> "unknown" types in output
            return {}
        return types

    def _load_schema_types_from_sql(self, sql_path: Path) -> Dict[Tuple[str, str], str]:
        """
        Lightweight SQL parser for CREATE TABLE blocks.
        """
        types: Dict[Tuple[str, str], str] = {}
        sql = sql_path.read_text(encoding="utf-8", errors="ignore")

        create_table_re = re.compile(
            r'CREATE\s+TABLE\s+"?([A-Za-z0-9_]+)"?\s*\((.*?)\)\s*;',
            re.IGNORECASE | re.DOTALL,
        )

        col_re = re.compile(
            r'^\s*"?(?P<col>[A-Za-z0-9_]+)"?\s+(?P<type>[A-Za-z0-9_]+(?:\([^)]+\))?)',
            re.IGNORECASE,
        )

        for m in create_table_re.finditer(sql):
            table = m.group(1)
            body = m.group(2)
            for line in body.splitlines():
                line = line.strip().rstrip(",")
                if not line or line.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "CONSTRAINT")):
                    continue
                cm = col_re.match(line)
                if not cm:
                    continue
                col = cm.group("col")
                ctype = cm.group("type")
                types[(table, col)] = ctype
        return types

    # ---------------------------
    # Helpers
    # ---------------------------

    @staticmethod
    def _shorten(text: str, n: int = 220) -> str:
        text = (text or "").strip()
        if len(text) <= n:
            return text
        return text[: n - 3].rstrip() + "..."

    def _col_type(self, table: str, column: str) -> Optional[str]:
        return self.schema_types.get((table, column))

    # ---------------------------
    # PART A: True BSL (business)
    # ---------------------------

    def build_intro(self) -> List[str]:
        return [
            "# BUSINESS SEMANTICS LAYER (BSL)",
            "",
            "## Purpose",
            "This BSL defines **business meaning** (terms, metrics, segments, and interpretation rules) for the Credit domain.",
            "It is written to be **LLM-friendly** and to support consistent analytics across tools (Text2SQL, BI, reporting).",
            "",
            "## Scope",
            "- Business concepts (e.g., *customer*, *net worth*, *high engagement*, *investment focused*).",
            "- Business rules and thresholds used to interpret data.",
            "- Metric definitions (formulas) at the conceptual level.",
            "",
            "## Non-goals (out of scope for the BSL itself)",
            "- SQL dialect details (casting, placeholder syntax, JSON functions).",
            "- Query optimization, join order tuning, engine limitations.",
            "",
            "> Note: Implementation specifics appear in **Annex C: SQL Generation Policy** and are **not part of the BSL**.",
        ]

    def extract_glossary(self, kb_entries: List[Dict[str, Any]]) -> List[str]:
        glossary = [
            "## Glossary (Canonical Business Terms)",
            "",
            "- **Customer**: A person/entity represented by one record across the domain tables.",
            "- **Customer ID (business)**: The identifier used in outputs and reports (see Mapping section for source).",
            "- **Registry ID (technical)**: The internal identifier used to relate records across tables (see Mapping section).",
            "",
        ]

        calc = [m for m in kb_entries if m.get("type") == "calculation_knowledge"]
        if calc:
            glossary.append("### Metrics (Canonical Names)")
            for m in calc:
                name = m.get("knowledge", "").strip()
                desc = self._shorten(m.get("description", ""), 160)
                if name:
                    glossary.append(f"- **{name}**: {desc}")
            glossary.append("")

        domain = [m for m in kb_entries if m.get("type") == "domain_knowledge"]
        if domain:
            glossary.append("### Segments / Classifications")
            for m in domain:
                name = m.get("knowledge", "").strip()
                if name:
                    glossary.append(f"- **{name}**: Segment defined by business rules (see section below).")
            glossary.append("")

        return glossary

    def extract_business_logic_rules(self, kb_entries: List[Dict[str, Any]]) -> List[str]:
        rules: List[str] = [
            "## Business Rules",
            "",
            "### Customer Segmentation",
            "Segments are defined **by business conditions** on metrics and attributes. They must be interpreted consistently.",
            "",
        ]

        domain_rules = [m for m in kb_entries if m.get("type") == "domain_knowledge"]
        for rule in domain_rules:
            name = rule.get("knowledge", "").strip()
            definition = (rule.get("definition") or "").strip()
            if name and definition:
                rules.extend([f"#### {name}", definition, ""])

        value_rules = [m for m in kb_entries if m.get("type") == "value_illustration"]
        if value_rules:
            rules.append("### Value Interpretation Guidelines")
            for rule in value_rules:
                name = rule.get("knowledge", "").strip()
                definition = self._shorten(rule.get("definition", ""), 280)
                if name and definition:
                    rules.append(f"- **{name}**: {definition}")
            rules.append("")

        return rules

    def extract_metric_definitions(self, kb_entries: List[Dict[str, Any]]) -> List[str]:
        metric_section = [
            "## Metric Definitions (Conceptual)",
            "",
            "When a question references a metric name, interpret it using these definitions.",
            "Formulas are expressed conceptually; implementation details may vary by SQL dialect.",
            ""
        ]

        calc_metrics = [m for m in kb_entries if m.get("type") == "calculation_knowledge"]
        for metric in calc_metrics:
            name = (metric.get("knowledge") or "").strip()
            desc = (metric.get("description") or "").strip()
            formula = (metric.get("definition") or "").strip()
            if not name:
                continue
            metric_section.append(f"### {name}")
            if desc:
                metric_section.append(f"- **Meaning:** {desc}")
            if formula:
                metric_section.append(f"- **Definition / Formula:** {formula}")
            metric_section.append("")

        return metric_section

    # ---------------------------
    # PART B: Semantic-to-Schema Mapping
    # ---------------------------

    def extract_identity_mapping(self) -> List[str]:
        return [
            "# SEMANTIC-TO-SCHEMA MAPPING (NOT PART OF THE BSL)",
            "",
            "## Identifier Mapping (Critical)",
            "",
            "This domain uses **two identifiers for the same customer**:",
            "",
            "### Customer ID (business output identifier)",
            "- **Semantic meaning:** what business users mean by \"customer id\" in reports",
            "- **Source column:** `core_record.coreregistry`",
            "- **Format:** `CS` + digits (e.g., `CS206405`)",
            "",
            "### Client Reference (alternative identifier)",
            "- **Semantic meaning:** alternative client reference number",
            "- **Source column:** `core_record.clientref`",
            "- **Format:** `CU` + digits (e.g., `CU338528`)",
            "",
            "### Invariants (must always hold)",
            "- A single customer has **both** identifiers, but they are **not equal** and must never be compared for equality.",
            "- **CRITICAL: Business outputs MUST ALWAYS use Customer ID (CS format) from core_record.coreregistry as the customer_id.**",
            "- Use Client Reference (CU format) ONLY when the question explicitly asks for \"client reference\" or \"clientref\".",
            "- Data relationships across tables are expressed using the **Registry ID chain** (see relationship chain below).",
            ""
        ]

    def extract_relationship_chain(self) -> List[str]:
        return [
            "## Entity Relationship Chain (Conceptual)",
            "",
            "The data model forms a strict customer-centric chain:",
            "",
            "- **Core Record** → **Employment & Income** → **Expenses & Assets** → **Bank & Transactions** → **Credit & Compliance** → **Credit Accounts & History**",
            "",
            "### Why this matters",
            "- Many business questions combine metrics from multiple domain areas.",
            "- Correct answers require respecting the relationship chain; skipping intermediate entities can break meaning and integrity.",
            ""
        ]

    def extract_json_field_paths(self, meanings: Dict[str, Any]) -> List[str]:
        rules: List[str] = [
            "## Semi-Structured Fields (JSON stored in a column)",
            "",
            "Some columns contain JSON documents (often stored as TEXT in the schema).",
            "Interpret these fields using the paths below.",
            ""
        ]

        json_cols = {k: v for k, v in meanings.items()
                    if isinstance(v, dict) and "fields_meaning" in v}

        if not json_cols:
            rules.append("_No JSON-like columns detected from meanings._")
            rules.append("")
            return rules

        for key, value in json_cols.items():
            parts = key.split("|")
            if len(parts) != 3:
                continue
            _, table, column = parts
            col_type = self._col_type(table, column)
            storage_note = f"(declared type: `{col_type}`)" if col_type else "(declared type: unknown)"
            column_meaning = (value.get("column_meaning") or "").strip()

            rules.append(f"### {table}.{column} {storage_note}")
            if column_meaning:
                rules.append(column_meaning)

            fields = value.get("fields_meaning", {})
            rules.append("")
            rules.append("**Paths:**")
            for field, desc in fields.items():
                if isinstance(desc, dict):
                    rules.append(f"- `{field}` (object):")
                    for subfield, subdesc in desc.items():
                        rules.append(f"  - `{field}.{subfield}`: {subdesc}")
                else:
                    rules.append(f"- `{field}`: {desc}")
            rules.append("")
        return rules

    # ---------------------------
    # PART C: SQL Generation Policy (Annex)
    # ---------------------------

    def extract_policy_annex(self, kb_entries: List[Dict[str, Any]]) -> List[str]:
        rules = [
            "# ANNEX C: SQL GENERATION POLICY (IMPLEMENTATION NOTES)",
            "",
            "## Aggregation vs Detail Decision Rules",
            "",
            "### Aggregation questions (GROUP BY)",
            "Trigger words: 'by category', 'by segment', 'for each', 'breakdown', 'summary', 'cohorts', 'how many', 'count', 'average', 'total'.",
            "",
            "### Ranking/listing (ORDER BY + LIMIT)",
            "Trigger words: 'top N', 'highest', 'lowest', 'best', 'worst'.",
            "",
            "### Row-level detail (no aggregation)",
            "Trigger words: 'show all', 'list each', 'identify', 'find customers where'.",
            "",
            '### Policy Overrides (Credit DB)',
            '- "digital native" → treat as **Digital First Customer** segment.',
            '- "credit classification" → treat as **credit score categories** (credscore bands).',
            '- If a question says "few customers" without a threshold: default to `HAVING COUNT(*) >= 10` (policy choice).',
            '- "investment potential" label → use \'Target\' for customers with ALR > 0.3 AND mthincome > 5000, otherwise \'Standard\'.',
            '- Percentage metrics (e.g., pct_high_engagement) → always express as decimal ratio 0-1 (e.g., 0.1684), never multiply by 100.',
            ''
        ]

        calc = [m for m in kb_entries if m.get("type") == "calculation_knowledge"]
        if calc:
            rules.append("## Reminder: Frequently Used Metrics")
            for m in calc[:8]:
                rules.append(f"- {m.get('knowledge')}: {self._shorten(m.get('definition',''), 120)}")
            rules.append("")

        return rules

    # ---------------------------
    # Build document
    # ---------------------------

    def build_bsl(self, output_path: str):
        print("Building Business Semantics Layer (BSL)...")

        kb_entries = self.load_kb()
        meanings = self.load_meanings()

        part_a: List[str] = []
        part_a.extend(self.build_intro())
        part_a.append("")
        part_a.extend(self.extract_glossary(kb_entries))
        part_a.append("")
        part_a.extend(self.extract_business_logic_rules(kb_entries))
        part_a.append("")
        part_a.extend(self.extract_metric_definitions(kb_entries))

        part_b: List[str] = []
        part_b.extend(self.extract_identity_mapping())
        part_b.append("")
        part_b.extend(self.extract_relationship_chain())
        part_b.append("")
        part_b.extend(self.extract_json_field_paths(meanings))

        part_c: List[str] = []
        part_c.extend(self.extract_policy_annex(kb_entries))

        content: List[str] = []
        content.extend(part_a)
        content.extend(["", "---", ""])
        content.extend(part_b)
        content.extend(["", "---", ""])
        content.extend(part_c)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(content), encoding="utf-8")

        print(f"BSL saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build Business Semantics Layer (Credit DB only)")

    parser.add_argument("--kb", default=None, help="Path to KB JSONL file (optional)")
    parser.add_argument("--meanings", default=None, help="Path to meanings JSON file (optional)")
    parser.add_argument("--schema", default=None, help="Path to schema SQL/SQLite file (optional)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output BSL file path (default: mini-interact/credit/credit_bsl.txt)",
    )

    args = parser.parse_args()

    # defaults for Credit DB
    kb_path, meanings_path, schema_path = default_credit_paths()

    if args.kb:
        kb_path = args.kb
    if args.meanings:
        meanings_path = args.meanings
    if args.schema:
        schema_path = args.schema

    if args.output is None:
        # default output next to credit assets
        # (resolved relative to repo root, not cwd)
        here = Path(__file__).resolve().parent
        root = find_repo_root(here)
        args.output = str(root / "mini-interact" / "credit" / "credit_bsl.txt")

    builder = BSLBuilder(kb_path=kb_path, meanings_path=meanings_path, schema_path=schema_path)
    builder.build_bsl(args.output)


if __name__ == "__main__":
    main()
