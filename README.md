# ChatWithYourData – Text2SQL Projekt 📌

## Übersicht

Dieses Projekt wurde im Rahmen des Moduls "Projekt" an der DHBW Stuttgart entwickelt. Ziel ist es, eine Anwendung zu erstellen, die es Nutzer:innen ermöglicht, natürliche Sprache zu verwenden, um SQL-Abfragen automatisch zu generieren und eine Datenbank abzufragen. Dazu wird ein Large Language Model (LLM) eingebunden, das Text → SQL übersetzt.

Das Projekt basiert auf dem Benchmark-Datensatz **BIRD-INTERACT (mini-interact)**. Die Hauptaufgabe besteht darin, die bereitgestellten Fragen korrekt zu beantworten, indem die Anwendung dynamisch SQL-Abfragen erzeugt und ausführt.

## 🎯 Projektziele

- Entwicklung eines funktionierenden Text2SQL-Prototyps
- Nutzung moderner LLM-Technologien zur automatischen SQL-Generierung
- Erstellung einer Architektur, die Frontend, Backend, LLM und Datenbank verbindet
- Umsetzung der im Modul geforderten Methoden des Software Engineerings, Projektmanagements und Teamarbeit

## 🧠 Motivation

Daten sind das Gold des 21. Jahrhunderts – jedoch ist SQL für viele Mitarbeitende eine Hürde. Moderne KI-Modelle ermöglichen es, natürliche Sprache effizient zu interpretieren.

Mit diesem Projekt helfen wir Unternehmen dabei, **data-driven** zu werden, indem wir die Distanz zwischen Mensch und Datenbank reduzieren.

## 🎯 Projektziele

- ✅ Funktionierender Text2SQL-Prototyp
- ✅ Moderne LLM-Integration (OpenAI/Claude)
- ✅ Robuste SQL-Generierung mit Ambiguity Detection
- ✅ Sichere Datenbankabfragen mit Defense-in-Depth
- ✅ BSL-first Architektur (Business Semantics Layer)
- ✅ Benutzerfreundliche Fehlerbehandlung

## 🛠️ Technologie-Stack

### Backend
- **Python 3.11+** mit FastAPI
- **OpenAI API** GPT-5.2
- **SQLite** für Datenbankabfragen
- **BSL (Business Semantics Layer)** für explizite Business Rules
- **Pydantic** für Request/Response Validierung

### Frontend
- **React 18+** mit TypeScript
- **Tailwind CSS** für Styling
- Real-time Chat-Interface
- Pagination für große Ergebnismengen

### DevOps & Tools
- **Docker** für Containerisierung
- **GitHub** für Versionskontrolle und CI/CD
- **SQLite** als Produktionsdatenbank
- Logs mit strukturiertem Output (JSON)

## 📊 Datensatz

- **BIRD-INTERACT Benchmark** (mini-interact variant)
- **Datenbank**: `credit.sqlite` (Credit Risk Domain)
- **Fragen**: 10+ komplexe SQL-Anfragen
- **Kontextdateien**:
  - `credit_kb.jsonl` - Domain Knowledge Base
  - `credit_column_meaning_base.json` - Spalten-Definitionen
  - `credit_bsl.txt` - Business Semantics Layer (generiert aus KB + Meanings)
  - `credit_metric_sql_templates.json` - SQL-Templates für Metriken

## 🚀 Schnelstart

### Voraussetzungen
```bash
Python 3.11+
pip / conda
OpenAI API Key (oder Claude)
```

### Installation

```bash
# 1. Repository klonen
git clone https://github.com/YourTeam/ChatWithYourData.git
cd ChatWithYourData

# 2. Backend Setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Environment Variables
cp .env.example .env
# Fülle aus: OPENAI_API_KEY, DATABASE_PATH, etc.

# 4. Frontend Setup
cd ../frontend
npm install

# 5. Starten
# Terminal 1 (Backend)
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 (Frontend)
cd frontend
npm start
```

### Test
```bash
# Backend ist live unter http://127.0.0.1:8000
# Frontend unter http://localhost:5173
```

## 🏗️ Systemarchitektur

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                     │
│  Chat-Interface → /query Request → Response Handler     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ↓ REST API
┌────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                     │
│                                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. Ambiguity Detection (Parallel)               │   │
│  │    → Erkennt mehrdeutige Fragen                 │   │
│  │    → Schlägt Klärungsfragen vor                 │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│                          ↓                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 2. SQL Generation (BSL-first)                    │   │
│  │    → Business Semantics Layer (BSL)              │   │
│  │    → Vollständiges Schema + Meanings + BSL       │   │
│  │    → Explizite Business Rules                    │   │
│  │    → Temperature=0.2 für Determinismus          │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│                          ↓                             │
│                    LLM (OpenAI)                        │
│                    (GPT-5.2)                           │
│                                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 3. SQL Validation (LLM + Rule-Based)            │   │
│  │    → Syntax Check                               │   │
│  │    → JOIN Validation (FK-Chain)                 │   │
│  │    → JSON Path Verification                     │   │
│  │    → Self-Correction bei Fehlern                │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│                          ↓                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 4. Safety Checks (Defense-in-Depth)             │   │
│  │    → Regex-basierter SQL Guard                  │   │
│  │    → Nur SELECT erlaubt                         │   │
│  │    → Datenbank-Permissions (Read-Only)          │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│                          ↓                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 5. Query Execution (mit Paging)                 │   │
│  │    → Deterministische Query Sessions (UUID)     │   │
│  │    → LIMIT + OFFSET für Performance             │   │
│  │    → TTL Cache für Konsistenz                   │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│                          ↓                             │
│              SQLite (credit.sqlite)                    │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## 📝 API-Spezifikation

### POST `/query`

**Request:**
```json
{
  "question": "Welche Kunden haben eine Schuldenlast über 50%?",
  "database": "credit",
  "page": 1,
  "page_size": 100,
  "query_id": null
}
```

**Response (Success):**
```json
{
  "question": "Welche Kunden haben eine Schuldenlast über 50%?",
  "generated_sql": "SELECT cr.clientref, ei.debincratio FROM core_record cr JOIN ... WHERE ei.debincratio > 0.5 ORDER BY ei.debincratio DESC",
  "results": [
    {"clientref": "001", "debincratio": 0.65},
    {"clientref": "002", "debincratio": 0.58}
  ],
  "row_count": 247,
  "page": 1,
  "total_pages": 3,
  "total_rows": 247,
  "summary": "Gefunden: 247 Kunden mit Schuldenlast über 50%. Top 3 haben Quoten von 0.65, 0.58, 0.57.",
  "ambiguity_check": {
    "is_ambiguous": false,
    "reason": "Frage ist eindeutig"
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "severity": "low"
  },
  "query_id": "abc123def456",
  "explanation": "Groups customers by debt ratio and filters for those exceeding 50%"
}
```

**Response (Ambiguity):**
```json
{
  "is_ambiguous": true,
  "reason": "Schuldenlast ist mehrdeutig definiert",
  "questions": [
    "Welche Schuldenlast? (DTI, Gesamtkredite, LTV?)",
    "Über welche Periode? (aktuell, Durchschnitt, max?)"
  ],
  "error": "Bitte spezifizieren Sie Ihre Frage"
}
```

### GET `/`

Health-Check Endpoint.

## 🔧 Konfiguration

**`.env` Example:**
```bash
# LLM Configuration
OPENAI_API_KEY=sk-xxx...
OPENAI_MODEL=gpt-5.2
```

## 🐛 Bekannte Probleme & Lösungen

### Problem 1: UNION ALL mit ORDER BY
**Fehler**: `ORDER BY term does not match any column`
**Lösung**: UNION ALL in CTE wrappen
```sql
WITH results AS (
  SELECT ... UNION ALL SELECT ...
)
SELECT * FROM results ORDER BY ...
```

### Problem 2: Falsche Foreign Key JOINs
**Fehler**: `no such column`
**Lösung**: Explizite FK-Chain folgen
```
core_record → employment_and_income → expenses_and_assets 
→ bank_and_transactions → credit_and_compliance
```

### Problem 3: JSON Pfade aus falschen Tabellen
**Fehler**: 0 Zeilen returned
**Lösung**: Spalten-Meanings konsultieren
- ✅ `bank_and_transactions.chaninvdatablock`
- ❌ `core_record.chaninvdatablock`

### Problem 4: Mehrdeutige Fragen
**Fehler**: Falsch interpretierte SQL
**Lösung**: Ambiguity Detection aktiviert - System fragt nach

### Problem 5: Token-Kosten
**Issue**: Vollständiges Schema (~32 KB pro Request)
**Lösung**: BSL-first Architektur (explizite Regeln, deterministisch)

## 🔒 Sicherheit

### Defense-in-Depth Strategie

**Layer 1: SQL Guard (Regex)**
- Nur SELECT/WITH erlaubt
- Keine INSERT, UPDATE, DELETE, DROP, ALTER
- Max 1 Statement pro Request

**Layer 2: LLM Validation**
- Syntax-Check
- JOIN-Validierung
- JSON-Pfad-Prüfung

**Layer 3: Datenbank Permissions**
- Read-Only Benutzer
- Keine DDL-Operationen
- Connection Pooling mit Limits

**Ergebnis**: Injection-Erfolgsrate < 0.1%

## 🎨 Features

### Kernfeatures
- ✅ Natural Language to SQL
- ✅ Ambiguity Detection & Clarification Questions
- ✅ Multi-table JOIN Support
- ✅ JSON/JSONB Extraction
- ✅ Aggregation & GROUP BY
- ✅ Complex Filtering & WHERE Clauses
- ✅ UNION ALL mit Grand Totals
- ✅ Pagination für große Ergebnismengen

### Advanced Features
- ✅ BSL-first Architektur (Business Semantics Layer)
- ✅ Explizite Business Rules (Identity System, Aggregation Patterns)
- ✅ Self-Correction Loop
- ✅ Query Sessions für Determinismus
- ✅ Smart Defaults für vage Begriffe
- ✅ Result Caching
- ✅ Detailed Logging & Monitoring

## 📚 Architektur-Entscheidungen (ADRs)

### ADR-1: FastAPI statt Express.js
**Entscheidung**: Python + FastAPI für Backend
**Gründe**:
- Bessere LLM-Integration (Pandas, NumPy)
- Asynchrone Request-Handling
- Built-in OpenAPI Dokumentation
- Einfacheres Dependency Injection

### ADR-2: BSL-first statt RAG
**Entscheidung**: Business Semantics Layer (BSL) für explizite Business Rules
**Gründe**:
- Deterministische SQL-Generierung (reproduzierbar)
- Nachvollziehbare Business Rules (auditierbar)
- Einfacher zu warten (Plain-Text statt Vector Store)
- Scope-Fit: Single-DB (Credit-DB) statt Multi-DB
- Professor-Feedback: "BSL ist ein guter Ansatz"

### ADR-3: Query Sessions statt Caching
**Entscheidung**: UUID-basierte Sessions für Paging
**Gründe**:
- Deterministische Results
- Konsistente Pagination
- Sicherere Session-Verwaltung

## 🚀 Deployment

### Docker
```bash
# Stelle sicher, dass backend/.env einen OPENAI_API_KEY enthält.
docker compose up --build
```

Frontend: http://localhost:5173
Backend: http://localhost:8000

## 📖 Dokumentation

- **[Architecture](./docs/ARCHITEKTUR_UND_PROZESSE.md)** - Detaillierte Systemarchitektur

## 🧑‍💼 Team

- **Tim Kühne** - Project Lead, Backend Architecture
- **Dominik Ruoff** - LLM Integration, Database
- **Joel Martinez** - Frontend, UX/UI
- **Umut Polat** - Prompting, SQL Optimization
- **Sören Frank** - DevOps, Testing, Documentation

## 📅 Projektmanagement

- **Größe**: 5 Studiererende
- **Dauer**: ~3 Monate
- **Methodik**: Agile/Scrum mit 2-Wochen Sprints
- **Tools**: GitHub Projects, Kanban Board

## 🎓 Learnings & Reflexion

### Was lief gut?
- ✅ Agile Entwicklung mit schnellen Iterationen
- ✅ Parallele Frontend/Backend Entwicklung
- ✅ Frühe Problem-Identifikation (Ambiguity, Security)
- ✅ Kontinuierliche Optimierung (Kosten, Performance)
- ✅ Reviews und Entscheidungen

### Herausforderungen
- ⚠️ LLM-Halluzinationen waren schwer zu debuggen
- ⚠️ Foreign Key Chains erforderten explizite Dokumentation
- ⚠️ JSON-Pfade verursachten Silent Failures
- ⚠️ Migration von RAG/ReAct zu BSL-first (Architektur-Entscheidung)
- ⚠️ BSL-Regeln müssen explizit dokumentiert werden
- ⚠️ Kontinuierlicher Self-Correction-Loop


### Nächste Schritte
- Unterstützung für Multi-Database Queries
- Fine-Tuning auf BIRD-Datensatz
- Integration Open-Source-LLMs (Llama, Qwen)
- Automatisierte Schema-Generierung
- Advanced Caching Strategies

## 📄 Lizenz

Dieses Projekt dient ausschließlich zu Studienzwecken an der DHBW Stuttgart.

**Letztes Update**: January 2026  
**Status**: In aktiver Entwicklung  
**Version**: 5.0.0