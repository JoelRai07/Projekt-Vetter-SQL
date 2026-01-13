# Funktionen-Übersicht - Text2SQL System

## 📋 Inhaltsverzeichnis
1. [Frontend-Funktionen](#frontend-funktionen-reactjs)
2. [Backend-API-Endpunkte](#backend-api-endpunkte)
3. [LLM-Generator-Funktionen](#llm-generator-funktionen)
4. [Database-Manager-Funktionen](#database-manager-funktionen)
5. [Utility-Funktionen](#utility-funktionen)
6. [Schema-Retriever-Funktionen](#schema-retriever-funktionen-rag)

---

## Frontend-Funktionen (React.js)

### `function App()`
**Datei**: `frontend/src/App.jsx`

**Zweck**: Haupt-React-Komponente für die Nutzer-Oberfläche

**Kernfunktionen**:
- State Management (question, messages, theme, etc.)
- HTTP Kommunikation mit Backend
- Dark/Light Theme Toggle
- Paging-Steuerung
- Fehlerbehandlung

### `askQuestion(question: string, page?: number, pageSize?: number, queryId?: string)`

**Parameter**:
- `question`: Nutzer-Frage in natürlicher Sprache
- `page`: Seite der Ergebnisse (default: 1)
- `pageSize`: Zeilen pro Seite (default: 100)
- `queryId`: UUID für Paging-Determinismus

**Return**: `Promise<void>` - Aktualisiert UI mit Ergebnissen

**Ablauf**:
```
1. POST /query mit QueryRequest
2. Warte auf Response
3. Speichere message in State
4. Rendere Ergebnisse
5. Cleanup & Error Handling
```

**Fehlerbehandlung**:
- Network Error → "Verbindung fehlgeschlagen"
- Server Error (5xx) → "Interner Server Fehler"
- Client Error (4xx) → "Ungültige Anfrage"
- Parsing Error → "Fehler beim Verarbeiten der Antwort"

### `handleSubmit()`

**Zweck**: Verarbeitet Form-Submission

**Schritte**:
1. Prüfe: question nicht leer
2. Setze isLoading = true
3. Rufe askQuestion() auf
4. Setze isLoading = false
5. Scrolle zu Ergebnissen

### `handlePageChange(messageId: string, newPage: number)`

**Zweck**: Navigiere zu nächster/vorheriger Seite

**Schritte**:
1. Finde message im State (nach messageId)
2. Extrahiere query_id (für Determinismus)
3. Rufe askQuestion() mit newPage + queryId auf
4. Aktualisiere message.results + paging_info

### `toggleSQL(messageId: string)`

**Zweck**: Ein-/Ausblenden der generierten SQL

**Funktion**: Toggle message.showSQL boolean

### `toggleTheme()`

**Zweck**: Wechsel zwischen Dark/Light Mode

**Implementation**:
```
theme = theme === "dark" ? "light" : "dark"
Speichere in localStorage (persist über Page Reload)
```

### `copyToClipboard(text: string, id: string)`

**Zweck**: Kopiere SQL in Zwischenablage

**Funktion**:
1. Kopiere text zu Clipboard
2. Zeige CheckIcon für 2 Sekunden
3. Zurück zu CopyIcon

---

## Backend-API-Endpunkte

### `GET /`

**Zweck**: Health-Check & API-Info

**Response**:
```json
{
  "message": "Text2SQL API läuft",
  "version": "2.1.0",
  "features": ["Ambiguity Detection", "SQL Validation", "Modular Structure"]
}
```

### `POST /query`

**Datei**: `backend/main.py` - `query_database(request: QueryRequest)`

**Request Schema** (`QueryRequest`):
```json
{
  "question": "Nutzer-Frage",
  "database": "credit",
  "page": 1,
  "page_size": 100,
  "use_react": true,
  "query_id": null
}
```

**Response Schema** (`QueryResponse`):
```json
{
  "question": "Nutzer-Frage",
  "generated_sql": "SELECT ...",
  "results": [...],
  "row_count": 10,
  "page": 1,
  "total_pages": 5,
  "total_rows": 450,
  "has_next_page": true,
  "has_previous_page": false,
  "ambiguity_check": {...},
  "validation": {...},
  "summary": "...",
  "explanation": "...",
  "query_id": "uuid...",
  "error": null
}
```

**6-Stufen Pipeline**:

1. **Phase 1: Context Loading**
   - Lädt Schema (mit Caching)
   - Lädt KB (mit Caching)
   - Lädt Meanings (mit Caching)

2. **Phase 2: Ambiguity Detection** (Parallel)
   - Prüft ob Frage mehrdeutig ist
   - Falls ja: STOP & Rückfragen
   - Falls nein: Weiter

3. **Phase 3: SQL Generation** (Parallel)
   - Nutzt ReAct + Retrieval oder Standard-Modus
   - Gibt SQL + Confidence Score zurück

4. **Phase 4: SQL Validation**
   - SQL Guard Prüfung
   - LLM Validation
   - Optional: Self-Correction bei Errors

5. **Phase 5: SQL Execution**
   - Führt SQL mit Paging aus
   - Berechnet Total Count
   - Bestimmt Navigation-Flags

6. **Phase 6: Result Summarization**
   - LLM erstellt Zusammenfassung
   - Fallback bei Fehler

---

## LLM-Generator-Funktionen

### `class OpenAIGenerator`

**Datei**: `backend/llm/generator.py`

**Konstruktor**: `__init__(api_key: str, model_name: str)`
- Initialisiert OpenAI Client
- Setzt model_name (z.B. "gpt-4o-mini")

### `_call_openai(system_instruction: str, prompt: str) -> str`

**Zweck**: Generischer OpenAI ChatCompletion Call

**Parameter**:
- `system_instruction`: System-Prompt (Rolle des LLM)
- `prompt`: User-Prompt (konkrete Aufgabe)

**Return**: LLM Response als String

**Error Handling**:
- `RateLimitError`: "Rate Limit reached, retry later"
- `AuthenticationError`: "API Key invalid"
- `APIStatusError`: Log detailliert & Raise

**Config**:
- model: `self.model_name`
- temperature: 0.2 (deterministisch)
- messages: [system, user]

### `_parse_json_response(response: str) -> Dict[str, Any]`

**Zweck**: Parse JSON aus LLM Response (robust gegen Markdown etc.)

**Ablauf**:
1. Entferne Markdown: ```json → ""
2. Finde erste `{`
3. Zähle Braces bis zum Ende
4. Extrahiere JSON String
5. Parse mit json.loads()
6. Fallback: `json.loads(..., strict=False)` wenn strict fehlschlägt

**Return**: Parsed JSON Dict

**Error Handling**: Wirft JSONDecodeError falls gar nicht zu parsen

### `_ensure_generation_fields(result: Dict[str, Any]) -> Dict[str, Any]`

**Zweck**: Validiere/normalisiere SQL-Generierung Response

**Garantiert diese Felder**:
- `thought_process`: "" (default wenn fehlend)
- `explanation`: "" (default wenn fehlend)
- `confidence`: 0.0-1.0 (float)
- `sql`: None oder SQL String

**Return**: Normalisierter Dict

### `check_ambiguity(question: str, schema: str, kb: str, meanings: str) -> Dict[str, Any]`

**Zweck**: Prüfe ob Nutzer-Frage mehrdeutig ist

**Prompt**: `SystemPrompts.AMBIGUITY_DETECTION`

**Return**:
```json
{
  "is_ambiguous": boolean,
  "reason": "Erklärung warum (nicht) mehrdeutig",
  "questions": ["Klärungsfrage 1", "Klärungsfrage 2"]
}
```

**Error Handling**: 
- Falls Fehler: `{"is_ambiguous": false, "reason": "Error: ...", "questions": []}`

### `generate_sql(question: str, schema: str, kb: str, meanings: str) -> Dict[str, Any]`

**Zweck**: Generiere SQL-Query aus Nutzer-Frage (Standard-Methode)

**Prompt**: `SystemPrompts.SQL_GENERATION`

**Return**:
```json
{
  "thought_process": "LLM's Überlegung",
  "sql": "SELECT ...",
  "explanation": "Was macht die Query",
  "confidence": 0.85
}
```

**Error Handling**: 
- JSON Parse Error: Retry mit strict=False
- API Error: Propagiere mit Exception

### `validate_sql(sql: str, schema: str) -> Dict[str, Any]`

**Zweck**: Validiere generierte SQL-Query

**Prompt**: `SystemPrompts.SQL_VALIDATION`

**Return**:
```json
{
  "is_valid": boolean,
  "errors": ["Error 1", "Error 2"],
  "severity": "low|medium|high",
  "suggestions": ["Suggestion 1"]
}
```

**Error Handling**: 
- Falls LLM-Call fehlschlägt: `{"is_valid": true, "errors": [], "severity": "low", "suggestions": []}`
- Non-blocking (System fährt fort auch wenn Validation fehlschlägt)

### `summarize_results(question: str, generated_sql: str, results: Any, row_count: int, notice: Optional[str] = None) -> str`

**Zweck**: Erstelle natürlichsprachliche Zusammenfassung der Ergebnisse

**Input**:
- `question`: Original-Frage des Nutzers
- `generated_sql`: Die ausgeführte SQL
- `results`: First 3 rows als List
- `row_count`: Total Zeilen
- `notice`: Optional (z.B. Paging-Info)

**Return**: Natürlichsprachliche Zusammenfassung (String)

**Fallback**: Falls Fehler: "Hier sind die Ergebnisse: ..."

### `generate_sql_with_react_retrieval(question: str, db_path: str, database_name: str, max_iterations: int = 3) -> Dict[str, Any]`

**Zweck**: Generiere SQL mit ReAct + Vector Retrieval (Iterativ)

**ReAct Loop** (bis max_iterations):

**Iteration 1-N**:
1. **THINK**: LLM analysiert Frage → "Was brauch ich?"
2. **ACT**: Generiere Search Queries
3. **OBSERVE**: ChromaDB Retrieval für Schema/KB/Meanings
4. **REASON**: Hat LLM genug Info? JA/NEIN?
5. Falls JA: Break aus Loop
6. Falls NEIN: Weiter zu nächster Iteration

**Nach Loop**:
- Sammle alle retrieved Chunks
- Generiere SQL mit NUR relevanten Infos
- Return: `{sql, explanation, confidence, thought_process}`

**Return**:
```json
{
  "thought_process": "...",
  "sql": "SELECT ...",
  "explanation": "...",
  "confidence": 0.88,
  "retrieval_info": {
    "iterations": 2,
    "schema_chunks": 16,
    "kb_entries": 18,
    "meanings": 18
  }
}
```

### `generate_sql_with_correction(question: str, schema: str, kb: str, meanings: str, max_iterations: int = 2) -> Dict[str, Any]`

**Zweck**: Generiere SQL mit Self-Correction bei Validation Fehlern

**Ablauf** (bis max_iterations):

1. Generiere SQL
2. Validiere SQL
3. Falls Fehler & Iteration < max_iterations:
   - Gib Validation-Feedback zu LLM
   - Fordere Korrektur an
   - Retry Validierung
4. Gib bestes Ergebnis zurück

**Return**: Korrigierte SQL oder Original falls keine Korrektur möglich

---

## Database-Manager-Funktionen

### `class DatabaseManager`

**Datei**: `backend/database/manager.py`

**Konstruktor**: `__init__(db_path: str)`
- Speichert db_path
- Initialisiert SQLite Connection (lazy)

### `get_schema_and_sample() -> str`

**Zweck**: Hol Schema + Beispieldaten für LLM-Kontext

**Return**: Formatted String mit:
```
CREATE TABLE core_record (
  coreregistry TEXT NOT NULL,
  clientref TEXT,
  ...
);
First 3 rows:
coreregistry    clientref    ...
CS206405        CU338528     ...
...
```

**Wichtig**: Zeigt Beispielzeilen (wichtig für JSON-Spalten)

**Caching**: `@lru_cache(maxsize=1)` - wird einmal pro Instanz gecacht

### `get_table_columns() -> Dict[str, List[str]]`

**Zweck**: Mapping Tabelle → Spalten (für Validierung)

**Return**:
```python
{
  "core_record": ["coreregistry", "clientref", ...],
  "employment_and_income": ["emplcoreref", "debincratio", ...],
  ...
}
```

**Caching**: `@lru_cache(maxsize=1)`

### `execute_query(sql: str, max_rows: int = None) -> Tuple[List[Dict], bool]`

**Zweck**: Führe SQL aus und hol Ergebnisse

**Parameter**:
- `sql`: SQL Query String
- `max_rows`: Max Zeilen zum Fetchen (optional)

**Return**:
```python
(
  [{"col1": val1, "col2": val2}, ...],  # Results als Dicts
  truncated_flag  # bool: wurden mehr Zeilen gecappt?
)
```

**Error Handling**: Wirft sqlite3.OperationalError bei SQL-Fehler

### `execute_query_with_paging(sql: str, page: int = 1, page_size: int = 100) -> Tuple[List[Dict], Dict]`

**Zweck**: Führe SQL mit Paging aus

**Ablauf**:

1. **Count Query**: `SELECT COUNT(*) FROM ({sql})` → total_rows
2. **Berechne Paging**:
   - `offset = (page - 1) * page_size`
   - `limit = page_size`
   - `total_pages = ceil(total_rows / page_size)`
3. **Paginated Query**: `{sql} LIMIT {limit} OFFSET {offset}`
4. **Fetch Results**: als List[Dict]
5. **Berechne Flags**: has_next_page, has_previous_page

**Return**:
```python
(
  results,  # List[Dict]
  {
    "page": 1,
    "page_size": 100,
    "total_rows": 1247,
    "total_pages": 13,
    "has_next_page": True,
    "has_previous_page": False,
    "rows_on_page": 100
  }
)
```

### `normalize_sql_for_paging(sql: str) -> str`

**Zweck**: Entferne existierende LIMIT/OFFSET aus SQL

**Grund**: Determinismus - jeder Paging-Call verwendet gleiche Base-SQL

**Implementation**: Regex um LIMIT/OFFSET zu entfernen

---

## Utility-Funktionen

### Cache-Funktionen

**Datei**: `backend/utils/cache.py`

### `get_cached_schema(db_path: str) -> str`

**Caching**: LRU Cache (maxsize=32, never expires)

**Lazily loads**: Schema beim ersten Call

### `get_cached_kb(db_name: str, data_dir: str) -> str`

**Caching**: TTL Cache (maxsize=32, ttl=3600 Sekunden = 1 Stunde)

**Lazily loads**: KB beim ersten Call

### `get_cached_meanings(db_name: str, data_dir: str) -> str`

**Caching**: TTL Cache (maxsize=32, ttl=3600 Sekunden)

**Lazily loads**: Meanings beim ersten Call

### `get_cached_query_result(question: str, database: str) -> Dict | None`

**Caching**: TTL Cache (maxsize=100, ttl=300 Sekunden = 5 Minuten)

**Key**: `md5(database + question)` Hash

### `cache_query_result(question: str, database: str, result: Dict)`

**Speichert**: Query-Ergebnis für 5 Minuten

### `create_query_session(database: str, sql: str, question: str) -> str`

**Return**: UUID query_id

**Speichert**: Session mit SQL (für deterministisches Paging)

### `get_query_session(query_id: str) -> Dict | None`

**Abrufen**: Session mit Database, SQL, Question

---

### SQL Guard Funktionen

**Datei**: `backend/utils/sql_guard.py`

### `enforce_safety(sql: str) -> Optional[str]`

**Zweck**: Basale Sicherheits-Checks

**Prüfung 1**: Nur 1 Statement
```python
if sql.count(';') > 1:
    return "Mehrere SQL-Statements erkannt"
```

**Prüfung 2**: Nur SELECT/WITH
```python
if not (sql.lower().startswith("select") or sql.lower().startswith("with")):
    return "Nur SELECT erlaubt"
```

**Prüfung 3**: Keine gefährlichen Keywords
```python
forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", ...]
if any(kw in sql.upper() for kw in forbidden):
    return "Gefährliche Operation"
```

**Return**: Error Message (string) oder None (=OK)

### `enforce_known_tables(sql: str, table_columns: Dict[str, List[str]]) -> Optional[str]`

**Zweck**: Nur bekannte Tabellen erlauben

**Ablauf**:
1. Extrahiere CTE-Namen aus `WITH ... AS`
2. Extrahiere Tabellennamen aus `FROM` / `JOIN` (Regex)
3. Prüfe: Alle Tabellen in `table_columns` oder in CTEs?
4. Wenn unbekannte Tabellen: Return Error

**Return**: Error Message oder None (=OK)

---

### Context Loader Funktionen

**Datei**: `backend/utils/context_loader.py`

### `load_context_files(db_name: str, data_dir: str = "mini-interact") -> Tuple[str, str]`

**Zweck**: Lade Knowledge Base und Column Meanings aus Dateien

**Laden**:
1. **KB**: `{data_dir}/{db_name}/{db_name}_kb.jsonl`
   - Formatiere als: "• Knowledge: Definition"
   - Join mit Newlines
   
2. **Meanings**: `{data_dir}/{db_name}/{db_name}_column_meaning_base.json`
   - Formatiere als: "  {db|table|column}: description"
   - Join mit Newlines

**Return**: `(kb_text, meanings_text)` oder mit `[FEHLER ...]` bei I/O Fehler

**Error Handling**: Graceful - gibt Error-String zurück statt Exception

---

### Query Optimizer

**Datei**: `backend/utils/query_optimizer.py`

### `class QueryOptimizer`

### `analyze_query_plan(sql: str) -> Dict`

**Zweck**: Analysiere Query Execution Plan

**Ablauf**:
1. `EXPLAIN QUERY PLAN {sql}`
2. Parse Plan Rows
3. Prüfe: Nutzt Index? Full Table Scan?
4. Gib Suggestions

**Return**:
```python
{
  "uses_index": boolean,
  "full_table_scan": boolean,
  "suggestions": ["Consider adding index on..."]
}
```

**Error Handling**: Wirft Exception nicht, gibt Default zurück

---

## Schema-Retriever-Funktionen (RAG)

### `class SchemaRetriever`

**Datei**: `backend/rag/schema_retriever.py`

**Konstruktor**: `__init__(db_path: str, persist_dir: str = "./vector_store/schema")`

- Initialisiert OpenAI Embeddings
- Initialisiert 3 ChromaDB Vector Stores:
  - schema_store: Schema Chunks
  - kb_store: Knowledge Base Einträge
  - meanings_store: Column Meanings

### `index_kb(kb_text: str)`

**Zweck**: Indexiere Knowledge Base in Vector Store

**Ablauf**:
1. Prüfe ob KB schon indexiert ist (via Hash)
2. Wenn nicht: Split KB in einzelne Zeilen
3. Für jede Zeile: Generiere Embedding
4. Speichere in ChromaDB

**Caching**: Nutzt MD5 Hash um erneute Indexierung zu vermeiden

### `index_meanings(meanings_text: str)`

**Zweck**: Indexiere Column Meanings in Vector Store

**Ablauf**: Ähnlich wie `index_kb()`

### `retrieve_relevant_schema(question: str, top_k: int = 5) -> Optional[str]`

**Zweck**: Semantische Suche nach relevanten Schema-Chunks

**Ablauf**:
1. Konvertiere question zu Embedding (OpenAI)
2. Suche ähnliche Vektoren in schema_store (Cosine Similarity)
3. Gib Top-K Chunks zurück

**Return**: Konkatenierte Schema-Chunks oder None

### `retrieve_relevant_kb(question: str, top_k: int = 5) -> str`

**Zweck**: Semantische Suche nach relevanten KB-Einträgen

**Return**: Konkatenierte KB-Einträge

### `retrieve_relevant_meanings(question: str, top_k: int = 10) -> str`

**Zweck**: Semantische Suche nach relevanten Column Meanings

**Return**: Konkatenierte Meanings

---

## Zusammenfassung der Funktions-Abhängigkeiten

```
Frontend (React)
    ↓
    askQuestion()
    ↓
    POST /query → query_database()
    ↓
    ├─ Phase 1: get_cached_schema() + get_cached_kb() + get_cached_meanings()
    ├─ Phase 2: check_ambiguity() (Parallel)
    ├─ Phase 3: generate_sql_with_react_retrieval() (Parallel)
    │           ├─ SchemaRetriever.index_kb()
    │           ├─ SchemaRetriever.retrieve_relevant_schema()
    │           ├─ SchemaRetriever.retrieve_relevant_kb()
    │           └─ SchemaRetriever.retrieve_relevant_meanings()
    ├─ Phase 4: validate_sql()
    ├─ Phase 5: execute_query_with_paging()
    │           ├─ normalize_sql_for_paging()
    │           ├─ count_query()
    │           └─ paginated_query()
    ├─ Phase 6: summarize_results()
    └─ Return QueryResponse
    ↓
Frontend rendert Ergebnisse
```

---

**Hinweis für Entwickler**: Diese Dokumentation deckt die API ab. Für interne Implementierungsdetails siehe die Source-Code-Kommentare.
