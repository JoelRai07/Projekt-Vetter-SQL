from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _format_kb_entries(entries: Iterable[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for item in entries:
        name = item.get("knowledge") or item.get("name") or item.get("metric")
        definition = item.get("definition")
        description = item.get("description")
        entry_type = item.get("type")
        if not name or not definition:
            continue
        line = f"- {name}: {definition}"
        if description:
            line += f" | {description}"
        if entry_type:
            line += f" ({entry_type})"
        lines.append(line)
    return lines


def _format_meanings(data: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for key, value in data.items():
        if isinstance(value, dict) and "column_meaning" in value:
            lines.append(f"- {key}: {value['column_meaning']}")
            fields = value.get("fields_meaning", {})
            for field, field_desc in fields.items():
                if isinstance(field_desc, dict):
                    lines.append(f"  - {key}.{field}:")
                    for subfield, subdesc in field_desc.items():
                        lines.append(f"    - {key}.{field}.{subfield}: {subdesc}")
                else:
                    lines.append(f"  - {key}.{field}: {field_desc}")
        else:
            lines.append(f"- {key}: {value}")
    return lines


def _split_primary_keys(meanings_lines: Iterable[str]) -> Tuple[List[str], List[str]]:
    primary_keys: List[str] = []
    other_lines: List[str] = []
    for line in meanings_lines:
        if "primary key" in line.lower():
            primary_keys.append(line)
        else:
            other_lines.append(line)
    return primary_keys, other_lines


def build_bsl_context(
    kb_entries: Iterable[Dict[str, Any]],
    meanings_data: Dict[str, Any],
    metric_lines: Iterable[str] | None = None,
) -> Tuple[str, str]:
    kb_lines = _format_kb_entries(kb_entries)
    meanings_lines = _format_meanings(meanings_data)
    primary_keys, other_meanings = _split_primary_keys(meanings_lines)

    kb_sections: List[str] = []
    if kb_lines:
        kb_sections.append("BSL KNOWLEDGE BASE:")
        kb_sections.extend(kb_lines)

    if metric_lines:
        kb_sections.append("")
        kb_sections.append("BSL METRIC SQL TEMPLATES:")
        kb_sections.extend(metric_lines)

    kb_text = "\n".join(kb_sections).strip()
    meanings_sections: List[str] = []
    if primary_keys:
        meanings_sections.append("BSL PRIMARY KEYS:")
        meanings_sections.extend(primary_keys)
        meanings_sections.append("")
    meanings_sections.append("BSL COLUMN MEANINGS:")
    meanings_sections.extend(other_meanings or [])
    meanings_text = "\n".join(meanings_sections).strip()

    return kb_text, meanings_text
