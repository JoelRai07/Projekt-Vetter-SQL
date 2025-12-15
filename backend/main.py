# main.py
import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# --- KONFIGURATION ---
# Stelle sicher, dass du die Variable in deiner Umgebung gesetzt hast
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
# Überprüfe, ob der Key vorhanden ist, bevor die Konfiguration erfolgt
if not GEMINI_API_KEY:
    print("FEHLER: GEMINI_API_KEY ist nicht in der .env-Datei oder Umgebung gesetzt.")
    # In einer echten App würde man hier abbrechen
    # Wir lassen es für den Moment, aber es wird später fehlschlagen
    
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="Text2SQL API mit Gemini")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class QueryRequest(BaseModel):
    question: str
    database: str = "credit"

class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    results: List[Dict[str, Any]]
    row_count: int
    error: Optional[str] = None

# --- DATABASE MANAGER ---
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_schema_and_sample(self) -> str:
        """Holt Schema und gibt Samples für JSON-Spalten, damit Gemini die Struktur versteht."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_parts = []
        for (table_name,) in tables:
            # Create Statement holen
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            create_stmt = cursor.fetchone()[0]
            schema_parts.append(create_stmt)
            
            # Sample Data holen (wichtig für JSON Spalten wie chaninvdatablock)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                row_dict = dict(zip(columns, row))
                # Kürze lange Strings für den Prompt, aber lass JSON intakt
                sample_str = json.dumps(row_dict, default=str)
                schema_parts.append(f"-- Beispielzeile für {table_name}: {sample_str}")

        conn.close()
        return "\n\n".join(schema_parts)
    
    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            raise e
        finally:
            conn.close()

# --- HELPER FUNCTIONS ---
def load_context_files(db_name: str):
    """Lädt KB und Column Meanings.
    
    ANGEPASST: Sucht Dateien in 'mini-interact/{db_name}/'
    """
    kb_text = ""
    meanings_text = ""
    
    # 1. Knowledge Base laden (KB)
    file_path_kb = f"mini-interact/{db_name}/{db_name}_kb.jsonl"
    print(f"DEBUG: Suche Knowledge Base: {file_path_kb}") # <--- DEBUG
    try:
        if not os.path.exists(file_path_kb):
             raise FileNotFoundError(f"Knowledge Base Datei nicht gefunden unter: {file_path_kb}")
             
        with open(file_path_kb, 'r', encoding='utf-8') as f:
            entries = []
            for line in f:
                item = json.loads(line)
                # Wir formatieren das schön für den LLM
                entries.append(f"- Begriff: {item['knowledge']}\n  Definition: {item['definition']}")
            kb_text = "\n".join(entries)
    except FileNotFoundError as e:
        kb_text = f"Fehler: {str(e)}"
    except Exception as e:
         kb_text = f"Fehler beim Lesen der KB: {str(e)}"


    # 2. Column Meanings laden
    file_path_meanings = f"mini-interact/{db_name}/{db_name}_column_meaning_base.json"
    print(f"DEBUG: Suche Spaltenbeschreibung: {file_path_meanings}") # <--- DEBUG
    try:
        if not os.path.exists(file_path_meanings):
             raise FileNotFoundError(f"Spaltenbeschreibung Datei nicht gefunden unter: {file_path_meanings}")
             
        with open(file_path_meanings, 'r', encoding='utf-8') as f:
            data = json.load(f)
            meanings_list = []
            for table, cols in data.items():
                for col, desc in cols.items():
                    # Falls es ein Dictionary ist (für JSON Details), als String formatieren
                    if isinstance(desc, dict):
                        desc = json.dumps(desc)
                    meanings_list.append(f"{table}.{col}: {desc}")
            meanings_text = "\n".join(meanings_list)
    except FileNotFoundError as e:
        meanings_text = f"Fehler: {str(e)}"
    except Exception as e:
        meanings_text = f"Fehler beim Lesen der Meanings: {str(e)}"
        
    return kb_text, meanings_text

# --- LLM GENERATION ---
def generate_sql_gemini(question: str, schema: str, kb: str, meanings: str) -> str:
    # System Instruction für Gemini
    system_instruction = """Du bist ein Experte für SQLite Text-to-SQL Generierung.
    Deine Aufgabe ist es, präzisen SQL-Code zu schreiben, der die Frage des Nutzers beantwortet.
    
    REGELN:
    1. Nutze NUR die Tabellen und Spalten aus dem gegebenen SCHEMA.
    2. Wenn in der Knowledge Base (KB) eine Formel definiert ist (z.B. 'Net Worth' oder 'Credit Health Score'), MUSST du diese Berechnungslogik im SQL umsetzen.
    3. Für JSON-Spalten (z.B. chaninvdatablock) nutze die SQLite Syntax `json_extract(spalte, '$.feld')`.
    4. Antworte NUR mit dem SQL-Code. Kein Markdown, keine Erklärungen. Beginne direkt mit SELECT.
    """

    prompt = f"""
    ### DATENBANK SCHEMA & BEISPIELDATEN:
    {schema}

    ### SPALTEN BEDEUTUNGEN:
    {meanings}

    ### DOMAIN WISSEN & BERECHNUNGEN (WICHTIG!):
    {kb}

    ### FRAGE:
    {question}

    ### SQL:
    """

    # HIER WIRD 'gemini-2.5-flash' VERWENDET, WIE GEWÜNSCHT.
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
    
    try:
        response = model.generate_content(prompt)
        sql = response.text.strip()
        # Entferne Markdown Formatierung falls vorhanden
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql
    except Exception as e:
        return f"-- Fehler bei der Generierung: {str(e)}"

# --- ENDPOINTS ---
@app.post("/query", response_model=QueryResponse)
async def query_database(request: QueryRequest):
    # Fangen wir den Fehler direkt im Endpoint ab, falls er vorher auftritt.
    try:
        # NEUER PFAD: mini-interact/credit/credit.sqlite
        db_path = f"mini-interact/{request.database}/{request.database}.sqlite"
        print(f"DEBUG: Suche Datenbank unter Pfad: {db_path}") # <--- DEBUG
        
        if not os.path.exists(db_path):
             raise FileNotFoundError(f"Datenbankdatei nicht gefunden unter: {db_path}")
             
        db_manager = DatabaseManager(db_path)
        
        # 2. Kontext laden
        schema = db_manager.get_schema_and_sample()
        kb_text, meanings_text = load_context_files(request.database)
        
        # Fehlerprüfung der Kontextdateien
        if kb_text.startswith("Fehler:") or meanings_text.startswith("Fehler:"):
            error_message = f"Kontext-Ladefehler: {kb_text if kb_text.startswith('Fehler:') else ''} {meanings_text if meanings_text.startswith('Fehler:') else ''}"
            return QueryResponse(question=request.question, generated_sql="", results=[], row_count=0, error=error_message.strip())

        # 3. SQL Generieren
        generated_sql = generate_sql_gemini(request.question, schema, kb_text, meanings_text)
        
        # 4. SQL Ausführen
        if generated_sql.startswith("-- Fehler") or generated_sql.startswith("Error"):
             # Hier kommt ein Fehler vom LLM (z.B. API Key Problem oder Generierungsproblem)
             return QueryResponse(question=request.question, generated_sql=generated_sql, results=[], row_count=0, error="LLM Generierungsfehler oder API-Problem.")

        results = db_manager.execute_query(generated_sql)
        
        return QueryResponse(
            question=request.question,
            generated_sql=generated_sql,
            results=results,
            row_count=len(results)
        )

    except FileNotFoundError as e:
         raise HTTPException(status_code=500, detail=f"Konfigurationsfehler: {str(e)}")
    except Exception as e:
        # SQLite Fehler oder andere interne Fehler
        sql_or_empty = generated_sql if 'generated_sql' in locals() else ""
        return QueryResponse(
            question=request.question,
            generated_sql=sql_or_empty,
            results=[],
            row_count=0,
            error=f"Interner Server- oder SQL-Fehler: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Nutze env variable für Port oder Default 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)