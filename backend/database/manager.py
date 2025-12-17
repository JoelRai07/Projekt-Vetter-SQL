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
    
    def execute_query_with_paging(
        self, 
        sql: str, 
        page: int = 1, 
        page_size: int = 100
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Führt SQL Query aus mit Paging-Unterstützung.
        
        Returns:
            (results, paging_info)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Gesamtanzahl der Zeilen ermitteln
            count_sql = self._create_count_query(sql)
            cursor.execute(count_sql)
            total_rows = cursor.fetchone()[0]
            
            # 2. Paging-Parameter berechnen
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0
            offset = (page - 1) * page_size
            
            # 3. Haupt-Query mit LIMIT und OFFSET ausführen
            paged_sql = self._add_paging_to_sql(sql, page_size, offset)
            cursor.execute(paged_sql)
            rows = cursor.fetchall()
            
            # 4. Paging-Informationen
            paging_info = {
                "page": page,
                "page_size": page_size,
                "total_rows": total_rows,
                "total_pages": total_pages,
                "has_next_page": page < total_pages,
                "has_previous_page": page > 1,
                "rows_on_page": len(rows)
            }
            
            return [dict(row) for row in rows], paging_info
        finally:
            conn.close()
    
    def _create_count_query(self, sql: str) -> str:
        """Erstellt COUNT-Query aus SELECT-Query"""
        sql_upper = sql.upper()
        
        # Finde SELECT ... FROM Teil
        select_idx = sql_upper.find("SELECT")
        from_idx = sql_upper.find("FROM")
        
        if from_idx == -1:
            raise ValueError("Kein FROM in SQL gefunden")
        
        # Finde Ende der Query (vor ORDER BY, LIMIT, etc.)
        end_idx = len(sql)
        for keyword in ["ORDER BY", "LIMIT", "OFFSET", "GROUP BY", "HAVING"]:
            keyword_idx = sql_upper.find(keyword, from_idx)
            if keyword_idx != -1 and keyword_idx < end_idx:
                end_idx = keyword_idx
        
        original_query = sql[select_idx:end_idx].strip()
        
        # Bei DISTINCT oder GROUP BY: Subquery verwenden
        if "DISTINCT" in sql_upper or "GROUP BY" in sql_upper:
            return f"SELECT COUNT(*) FROM ({original_query}) AS count_query"
        else:
            # Einfacher Fall: Ersetze SELECT ... mit COUNT(*)
            return f"SELECT COUNT(*) {sql[from_idx:end_idx]}"
    
    def _add_paging_to_sql(self, sql: str, limit: int, offset: int) -> str:
        """Fügt LIMIT und OFFSET zur SQL-Query hinzu"""
        sql_upper = sql.upper()
        
        # Entferne vorhandene LIMIT/OFFSET
        limit_idx = sql_upper.rfind("LIMIT")
        if limit_idx != -1:
            limit_end = sql_upper.find(";", limit_idx)
            if limit_end == -1:
                limit_end = len(sql)
            else:
                limit_end += 1
            sql = sql[:limit_idx].rstrip() + sql[limit_end:]
        
        offset_idx = sql_upper.rfind("OFFSET")
        if offset_idx != -1:
            offset_end = sql_upper.find(";", offset_idx)
            if offset_end == -1:
                offset_end = len(sql)
            else:
                offset_end += 1
            sql = sql[:offset_idx].rstrip() + sql[offset_end:]
        
        # Füge neues LIMIT und OFFSET hinzu
        sql = sql.rstrip().rstrip(";")
        sql += f" LIMIT {limit} OFFSET {offset};"
        
        return sql