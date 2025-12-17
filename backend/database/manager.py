import sqlite3
import json
from typing import List, Dict, Any, Tuple, Optional
from functools import lru_cache

class DatabaseManager:
    """Verwaltet Datenbankzugriffe und Schema-Abfragen"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_schema_and_sample(self) -> str:
        """Holt Schema und Beispieldaten für LLM Context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_parts = []
        for (table_name,) in tables:
            # CREATE Statement
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            create_stmt = cursor.fetchone()[0]
            schema_parts.append(create_stmt)
            
            # Sample Row (wichtig für JSON Spalten)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                row_dict = dict(zip(columns, row))
                sample_str = json.dumps(row_dict, default=str, ensure_ascii=False)
                schema_parts.append(f"-- Beispielzeile für {table_name}:\n-- {sample_str}\n")
        
        conn.close()
        return "\n\n".join(schema_parts)

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
    
    def execute_query(
        self,
        sql: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        """Führt eine SQL-Query mit optionalem Limit/Offset aus und liefert den nächsten Offset."""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            if limit is None:
                cursor.execute(sql)
                rows = cursor.fetchall()
                next_offset = None
            else:
                paginated_sql = f"SELECT * FROM ({sql}) AS subquery LIMIT ? OFFSET ?"
                cursor.execute(paginated_sql, (limit + 1, offset))

                fetched_rows = cursor.fetchall()
                has_more = len(fetched_rows) > limit
                rows = fetched_rows[:limit]
                next_offset = offset + limit if has_more else None

            return [dict(row) for row in rows], next_offset
        finally:
            conn.close()
