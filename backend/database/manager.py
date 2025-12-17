import sqlite3
import json
from typing import List, Dict, Any, Tuple
from functools import lru_cache


class DatabaseManager:
    """Verwaltet Datenbankzugriffe und Schema-Abfragen"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_schema_and_sample(self) -> str:
        """Holt Schema und Beispieldaten für LLM Context"""
        blocks = self.get_schema_blocks()
        return "\n\n".join(block["text"] for block in blocks)

    @lru_cache(maxsize=1)
    def get_schema_blocks(self) -> List[Dict[str, str]]:
        """Liefert Schema-Abschnitte pro Tabelle inklusive Beispielzeile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        blocks: List[Dict[str, str]] = []
        for (table_name,) in tables:
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            create_stmt = cursor.fetchone()[0]

            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            sample_str = "{}"
            if row:
                row_dict = dict(zip(columns, row))
                sample_str = json.dumps(row_dict, default=str, ensure_ascii=False)

            text_block = f"{create_stmt}\n-- Beispielzeile für {table_name}:\n-- {sample_str}\n"
            blocks.append({"table": table_name, "text": text_block})

        conn.close()
        return blocks

    @lru_cache(maxsize=1)
    def get_table_columns(self) -> Dict[str, List[str]]:
        """Liefert ein Mapping aus Tabellenname -> Spaltenliste für Validierung."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        cursor.execute(tables_query)
        table_names = [row[0] for row in cursor.fetchall()]

        mapping: Dict[str, List[str]] = {}
        for table in table_names:
            cursor.execute(f"PRAGMA table_info('{table}')")
            mapping[table] = [row[1] for row in cursor.fetchall()]

        conn.close()
        return mapping

    def execute_query(self, sql: str, max_rows: int | None = None) -> Tuple[List[Dict[str, Any]], bool]:
        """Führt SQL Query aus, begrenzt optional die Zeilenzahl und kennzeichnet Kürzungen."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(sql)

            truncated = False
            if max_rows is None:
                rows = cursor.fetchall()
            else:
                # Hole maximal max_rows + 1, um zu erkennen, ob mehr Daten vorhanden sind
                fetched_rows = cursor.fetchmany(max_rows + 1)
                truncated = len(fetched_rows) > max_rows
                rows = fetched_rows[:max_rows]

            return [dict(row) for row in rows], truncated
        finally:
            conn.close()
