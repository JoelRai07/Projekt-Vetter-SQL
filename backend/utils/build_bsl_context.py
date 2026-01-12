from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from utils.bsl_transformer import build_bsl_context


def _load_kb_entries(kb_path: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    with kb_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def _load_metric_lines(templates_path: Path) -> List[str]:
    if not templates_path.exists():
        return []
    with templates_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        entries = list(data.values())
    elif isinstance(data, list):
        entries = data
    else:
        entries = []

    metric_lines: List[str] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("metric") or item.get("knowledge")
        sql = item.get("sql") or item.get("sql_example")
        desc = item.get("description") or ""
        if not name or not sql:
            continue
        line = f"- {name}: {sql}"
        if desc:
            line += f" -- {desc}"
        metric_lines.append(line)
    return metric_lines


def build_bsl_file(
    db_name: str,
    data_dir: Path,
    output_path: Path,
    schema_path: Path | None = None,
) -> None:
    kb_path = data_dir / db_name / f"{db_name}_kb.jsonl"
    meanings_path = data_dir / db_name / f"{db_name}_column_meaning_base.json"
    templates_path = data_dir / db_name / f"{db_name}_metric_sql_templates.json"

    kb_entries = _load_kb_entries(kb_path)
    meanings_data = json.loads(meanings_path.read_text(encoding="utf-8"))
    metric_lines = _load_metric_lines(templates_path)

    bsl_kb, bsl_meanings = build_bsl_context(
        kb_entries=kb_entries,
        meanings_data=meanings_data,
        metric_lines=metric_lines,
    )

    schema_text = ""
    if schema_path and schema_path.exists():
        schema_text = schema_path.read_text(encoding="utf-8").strip()

    sections: List[str] = []
    if schema_text:
        sections.append("BSL DATABASE SCHEMA:")
        sections.append(schema_text)
        sections.append("")
    if bsl_kb:
        sections.append(bsl_kb)
        sections.append("")
    if bsl_meanings:
        sections.append(bsl_meanings)

    output_path.write_text("\n".join(sections).strip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a BSL context file from schema, KB, and column meanings."
    )
    parser.add_argument("db_name", help="Database name (e.g. credit)")
    parser.add_argument(
        "--data-dir",
        default="backend/mini-interact",
        help="Base directory containing DB folders",
    )
    parser.add_argument(
        "--schema-path",
        default=None,
        help="Optional schema text file to embed (e.g. credit_schema.txt)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: <db_dir>/<db>_bsl_context.txt)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    db_dir = data_dir / args.db_name
    output_path = (
        Path(args.output)
        if args.output
        else db_dir / f"{args.db_name}_bsl_context.txt"
    )
    schema_path = Path(args.schema_path) if args.schema_path else None

    build_bsl_file(args.db_name, data_dir, output_path, schema_path=schema_path)
    print(f"✅ BSL context file written to: {output_path}")


if __name__ == "__main__":
    main()
