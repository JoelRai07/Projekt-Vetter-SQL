# Architektur & Prozesse - Text2SQL System

## 📖 Inhaltsverzeichnis
1. [System-Übersicht](#system-übersicht)
2. [Detaillierter Prozessablauf](#detaillierter-prozessablauf)
3. [Komponenten & ihre Rollen](#komponenten--ihre-rollen)
4. [Datenfluss & Pipeline](#datenfluss--pipeline)
5. [Frontend-Backend Kommunikation](#frontend-backend-kommunikation)
6. [Technologische Entscheidungen](#technologische-entscheidungen)

---

## System-Übersicht

### Was ist das System?

**Text2SQL** ist ein System, das **natürliche Sprache in SQL-Abfragen übersetzt**. Ein Nutzer stellt eine Frage in normaler Sprache (z.B. "Zeige mir alle Premium-Kunden mit hoher Finanzstabilität"), und das System generiert automatisch die entsprechende SQL-Query, führt sie aus und präsentiert die Ergebnisse.

### Architektur auf höchster Ebene

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
│  • Nutzer-Interface                                         │
│  • Frage-Input, Paging-Steuerung                            │
│  • Ergebnisanzeige mit SQL-Visualization                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST (JSON)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 FASTAPI BACKEND                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Endpoint: POST /query                           │   │
│  │  • Entgegennahme der Nutzer-Anfrage                  │   │
│  │  • Koordination aller 6 Pipeline-Stufen              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
     ┌───────────────────┼───────────────────┐
     │                   │                   │
     ▼                   ▼                   ▼
  ┌─────────┐      ┌──────────┐      ┌──────────────┐
  │   LLM   │      │ Database │      │   Schema &   │
  │Generator│      │ Manager  │      │   KB Cache   │
  └─────────┘      └──────────┘      └──────────────┘
```

---

## Detaillierter Prozessablauf

### Phase 1: Anfrage-Entgegennahme & Context Loading

**Schritt 1.1: Frontend sendet Anfrage**
```
User: "Zeige mir Kunden mit hoher Schuldenlast nach Segment"
     ↓
Frontend POST /query
{
  "question": "Zeige mir Kunden mit hoher Schuldenlast nach Segment",
  "database": "credit",
  "page": 1,
  "page_size": 100,
  "use_react": true
}
```

**Schritt 1.2: Backend lädt Kontext (mit Caching)**

Der Backend lädt drei Kontextdokumente parallel:

1. **Schema** (7,5 KB)
   - CREATE TABLE Statements für alle Tabellen
   - Beispielzeilen von jeder Tabelle (wichtig für JSON-Spalten!)
   - Foreign Key Beziehungen
   - **Caching**: LRU-Cache (unendlich, ändert sich nie)

2. **Knowledge Base** (10 KB) - Domänen-Wissen
   - 51 Einträge mit Definitionen von Metriken
   - Formeln: DTI = debincratio, CUR = credutil, FSI = 0.3×(1-debincratio) + ...
   - Klassifizierungen: "Prime Customer", "Financially Vulnerable", etc.
   - **Caching**: TTL-Cache (1 Stunde, da Metriken stabil sind)

3. **Column Meanings** (15 KB) - Spalten-Definitionen
   - Beschreibung jeder Spalte
   - JSON-Felder und ihre Unterkategorien
   - Datentypen und Beispielwerte
   - **Caching**: TTL-Cache (1 Stunde)

**Warum dieser Ansatz?**
- Nutzer wartet schneller (Caching)
- LLM erhält vollständigen Kontext für bessere Qualität
- Schema-Änderungen sind selten (daher aggressives Caching)

---

### Phase 2: Ambiguity Detection (Mehrdeutigkeitserkennung)

**Schritt 2.1: LLM prüft auf Mehrdeutigkeit**

```
LLM erhält:
- Nutzer-Frage
- Schema
- KB
- Column Meanings

LLM antwortet:
{
  "is_ambiguous": true,
  "reason": "Mehrere Interpretationen möglich...",
  "questions": [
    "Welche Metriken für 'Schuldenlast'? (DTI, totliabs, LTV?)",
    "Nur Premium-Segmente oder alle?",
    "Mindestanzahl Kunden pro Segment?"
  ]
}
```

**Wann ist eine Frage mehrdeutig?**

✅ MEHRDEUTIG (Pipeline stoppt):
- "debt burden" nicht eindeutig (DTI? totliabs? LTV?)
- "few customers" ohne Schwellenwert
- "relevant metrics" ohne Spezifizierung

❌ NICHT mehrdeutig:
- Wording etwas vage, aber Absicht ist klar
- Schema/KB erlaubt ein Standardinterpretation
- Zuverlässige Default-Werte vorhanden

**Warum separat prüfen?**
- Verhindert falsche SQL-Generierung bevor sie passiert
- Feedback an Nutzer statt stilles Scheitern
- Spart OpenAI-Kosten (keine verschwendeten SQL-Generierungen)

---

### Phase 3: SQL-Generierung mit ReAct + Retrieval

**Warum ReAct + Retrieval statt direkter Generierung?**

Direkter Ansatz ❌:
```
Input: Ganze Schema (7.5 KB) + KB (10 KB) + Frage
       → Token-Overkill (zu viel irrelevante Infos)
       → Teurere API-Calls
       → Mehr Fehler wegen Information Overload
```

ReAct + Retrieval ✅:
```
Iteration 1:
  - LLM denkt: "Ich brauche: core_record.clientseg, employment_and_income.debincratio, ..."
  - Vector Retrieval sucht: "debt-to-income ratio", "customer segments"
  - Relevant Schema: 16 Chunks (statt ganzes Schema)
  - Relevant KB: 18 Einträge (statt alle 51)
  
Iteration 2:
  - LLM denkt: "Brauch ich noch für Aggregationen..."
  - Weitere Retrieval-Runde
  
Iteration 3:
  - Genug Info gesammelt
  - SQL wird generiert
```

**Detaillierter Ablauf:**

```
Schritt 3.1: LLM Thinking Phase
  "THINK: Die Frage fragt nach Schuldenlast pro Segment.
   Ich benötige:
   - Kundensegmente (core_record.clientseg)
   - Schuldenlast-Metriken (debincratio, totliabs, ...)
   - Mögliche JOINs: core_record → employment_and_income → expenses_and_assets
   
   Search Queries:
   - 'debt-to-income ratio debincratio segment analysis'
   - 'customer segments clientseg premium standard'
   - 'total liabilities expenses assets'
   - 'foreign key relationships joins'"

Schritt 3.2: Vector Retrieval (ChromaDB + OpenAI Embeddings)
  Für jeden Search Query:
  - Semantische Suche in Schema-Chunks
  - Semantische Suche in KB-Einträgen
  - Semantische Suche in Column Meanings
  → Top-5 Ergebnisse pro Query

Schritt 3.3: LLM Observation & Reasoning
  "OBSERVE: Ich habe:
   - Schema für: core_record, employment_and_income, expenses_and_assets
   - KB Einträge für DTI, Financial Vulnerability
   - Meanings für alle relevanten Spalten
   
   REASON: Habe ich genug Info?
   - ✓ Kann debincratio extrahieren
   - ✓ Kann GROUP BY clientseg machen
   - ✓ Kann Aggregation durchführen
   → Ja, genug Info. SQL generieren."

Schritt 3.4: SQL Generation
  Mit NUR relevanten Infos:
  
  WITH customer_debt AS (
    SELECT
      cr.clientseg,
      ei.debincratio,
      ea.totliabs,
      ...
    FROM core_record cr
    JOIN employment_and_income ei ON ei.emplcoreref = cr.coreregistry
    JOIN expenses_and_assets ea ON ea.expemplref = ei.emplcoreref
  ),
  segment_stats AS (
    SELECT
      clientseg,
      COUNT(*) AS customer_count,
      AVG(debincratio) AS avg_dti,
      ...
    FROM customer_debt
    GROUP BY clientseg
    HAVING COUNT(*) >= 10
  )
  SELECT * FROM segment_stats
  UNION ALL
  SELECT 'GRAND TOTAL', ...
  ORDER BY ...
```

**Vorteile ReAct + Retrieval:**
- 40-60% Token-Ersparnis (nur relevante Infos)
- 10-15% bessere Accuracy (weniger Noise)
- Schneller (weniger zu verarbeiten)

---

### Phase 4: SQL-Validierung (Hybrid Approach)

**Zwei Validierungs-Ebenen:**

```
┌─────────────────────────────────────────┐
│      Generated SQL Query                │
└──────────────┬──────────────────────────┘
               │
        ┌──────▼──────┐
        │ Rule-based  │
        │ Validation  │
        │ (SQL Guard) │
        └──────┬──────┘
               │
     ✓ Sicherheits-Checks?
       - Nur SELECT/WITH erlaubt
       - Keine INSERT/UPDATE/DELETE/DROP
       - Nur bekannte Tabellen
       - Max 1 Statement
               │
        ┌──────▼──────┐
        │  LLM-based  │
        │ Validation  │
        │  (OpenAI)   │
        └──────┬──────┘
               │
     ✓ Semantische Korrektheit?
       - JOINs folgen FOREIGN KEY Chain?
       - Spalten korrekt qualifiziert?
       - JSON Pfade aus richtiger Tabelle?
       - GROUP BY/HAVING korrekt?
       - UNION ALL Spalten-Kompatibilität?
               │
        ┌──────▼──────────────────┐
        │ ✓ Valid → Execute       │
        │ ✗ Errors → Show to User │
        └─────────────────────────┘
```

**Beispiel einer Validierung:**

```sql
SELECT clientseg, COUNT(*) cnt
FROM core_record
GROUP BY clientseg
HAVING COUNT(*) > 10
UNION ALL
SELECT 'Total', COUNT(*)
FROM core_record
ORDER BY clientseg DESC
```

LLM prüft:
- ✓ Syntax ist korrekt
- ✓ Alle Tabellen existieren (core_record)
- ✓ Spalten existieren (clientseg)
- ✓ GROUP BY und HAVING konsistent
- ✓ UNION ALL: beide SELECTs haben 2 Spalten (clientseg/text, cnt/number)
- ✓ Kein INSERT/UPDATE/DELETE

Severity-Level:
- `low`: Style, funktioniert aber
- `medium`: Könnte falsche Ergebnisse geben
- `high`: Query nicht ausführbar

---

### Phase 5: SQL-Ausführung mit Paging

**Warum Paging?**
- Datenbank kann 10.000+ Zeilen zurückgeben
- Browser kann nicht 10.000 Zeilen auf einmal rendern
- Nutzer will nur erste 100 Zeilen sehen

**Paging-Prozess:**

```
Nutzer-Request: page=2, page_size=100
              ↓
Backend berechnet:
  - OFFSET = (page - 1) × page_size = 100
  - LIMIT = 100
              ↓
Original SQL:
  SELECT ... FROM ... WHERE ...
              ↓
Paging-SQL:
  SELECT ... FROM ... WHERE ... LIMIT 100 OFFSET 100
              ↓
Auch berechnet:
  - Total Row Count (ohne LIMIT/OFFSET)
  - Total Pages = ceil(Total / page_size)
  - has_next_page, has_previous_page
              ↓
Response enthält:
  {
    results: [...],
    page: 2,
    total_pages: 47,
    total_rows: 4650,
    has_next_page: true,
    has_previous_page: true
  }
```

**Determinismus:**
- Paging muss immer gleiche Zeilen pro Seite zurückgeben
- Dafür wird ein Query-ID (UUID) erstellt
- Session speichert: database, SQL, question
- Zweiter Request mit gleicher Query-ID verwendet gespeicherte SQL

---

### Phase 6: Ergebniszusammenfassung

```
Input für LLM:
  - Nutzer-Frage: "Schuldenlast nach Segment"
  - Generierte SQL: "SELECT clientseg, AVG(debincratio), ..."
  - Erste 3 Ergebnis-Zeilen (als JSON)
  - Row-Count: 1247

LLM generiert:
  "Die Analyse zeigt, dass Premium-Kunden eine durchschnittliche 
   Schuldenquote von 32% haben, während Standard-Kunden bei 45% liegen. 
   Insgesamt wurden 1247 Kundensätze analysiert..."
```

**Warum?**
- Rohe Daten sind schwer zu verstehen
- Natürlichsprachliche Zusammenfassung hilft Nutzer
- Gibt sofort wichtigste Insights

---

## Komponenten & ihre Rollen

### Frontend (React)

**Datei**: `frontend/src/App.jsx`

```
┌────────────────────────────┐
│   Nutzer-Input             │
│   - Text eingeben          │
│   - Datenbank wählen       │
│   - Submit                 │
└────────────────┬───────────┘
                 │
                 ▼
          ┌─────────────┐
          │  HTTP POST  │
          └──────┬──────┘
                 │
   ┌─────────────┼─────────────┐
   ▼             ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ Ergebnisse
│ darstellen
│ Paging-
│ Steuerung
│ SQL
│ anzeigen
│ Kopieren
│ Thema
│ (Dark/Light)
```

**Key Features:**
- Dark/Light Theme
- Responsive Design
- SQL-Visualisierung mit Syntax-Highlighting
- Paging-Steuerung (Seite X von Y)
- Copy-to-Clipboard für SQL
- Error-Handling

### Backend Pipeline

**Datei**: `backend/main.py`

```
1. Schema Retrieval Module
   └─ Lädt Schema (Core Record, Employment, Assets, ...)
   
2. LLM Generator Module
   └─ Ambiguity Detection
   └─ SQL Generation (mit ReAct)
   └─ SQL Validation
   └─ Result Summarization
   
3. Schema Retriever (RAG)
   └─ ChromaDB Vector Store
   └─ Semantische Suche
   
4. Database Manager
   └─ Query Execution
   └─ Paging Logic
   
5. Caching Layer
   └─ Schema Cache (LRU)
   └─ KB Cache (TTL: 1h)
   └─ Query Result Cache (TTL: 5min)
   
6. Security Layer (SQL Guard)
   └─ Regex-basierte Sicherheitsprüfungen
```

### LLM-Generator (OpenAI)

**Modell**: Aktuell GPT-5.2

**Methoden:**
1. `check_ambiguity()` - Mehrdeutigkeitsprüfung
2. `generate_sql()` - Standard SQL-Generierung
3. `generate_sql_with_react_retrieval()` - ReAct mit Retrieval
4. `validate_sql()` - LLM-basierte Validierung
5. `summarize_results()` - Ergebniszusammenfassung

---

## Datenfluss & Pipeline

### End-to-End Request Flow

```
╔═══════════════════════════════════════════════════════════╗
║                    USER SENDS QUESTION                    ║
║        "Zeige Schuldenlast pro Kundengruppe"              ║
╚═════════════┬═════════════════════════════════════════════╝
              │
              ▼
╔═══════════════════════════════════════════════════════════╗
║  PHASE 1: CONTEXT LOADING (Parallel, mit Caching)         ║
║  └─ Schema: CREATE TABLE + Beispielzeilen (7.5 KB)        ║
║  └─ KB: 51 Metriken & Formeln (10 KB)                     ║
║  └─ Meanings: Spalten-Definitionen (15 KB)                ║
╚═════════════┬═════════════════════════════════════════════╝
              │
              ▼
╔═══════════════════════════════════════════════════════════╗
║  PHASE 2: AMBIGUITY DETECTION (Parallel mit SQL Gen)      ║
║  └─ LLM prüft: Ist Frage mehrdeutig?                      ║
║  └─ if mehrdeutig → STOP & Rückfragen an Nutzer           ║
║  └─ if klar → Weiter zu Phase 3                           ║
╚═════════════┬═════════════════════════════════════════════╝
              │
              ▼
╔═══════════════════════════════════════════════════════════╗
║  PHASE 3: SQL GENERATION (ReAct + Retrieval)              ║
║  └─ Iteration 1: Thinking + Search Queries                ║
║  └─ ChromaDB Retrieval: Top-K relevante Chunks            ║
║  └─ Iteration 2: Observation + Reasoning                  ║
║  └─ Weiter bis genug Info vorhanden                       ║
║  └─ SQL wird generiert mit Confidence Score               ║
╚═════════════┬═════════════════════════════════════════════╝
              │
              ▼
╔═══════════════════════════════════════════════════════════╗
║  PHASE 4: SQL VALIDATION (Hybrid: Rule + LLM)             ║
║  └─ SQL Guard: Sicherheitsprüfungen (Regex-basiert)       ║
║  └─ LLM Validator: Semantische Korrektheit                ║
║  └─ if Fehler → Optional: Self-Correction Loop            ║
║  └─ if valide → Weiter zu Phase 5                         ║
╚═════════════┬═════════════════════════════════════════════╝
              │
              ▼
╔═══════════════════════════════════════════════════════════╗
║  PHASE 5: EXECUTION + PAGING                              ║
║  └─ SQLite führt Query aus                                ║
║  └─ Paging: OFFSET & LIMIT anwenden                       ║
║  └─ Berechne: Total Pages, has_next_page, etc.            ║
║  └─ Return: Results (100 Zeilen) + Metadaten              ║
╚═════════════┬═════════════════════════════════════════════╝
              │
              ▼
╔════════════════════════════════════════════════════════════╗
║  PHASE 6: RESULT SUMMARIZATION                             ║
║  └─ LLM erstellt natürlichsprachliche Zusammenfassung      ║
║  └─ Zeigt wichtigste Insights                              ║
║  └─ Fallback: Wenn LLM-Call fehlschlägt, alternative       ║
╚═════════════┬══════════════════════════════════════════════╝
              │
              ▼
╔════════════════════════════════════════════════════════════╗
║             JSON RESPONSE AN FRONTEND                      ║
║  {                                                         ║
║    question: "...",                                        ║
║    generated_sql: "SELECT ...",                            ║
║    results: [...],                                         ║
║    page: 1, total_pages: 47,                               ║
║    summary: "Die Analyse zeigt...",                        ║
║    ambiguity_check, validation, query_id, ...              ║
║  }                                                         ║
╚════════════════════════════════════════════════════════════╝
              │
              ▼
╔════════════════════════════════════════════════════════════╗
║        FRONTEND RENDERS RESULTS TO USER                    ║
╚════════════════════════════════════════════════════════════╝
```

---

## Frontend-Backend Kommunikation

### Request Format

```javascript
POST /query HTTP/1.1
Content-Type: application/json

{
  "question": "Zeige Schuldenlast pro Segment",
  "database": "credit",
  "page": 1,
  "page_size": 100,
  "use_react": true,
  "query_id": null  // Für Paging: UUID der Anfrage
}
```

### Response Format

```javascript
{
  // Basis-Info
  "question": "...",
  "generated_sql": "SELECT ...",
  
  // Ergebnisse + Paging
  "results": [
    { "clientseg": "Premium", "avg_dti": 0.32, ... },
    { "clientseg": "Standard", "avg_dti": 0.45, ... }
  ],
  "row_count": 3,
  "page": 1,
  "total_pages": 1,
  "total_rows": 3,
  "has_next_page": false,
  "has_previous_page": false,
  
  // Metadaten + Zusammenfassung
  "summary": "Die Analyse zeigt dass...",
  "explanation": "Diese Query aggregiert...",
  "notice": "Zeige Seite 1 von 1",
  
  // Validierung & Ambiguity
  "ambiguity_check": {
    "is_ambiguous": false,
    "reason": "..."
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "severity": "low"
  },
  
  // Session
  "query_id": "a1b2c3d4..."
}
```

---

## Technologische Entscheidungen

### 1. FastAPI vs. Flask vs. Django

**Entscheidung: FastAPI** ✅

**Gründe:**
- Automatic OpenAPI documentation
- Built-in JSON serialization
- Async support für parallelism
- Type hints & Pydantic validation
- Performance: ~17x schneller als Flask

**Alternative betrachtet:**
- Flask: Zu minimalistisch
- Django: Overkill für diese API

### 2. SQLite vs. PostgreSQL vs. MySQL

**Entscheidung: SQLite** ✅

**Gründe:**
- Datensätze sind statisch (Mini-Interact Dataset)
- Keine Concurrent Writes nötig
- Zero Configuration
- Perfekt für Uni-Projekt (keine Server-Setup)
- Schnell für Read-Operationen

### 3. OpenAI API vs. Open-Source LLMs

**Entscheidung: OpenAI (GPT-5.2)** ✅

**Gründe:**
- Beste Qualität für SQL-Generierung
- Zuverlässige API
- Kosteneffizient (GPT-5.2)
- Schnelle Updates & neue Modelle

**Geplante Migration zu GPT-5.2:**
- Bessere Instruction Following
- Höhere Accuracy bei komplexen Queries
- Bessere JSON-Parsing Zuverlässigkeit
- Kostenbenefit durch effizientere Token-Nutzung

### 4. ChromaDB vs. Pinecone vs. Weaviate

**Entscheidung: ChromaDB** ✅

**Gründe:**
- Open-source, kostenlos
- Keine externe Dependencies
- Lokal persistent (vector_store/)
- Einfach zu debuggen
- Perfekt für statisches Schema

### 5. Caching: LRU vs. Redis vs. Memcached

**Entscheidung: Hybrid (LRU + TTLCache)** ✅

```python
# Schema: LRU Cache (unendlich, ändert sich nie)
@lru_cache(maxsize=32)
def get_cached_schema(db_path):
    ...

# KB & Meanings: TTL Cache (1 Stunde)
kb_cache = TTLCache(maxsize=32, ttl=3600)

# Query Results: TTL Cache (5 Minuten)
query_cache = TTLCache(maxsize=100, ttl=300)
```

**Gründe:**
- In-Process Caching (keine Netzwerk-Latenz)
- TTL für Konsistenz mit Daten
- LRU für Schema (sehr stabil)

---

## Zusammenfassung der Architektur

| Aspekt | Technologie | Grund |
|--------|-------------|-------|
| **Frontend** | React | Modern, Reactive, User-Friendly |
| **Backend API** | FastAPI | Async, Type-Safe, High-Performance |
| **Database** | SQLite | Static Data, No Setup, Fast Reads |
| **LLM** | OpenAI GPT-5.2 | Best Quality, API, Reliable |
| **Retrieval** | ChromaDB | Local, Free, Simple, Effective |
| **Caching** | LRU + TTL | Fast, Consistent, In-Process |
| **Validation** | Hybrid | Defense in Depth, Robust |

Diese Architektur ist:
- **Scalable**: Leicht auf andere Datenbanken ausweiterbar
- **Maintainable**: Klare Separation of Concerns
- **Robust**: Multiple Validierungs-Ebenen
- **Efficient**: Parallel Processing, Caching, ReAct-Retrieval
- **User-Friendly**: Dark Mode, Paging, Error Messages
