# Vollständige Funktionsübersicht - Text2SQL System

## 📋 Alle implementierten Funktionen

Diese Dokumentation listet **alle** implementierten Funktionen des Text2SQL-Systems auf.

---

## 🔧 Backend-Funktionen

### 1. API-Endpunkte

#### 1.1 `GET /` - Health Check
- **Funktion**: Status-Endpoint
- **Rückgabe**: API-Version, Features-Liste
- **Zweck**: Überprüfung ob API läuft

#### 1.2 `POST /query` - Hauptendpoint
- **Funktion**: Verarbeitet Text2SQL-Anfragen
- **Input**: `QueryRequest` (question, database, page, page_size)
- **Output**: `QueryResponse` (SQL, Ergebnisse, Metadaten)
- **Pipeline**: 6-stufiger Verarbeitungsprozess

---

### 2. LLM-Funktionen (OpenAI Generator)

#### 2.1 `check_ambiguity()`
- **Was**: Prüft ob eine Frage mehrdeutig ist
- **Input**: Frage, Schema, KB, Meanings
- **Output**: JSON mit `is_ambiguous`, `reason`, `questions[]`
- **Zweck**: Erkennt unklare Anfragen bevor SQL generiert wird
- **Fehlerbehandlung**: Graceful - gibt `is_ambiguous: false` zurück bei Fehler

#### 2.2 `generate_sql()`
- **Was**: Generiert SQL aus natürlicher Sprache
- **Input**: Frage, Schema, KB, Meanings
- **Output**: JSON mit `sql`, `explanation`, `confidence`, `thought_process`
- **Features**:
  - Few-Shot Examples im Prompt
  - Strukturierte JSON-Ausgabe
  - SQL-Bereinigung (entfernt Markdown)
  - Confidence-Score
- **Fehlerbehandlung**: Gibt `sql: null` zurück bei Fehler

#### 2.3 `validate_sql()`
- **Was**: Validiert generierte SQL-Query
- **Input**: SQL, Schema
- **Output**: JSON mit `is_valid`, `errors[]`, `severity`, `suggestions[]`
- **Severity-Levels**: `low`, `medium`, `high`
- **Zweck**: Semantische Validierung durch LLM
- **Fehlerbehandlung**: Gibt `is_valid: true` zurück bei Fehler (non-blocking)

#### 2.4 `summarize_results()`
- **Was**: Erstellt Zusammenfassung der Abfrageergebnisse
- **Input**: Frage, SQL, Ergebnisse, Row-Count, Notice
- **Output**: Natürlichsprachliche Zusammenfassung (String)
- **Zweck**: Macht rohe Daten verständlicher
- **Fehlerbehandlung**: Wird übersprungen bei Fehler

#### 2.5 `_call_openai()` (Intern)
- **Was**: Generischer OpenAI API-Call
- **Features**:
  - Error Handling für Rate Limits
  - Error Handling für Authentication
  - Temperature: 0.2 (konsistent)
- **Fehlerbehandlung**: Spezifische RuntimeErrors

#### 2.6 `_parse_json_response()` (Intern)
- **Was**: Robustes JSON-Parsing
- **Features**:
  - Entfernt Markdown-Formatierung (```json```)
  - Brace-Counting für korrektes Parsing
  - Handle Escape-Sequenzen
  - Fallback: Entfernt Steuerzeichen
  - Fallback: `strict=False` Parsing
- **Zweck**: LLMs geben manchmal JSON mit Markdown/Steuerzeichen zurück

#### 2.7 `_ensure_generation_fields()` (Intern)
- **Was**: Validiert und normalisiert SQL-Generierung-Response
- **Features**:
  - Setzt Default-Werte (`thought_process`, `explanation`)
  - Konvertiert `confidence` zu Float
  - Setzt `sql: None` falls fehlend

---

### 3. Database-Funktionen (Database Manager)

#### 3.1 `get_schema_and_sample()`
- **Was**: Holt Schema + Beispieldaten
- **Output**: Formatierter String mit:
  - CREATE TABLE Statements für alle Tabellen
  - Eine Beispielzeile pro Tabelle (JSON-formatierte)
- **Zweck**: Kontext für LLM (zeigt Struktur + Beispielwerte)
- **Besonderheit**: Beispielzeilen wichtig für JSON-Spalten

#### 3.2 `get_table_columns()`
- **Was**: Mapping von Tabellen zu Spalten
- **Output**: `Dict[str, List[str]]` (Tabellenname → Spaltenliste)
- **Caching**: `@lru_cache(maxsize=1)` - wird einmal pro Instanz gecacht
- **Zweck**: Validierung (prüft ob generierte SQL nur existierende Tabellen/Spalten verwendet)
- **Methode**: PRAGMA table_info für jede Tabelle

#### 3.3 `execute_query()`
- **Was**: Führt SQL aus
- **Input**: SQL-String, optional `max_rows`
- **Output**: `Tuple[List[Dict], bool]` (Ergebnisse, truncated-Flag)
- **Features**:
  - Konvertiert Zeilen zu Dictionaries (für JSON-Serialisierung)
  - Begrenzt auf `max_rows` (Standard: 100)
  - Erkennt Truncation (holt `max_rows + 1`, prüft ob mehr vorhanden)
  - Row Factory: `sqlite3.Row` für Dictionary-Konvertierung
- **Fehlerbehandlung**: SQLite-Fehler werden weitergegeben

---

### 4. Sicherheits-Funktionen (SQL Guard)

#### 4.1 `enforce_safety()`
- **Was**: Rule-based Sicherheitsprüfungen
- **Prüfungen**:
  1. SQL vorhanden und String?
  2. Nur ein Statement (max. 1 Semikolon)?
  3. Beginnt mit SELECT oder WITH?
  4. Keine gefährlichen Keywords: INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, PRAGMA, REPLACE, TRUNCATE
- **Output**: `None` wenn sicher, `str` mit Fehlermeldung wenn unsicher
- **Zweck**: Verhindert Datenverlust durch gefährliche Operationen

#### 4.2 `enforce_known_tables()`
- **Was**: Prüft ob nur bekannte Tabellen verwendet werden
- **Features**:
  - Extrahiert Tabellennamen aus SQL (FROM/JOIN via Regex)
  - Ignoriert CTEs (Common Table Expressions)
  - Prüft gegen Liste bekannter Tabellen
- **Output**: `None` wenn alle Tabellen bekannt, `str` mit Fehlermeldung wenn unbekannt
- **Zweck**: Verhindert SQL-Injection durch erfundene Tabellen

---

### 5. Context-Loading-Funktionen

#### 5.1 `load_context_files()`
- **Was**: Lädt Knowledge Base und Spalten-Bedeutungen
- **Input**: Datenbankname, Datenverzeichnis
- **Output**: `Tuple[str, str]` (KB-Text, Meanings-Text)
- **Features**:
  - Lädt KB aus `.jsonl` Datei
  - Lädt Meanings aus `.json` Datei
  - Formatiert für LLM-Prompt
  - Fehlerbehandlung: Gibt `[FEHLER ...]` String zurück bei Fehler
- **KB-Format**: `• {knowledge}: {definition}`
- **Meanings-Format**: Unterstützt nested JSON-Strukturen für JSON-Spalten

---

### 6. Model-Funktionen (Pydantic)

#### 6.1 `QueryRequest`
- **Felder**:
  - `question: str` (erforderlich)
  - `database: str = "credit"` (optional, Default)
  - `page: int = 1` (optional, für Paging)
  - `page_size: int = 100` (optional, für Paging)
- **Funktion**: Request-Validierung

#### 6.2 `QueryResponse`
- **Felder**:
  - `question: str`
  - `ambiguity_check: Optional[AmbiguityResult]`
  - `generated_sql: str`
  - `validation: Optional[ValidationResult]`
  - `results: List[Dict[str, Any]]`
  - `row_count: int`
  - `notice: Optional[str]`
  - `summary: Optional[str]`
  - `explanation: Optional[str]`
  - `error: Optional[str]`
- **Funktion**: Response-Strukturierung

#### 6.3 `AmbiguityResult`
- **Felder**:
  - `is_ambiguous: bool`
  - `reason: Optional[str]`
  - `questions: List[str]` (Klärende Fragen)
- **Funktion**: Ambiguity-Detection-Ergebnis

#### 6.4 `ValidationResult`
- **Felder**:
  - `is_valid: bool`
  - `errors: List[str]`
  - `severity: str` ("low", "medium", "high")
  - `suggestions: List[str]`
- **Funktion**: SQL-Validation-Ergebnis

---

### 7. Pipeline-Funktionen (Main Endpoint)

#### 7.1 Kontext-Laden
- **Was**: Lädt Schema, KB, Meanings
- **Features**:
  - Fehlerprüfung für Kontextdateien
  - Logging der geladenen Zeichenanzahl
  - Graceful Error Handling

#### 7.2 Ambiguity Detection
- **Was**: Prüft Frage auf Mehrdeutigkeit
- **Features**:
  - Non-blocking (wird übersprungen bei Fehler)
  - Logging der Ergebnisse
  - Zeigt Klärungsfragen wenn mehrdeutig

#### 7.3 SQL Generation
- **Was**: Generiert SQL aus Frage
- **Features**:
  - Logging von Confidence und Explanation
  - Prüft ob SQL generiert wurde
  - Gibt Fehler-Response zurück wenn keine SQL

#### 7.4 SQL Validation (2 Ebenen)
- **Was**: Validiert generierte SQL
- **Ebenen**:
  1. **Rule-based** (SQL Guard):
     - `enforce_safety()` - Gefährliche Operationen
     - `enforce_known_tables()` - Nur bekannte Tabellen
  2. **LLM-based**:
     - Semantische Validierung
     - Severity-basierte Entscheidung (nur "high" stoppt Pipeline)

#### 7.5 SQL Execution
- **Was**: Führt SQL aus
- **Features**:
  - Begrenzt auf `MAX_RESULT_ROWS` (100)
  - Erkennt Truncation
  - Konvertiert zu Dictionaries
  - Logging der Zeilenanzahl

#### 7.6 Result Summarization
- **Was**: Erstellt Zusammenfassung
- **Features**:
  - Non-blocking (wird übersprungen bei Fehler)
  - Fallback: Einfache Zusammenfassung mit Spaltennamen
  - Zeigt erste 3 Zeilen an LLM

#### 7.7 Response-Erstellung
- **Was**: Kombiniert alle Ergebnisse
- **Features**:
  - Enthält alle Metadaten (Ambiguity, Validation, etc.)
  - Strukturierte JSON-Response
  - Error-Handling für alle Schritte

---

## 🎨 Frontend-Funktionen

### 1. UI-Komponenten

#### 1.1 Theme Toggle
- **Funktion**: Wechselt zwischen Dark/Light Mode
- **Implementierung**: `toggleTheme()` Funktion
- **State**: `theme` State (dark/light)
- **UI**: Sonne/Mond Icon im Header

#### 1.2 Chat-Interface
- **Funktion**: Zeigt Nachrichten-Thread
- **Features**:
  - User Messages
  - Assistant Messages
  - Error Messages
  - Loading Indicator
- **Auto-Scroll**: Scrollt automatisch zu neuesten Nachrichten

#### 1.3 Input-Bereich
- **Funktion**: Textarea für Fragen
- **Features**:
  - Auto-Resize (max. 200px Höhe)
  - Enter zum Senden (Shift+Enter für neue Zeile)
  - Disabled während Loading
  - Placeholder-Text

#### 1.4 Send-Button
- **Funktion**: Sendet Frage an Backend
- **Features**:
  - Disabled wenn Textarea leer
  - Disabled während Loading
  - Send-Icon

---

### 2. Daten-Anzeige-Funktionen

#### 2.1 Ergebnis-Tabelle
- **Funktion**: Zeigt SQL-Ergebnisse als Tabelle
- **Features**:
  - Dynamische Spalten (basierend auf Ergebnissen)
  - Responsive Design
  - Zeigt alle Zeilen aus `results` Array

#### 2.2 SQL-Anzeige (Toggle)
- **Funktion**: Zeigt/versteckt generierte SQL
- **Features**:
  - Toggle-Button mit Code-Icon
  - Syntax-Highlighting (via `<pre>` Tag)
  - Copy-to-Clipboard Funktion
  - Visuelles Feedback beim Kopieren (Check-Icon)

#### 2.3 Zusammenfassung
- **Funktion**: Zeigt LLM-generierte Zusammenfassung
- **Anzeige**: Banner über Tabelle

#### 2.4 Notice-Banner
- **Funktion**: Zeigt wichtige Hinweise
- **Beispiele**:
  - "Ergebnis wurde auf 100 Zeilen gekürzt"
  - Paging-Informationen

---

### 3. API-Integration-Funktionen

#### 3.1 `askQuestion()`
- **Funktion**: Sendet Request an Backend
- **Input**: Frage-String
- **Output**: Response-JSON
- **Features**:
  - POST Request zu `/query`
  - JSON Body mit Frage und Datenbank
  - Error Handling

#### 3.2 `handleSubmit()`
- **Funktion**: Verarbeitet Form-Submission
- **Features**:
  - Validiert Input (nicht leer, nicht während Loading)
  - Erstellt User Message
  - Ruft API auf
  - Erstellt Assistant Message mit allen Daten
  - Error Handling mit Error Messages
  - State Management (Loading, Messages)

#### 3.3 `handleKeyDown()`
- **Funktion**: Keyboard-Shortcuts
- **Features**:
  - Enter = Submit
  - Shift+Enter = Neue Zeile

---

### 4. Utility-Funktionen

#### 4.1 `toggleSQL()`
- **Funktion**: Togglet SQL-Anzeige für spezifische Nachricht
- **State**: `showSQL` Flag pro Message

#### 4.2 `copyToClipboard()`
- **Funktion**: Kopiert Text in Zwischenablage
- **Features**:
  - Visuelles Feedback (Check-Icon für 2 Sekunden)
  - State: `copiedId` für Feedback

---

## 🔄 Pipeline-Funktionen (Gesamtsystem)

### 1. Multi-Stage Processing Pipeline

#### Stage 1: Context Loading
- Lädt Schema aus SQLite
- Lädt KB aus JSONL
- Lädt Meanings aus JSON
- Validierung der Kontextdateien

#### Stage 2: Ambiguity Detection
- LLM-basierte Mehrdeutigkeitsprüfung
- Generiert Klärungsfragen wenn nötig
- Non-blocking (überspringbar)

#### Stage 3: SQL Generation
- LLM-basierte SQL-Generierung
- Few-Shot Prompting
- Strukturierte JSON-Ausgabe
- Confidence-Score

#### Stage 4: SQL Validation
- **4a. Rule-based**: SQL Guard (Sicherheit)
- **4b. LLM-based**: Semantische Validierung
- Severity-basierte Entscheidung

#### Stage 5: SQL Execution
- SQLite-Query-Ausführung
- Ergebnis-Konvertierung
- Truncation-Erkennung

#### Stage 6: Result Processing
- LLM-basierte Zusammenfassung
- Response-Zusammenstellung
- Metadaten-Anreicherung

---

## 🛡️ Sicherheits-Funktionen

### 1. SQL Guard (Rule-based)
- ✅ Prüft auf gefährliche Keywords
- ✅ Erlaubt nur SELECT/CTE
- ✅ Verhindert mehrere Statements
- ✅ Prüft auf bekannte Tabellen

### 2. LLM Validation
- ✅ Semantische Korrektheit
- ✅ Severity-Levels
- ✅ Fehler-Suggestions

### 3. Input Validation
- ✅ Pydantic Models validieren Request
- ✅ Type-Checking zur Laufzeit
- ✅ Automatische Fehlermeldungen

---

## 📊 Logging & Monitoring-Funktionen

### 1. Console Logging
- ✅ Detaillierte Logs für jeden Pipeline-Schritt
- ✅ Emoji-Icons für bessere Lesbarkeit
- ✅ Zeichenanzahl der geladenen Kontexte
- ✅ SQL-Preview (erste 200 Zeichen)
- ✅ Confidence-Scores
- ✅ Error-Logs mit Stack Traces

### 2. Response-Metadaten
- ✅ Ambiguity-Status
- ✅ Validation-Status
- ✅ Confidence-Score
- ✅ Explanation
- ✅ Summary

---

## 🎯 Spezielle Features

### 1. Graceful Degradation
- ✅ System funktioniert auch wenn einzelne Schritte fehlschlagen
- ✅ Ambiguity Check: Überspringbar
- ✅ Validation: Überspringbar
- ✅ Summarization: Überspringbar

### 2. Error Handling
- ✅ Spezifische Fehlermeldungen für jeden Fehlertyp
- ✅ User-freundliche Fehlermeldungen
- ✅ Developer-freundliche Logs
- ✅ HTTP Status Codes (404 für FileNotFound)

### 3. JSON-Spalten-Support
- ✅ Beispielzeilen zeigen JSON-Struktur
- ✅ LLM versteht JSON-Spalten durch Beispiele
- ✅ Unterstützung für `json_extract()` in Prompts

### 4. CTE-Support
- ✅ SQL Guard erkennt CTEs
- ✅ CTEs werden nicht als unbekannte Tabellen markiert
- ✅ Prompts erklären CTE-Verwendung

### 5. Few-Shot Prompting
- ✅ 3 Beispiele im SQL-Generation-Prompt
- ✅ Zeigt verschiedene Query-Typen
- ✅ Verbessert LLM-Performance

---

## 📱 Frontend-Features

### 1. Responsive Design
- ✅ Dark/Light Mode
- ✅ Mobile-friendly (Media Queries)
- ✅ Auto-resizing Textarea

### 2. User Experience
- ✅ Loading Indicators
- ✅ Auto-Scroll zu neuen Nachrichten
- ✅ Copy-to-Clipboard mit Feedback
- ✅ Toggle für SQL-Anzeige
- ✅ Visuelle Trennung User/Assistant/Error

### 3. State Management
- ✅ React Hooks (useState, useRef, useEffect)
- ✅ Message-History
- ✅ Loading-State
- ✅ Theme-State

---

## 🔧 Konfigurations-Funktionen

### 1. Config (`backend/config.py`)
- ✅ Environment Variables (.env)
- ✅ `OPENAI_API_KEY`
- ✅ `OPENAI_MODEL` (Default: gpt-4o-mini)
- ✅ `DATA_DIR` (Default: mini-interact)
- ✅ `MAX_RESULT_ROWS` (Default: 100)

### 2. CORS
- ✅ CORS Middleware aktiviert
- ✅ Erlaubt alle Origins (Development)
- ✅ Erlaubt alle Methods und Headers

---

## 📈 Performance-Features

### 1. Caching
- ✅ `@lru_cache` für `get_table_columns()` (1x pro Instanz)
- ⚠️ **Hinweis**: Schema/KB werden aktuell nicht gecacht (könnte optimiert werden)

### 2. Ergebnis-Begrenzung
- ✅ `MAX_RESULT_ROWS` verhindert Memory-Probleme
- ✅ Truncation-Erkennung
- ✅ Notice für Nutzer

### 3. Connection Management
- ✅ Datenbank-Verbindungen werden nach Gebrauch geschlossen
- ✅ Context Manager Pattern (try/finally)

---

## 🎓 Zusammenfassung: Alle Funktionen

### Backend (Python/FastAPI)
1. ✅ REST API Endpoints (GET /, POST /query)
2. ✅ Ambiguity Detection (LLM)
3. ✅ SQL Generation (LLM mit Few-Shot)
4. ✅ SQL Validation (Rule-based + LLM)
5. ✅ SQL Execution (SQLite)
6. ✅ Result Summarization (LLM)
7. ✅ Context Loading (Schema, KB, Meanings)
8. ✅ SQL Guard (Sicherheit)
9. ✅ Error Handling (Graceful Degradation)
10. ✅ Logging (Detailliert)
11. ✅ Request/Response Validation (Pydantic)
12. ✅ JSON-Parsing (Robust mit Fallbacks)
13. ✅ CTE-Support
14. ✅ JSON-Spalten-Support

### Frontend (React)
1. ✅ Chat-Interface
2. ✅ Theme Toggle (Dark/Light)
3. ✅ Auto-Resize Textarea
4. ✅ Keyboard Shortcuts (Enter/Shift+Enter)
5. ✅ Ergebnis-Tabelle
6. ✅ SQL-Anzeige (Toggle)
7. ✅ Copy-to-Clipboard
8. ✅ Loading Indicators
9. ✅ Auto-Scroll
10. ✅ Error Messages
11. ✅ Zusammenfassung-Anzeige
12. ✅ Notice-Banner

### Sicherheit
1. ✅ SQL Guard (Rule-based)
2. ✅ Table Validation
3. ✅ LLM Validation
4. ✅ Input Validation (Pydantic)
5. ✅ Error Sanitization

### Pipeline
1. ✅ 6-stufige Verarbeitungspipeline
2. ✅ Graceful Degradation
3. ✅ Non-blocking Steps
4. ✅ Metadaten-Anreicherung

---

## 📊 Statistik

- **Backend-Funktionen**: ~20 Hauptfunktionen
- **Frontend-Funktionen**: ~12 Hauptfunktionen
- **Sicherheits-Funktionen**: 5 Ebenen
- **Pipeline-Stufen**: 6 Stufen
- **LLM-Calls pro Query**: 3-4 (Ambiguity, SQL, Validation, Summary)
- **Validierungsebenen**: 3 (Input, Rule-based, LLM)

---

**Stand**: Version 2.1.0  
**Datum**: 2024

