import sqlite3
import re
from typing import Dict, Optional

class QueryOptimizer:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def analyze_query_plan(self, sql: str) -> Dict:
        """Analyze query execution plan"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get query plan
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            plan = cursor.fetchall()
            
            # Analyze plan
            analysis = {
                "uses_index": False,
                "full_table_scan": False,
                "suggestions": []
            }
            
            for row in plan:
                detail = row[3] if len(row) > 3 else ""
                if "USING INDEX" in detail.upper():
                    analysis["uses_index"] = True
                if "SCAN TABLE" in detail.upper() and "USING INDEX" not in detail.upper():
                    analysis["full_table_scan"] = True
                    table_match = re.search(r"SCAN TABLE (\w+)", detail, re.IGNORECASE)
                    if table_match:
                        table = table_match.group(1)
                        analysis["suggestions"].append(
                            f"Consider adding index on {table} for better performance"
                        )
            
            return analysis
        except Exception as e:
            print(f"⚠️  Query Plan Analysis Fehler: {str(e)}")
            return {
                "uses_index": False,
                "full_table_scan": False,
                "suggestions": []
            }
        finally:
            conn.close()
    
    def optimize_sql(self, sql: str) -> str:
        """Apply basic optimizations"""
        optimized = sql
        
        # Entferne vorhandene LIMIT/OFFSET für Optimierung
        # (wird später wieder hinzugefügt durch Paging)
        sql_upper = optimized.upper()
        
        # Add LIMIT if missing and query might return many rows
        # (nur wenn kein Paging verwendet wird)
        if "LIMIT" not in sql_upper and "COUNT" not in sql_upper:
            # Check if it's a simple SELECT without aggregation
            if re.search(r"SELECT\s+.*\s+FROM", optimized, re.IGNORECASE) and \
               not re.search(r"\b(GROUP BY|ORDER BY)\b", optimized, re.IGNORECASE):
                # LIMIT wird durch Paging hinzugefügt, also nicht hier
                pass
        
        return optimized

