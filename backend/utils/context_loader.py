import os
import json
from typing import Tuple, List, Dict, Any


def load_context_files(db_name: str, data_dir: str = "mini-interact") -> Tuple[str, str]:
    """Lädt Knowledge Base und Column Meanings"""

    kb_text = ""
    meanings_text = ""

    # 1. Knowledge Base (KB)
    kb_path = f"{data_dir}/{db_name}/{db_name}_kb.jsonl"
    try:
        if not os.path.exists(kb_path):
            raise FileNotFoundError(f"KB nicht gefunden: {kb_path}")

        with open(kb_path, 'r', encoding='utf-8') as f:
            entries = []
            for line in f:
                item = json.loads(line)
                entries.append(
                    f"• {item['knowledge']}: {item['definition']}"
                )
            kb_text = "\n".join(entries)
    except Exception as e:
        kb_text = f"[FEHLER beim Laden der KB: {str(e)}]"

    # 2. Column Meanings
    meanings_path = f"{data_dir}/{db_name}/{db_name}_column_meaning_base.json"
    try:
        if not os.path.exists(meanings_path):
            raise FileNotFoundError(f"Column Meanings nicht gefunden: {meanings_path}")

        with open(meanings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
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

    return kb_text, meanings_text


def load_kb_entries(db_name: str, data_dir: str = "mini-interact") -> List[Dict[str, Any]]:
    """Lädt KB als strukturierte Einträge für den Vektorindex."""
    kb_path = f"{data_dir}/{db_name}/{db_name}_kb.jsonl"
    entries: List[Dict[str, Any]] = []
    if not os.path.exists(kb_path):
        return entries

    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                entries.append({
                    "text": f"{item['knowledge']}: {item['definition']}",
                    "label": item.get("knowledge", "kb")
                })
    except Exception:
        return []

    return entries


def load_column_meanings(db_name: str, data_dir: str = "mini-interact") -> List[Dict[str, Any]]:
    """Lädt Column Meanings als flache Texte für die Schema-Suche."""
    meanings_path = f"{data_dir}/{db_name}/{db_name}_column_meaning_base.json"
    entries: List[Dict[str, Any]] = []
    if not os.path.exists(meanings_path):
        return entries

    try:
        with open(meanings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key, value in data.items():
                if isinstance(value, dict) and "column_meaning" in value:
                    entries.append({
                        "key": key,
                        "text": f"{key}: {value['column_meaning']}",
                    })
                    if "fields_meaning" in value:
                        for field, field_desc in value["fields_meaning"].items():
                            if isinstance(field_desc, dict):
                                for subfield, subdesc in field_desc.items():
                                    entries.append({
                                        "key": f"{key}.{field}.{subfield}",
                                        "text": f"{key}.{field}.{subfield}: {subdesc}",
                                    })
                            else:
                                entries.append({
                                    "key": f"{key}.{field}",
                                    "text": f"{key}.{field}: {field_desc}",
                                })
                else:
                    entries.append({
                        "key": key,
                        "text": f"{key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value}",
                    })
    except Exception:
        return []

    return entries
