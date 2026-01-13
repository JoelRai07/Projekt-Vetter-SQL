from typing import Tuple
import os
import json
from config import Config


def load_context_files(db_name: str = None, data_dir: str = None, include_kb: bool = True) -> Tuple[str, str, str]:
    """Lädt Knowledge Base, Column Meanings UND BSL für eine Datenbank"""
    
    # Defaults
    if db_name is None:
        db_name = Config.DEFAULT_DATABASE
    if data_dir is None:
        data_dir = Config.DATA_DIR
    
    kb_text = ""
    meanings_text = ""
    bsl_text = ""
    
    if include_kb:
        # 1. Knowledge Base laden
        kb_path = f"{data_dir}/{db_name}/{db_name}_kb.jsonl"
        try:
            if not os.path.exists(kb_path):
                raise FileNotFoundError(f"KB nicht gefunden: {kb_path}")
            
            with open(kb_path, 'r', encoding='utf-8') as f:
                entries = []
                for line in f:
                    item = json.loads(line)
                    entries.append(f"• {item['knowledge']}: {item['definition']}")
                kb_text = "\n".join(entries)
        except Exception as e:
            kb_text = f"[FEHLER beim Laden der KB: {str(e)}]"
    
        # 1b. Optional: Metric SQL Templates
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
    
                metric_lines = []
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
        
    # 2. Column Meanings laden
    meanings_path = f"{data_dir}/{db_name}/{db_name}_column_meaning_base.json"
    try:
        if not os.path.exists(meanings_path):
            raise FileNotFoundError(f"Column Meanings nicht gefunden: {meanings_path}")
        
        with open(meanings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            meanings_list = []
            
            for key, value in data.items():
                if isinstance(value, dict):
                    if "column_meaning" in value:
                        meanings_list.append(f"  {key}: {value['column_meaning']}")
                        if "fields_meaning" in value:
                            meanings_list.append(f"    └─ Felder:")
                            for field, field_desc in value["fields_meaning"].items():
                                if isinstance(field_desc, dict):
                                    meanings_list.append(f"       {field}:")
                                    for subfield, subdesc in field_desc.items():
                                        meanings_list.append(f"         • {subfield}: {subdesc}")
                                else:
                                    meanings_list.append(f"       • {field}: {field_desc}")
                    else:
                        meanings_list.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
                else:
                    meanings_list.append(f"  {key}: {value}")
            
            meanings_text = "\n".join(meanings_list)
    except Exception as e:
        meanings_text = f"[FEHLER beim Laden der Meanings: {str(e)}]"
    
    # 3. Business Semantics Layer laden
    bsl_path = f"{data_dir}/{db_name}/{db_name}_bsl.txt"
    try:
        if os.path.exists(bsl_path):
            with open(bsl_path, 'r', encoding='utf-8') as f:
                bsl_text = f.read()
        else:
            bsl_text = "[WARNUNG: BSL nicht gefunden]"
            print(f"⚠️  BSL nicht gefunden: {bsl_path}")
    except Exception as e:
        bsl_text = f"[FEHLER beim Laden der BSL: {str(e)}]"
        print(f"❌ BSL Fehler: {str(e)}")
    
    return kb_text, meanings_text, bsl_text
