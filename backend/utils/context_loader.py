import os
import json
from typing import Any, Dict, List, Tuple

from utils.bsl_transformer import build_bsl_context

def load_context_files(db_name: str, data_dir: str = "mini-interact") -> Tuple[str, str]:
    """Lädt Knowledge Base und Column Meanings"""
    
    kb_text = ""
    meanings_text = ""
    kb_entries: List[Dict[str, Any]] = []
    meanings_data: Dict[str, Any] = {}
    metric_lines: List[str] = []
    
    # 1. Knowledge Base (KB)
    kb_path = f"{data_dir}/{db_name}/{db_name}_kb.jsonl"
    try:
        if not os.path.exists(kb_path):
            raise FileNotFoundError(f"KB nicht gefunden: {kb_path}")
        
        with open(kb_path, 'r', encoding='utf-8') as f:
            entries = []
            for line in f:
                item = json.loads(line)
                kb_entries.append(item)
                entries.append(
                    f"• {item['knowledge']}: {item['definition']}"
                )
            kb_text = "\n".join(entries)
    except Exception as e:
        kb_text = f"[FEHLER beim Laden der KB: {str(e)}]"

    # 1b. Optional: Metric SQL Templates (deterministische SQL-Snippets)
    metric_templates_path = f"{data_dir}/{db_name}/{db_name}_metric_sql_templates.json"
    try:
        if os.path.exists(metric_templates_path):
            with open(metric_templates_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                entries = list(data.values())
            elif isinstance(data, list):
                entries = data
            else:
                entries = []

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

            if metric_lines:
                kb_text += "\n\nMETRIC SQL TEMPLATES:\n" + "\n".join(metric_lines)
    except Exception as e:
        kb_text += f"\n\n[FEHLER beim Laden der Metric SQL Templates: {str(e)}]"
    
    # 2. Column Meanings
    meanings_path = f"{data_dir}/{db_name}/{db_name}_column_meaning_base.json"
    try:
        if not os.path.exists(meanings_path):
            raise FileNotFoundError(f"Column Meanings nicht gefunden: {meanings_path}")
        
        with open(meanings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            meanings_data = data
            meanings_list = []
            
            # Format: {"db|table|column": "description" oder nested dict}
            for key, value in data.items():
                if isinstance(value, dict):
                    # Für JSONB Spalten (propfinancialdata, chaninvdatablock)
                    if "column_meaning" in value:
                        meanings_list.append(f"  {key}: {value['column_meaning']}")
                        if "fields_meaning" in value:
                            meanings_list.append(f"    └─ Felder:")
                            for field, field_desc in value["fields_meaning"].items():
                                if isinstance(field_desc, dict):
                                    # Nested fields (z.B. mortgagebits)
                                    meanings_list.append(f"       {field}:")
                                    for subfield, subdesc in field_desc.items():
                                        meanings_list.append(f"         • {subfield}: {subdesc}")
                                else:
                                    meanings_list.append(f"       • {field}: {field_desc}")
                    else:
                        # Falls es ein unerwartetes Dict-Format ist
                        meanings_list.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
                else:
                    # Standard: String-Beschreibung
                    meanings_list.append(f"  {key}: {value}")
            
            meanings_text = "\n".join(meanings_list)
    except Exception as e:
        meanings_text = f"[FEHLER beim Laden der Meanings: {str(e)}]"

    if kb_entries and meanings_data:
        try:
            bsl_kb, bsl_meanings = build_bsl_context(
                kb_entries=kb_entries,
                meanings_data=meanings_data,
                metric_lines=metric_lines,
            )
            if bsl_kb:
                kb_text = bsl_kb
            if bsl_meanings:
                meanings_text = bsl_meanings
        except Exception as e:
            kb_text += f"\n\n[FEHLER bei BSL-Formatierung: {str(e)}]"

    return kb_text, meanings_text
