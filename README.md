# ChatWithYourData – Text2SQL Projekt 📌

Natürliche Sprache zu SQL-Abfragen mittels Large Language Models (LLMs). Dieses Projekt wurde im Rahmen des Moduls "Projekt" an der DHBW Stuttgart entwickelt.

## 🎯 Projektziele

- ✅ Funktionierender Text2SQL-Prototyp
- ✅ Moderne LLM-Integration (OpenAI/Claude)
- ✅ Robuste SQL-Generierung mit Ambiguity Detection
- ✅ Sichere Datenbankabfragen mit Defense-in-Depth
- ✅ Skalierbare Architektur mit RAG-Retrieval
- ✅ Benutzerfreundliche Fehlerbehandlung

## 🧠 Motivation

Daten sind das Gold des 21. Jahrhunderts – jedoch ist SQL für viele Mitarbeitende eine Hürde. Moderne KI-Modelle ermöglichen es, natürliche Sprache effizient zu interpretieren.

Mit diesem Projekt reduzieren wir die Distanz zwischen Mensch und Datenbank und machen **datengesteuerte Entscheidungen für alle zugänglich**.

## 🛠️ Technologie-Stack

### Backend
- **Python 3.11+** mit FastAPI
- **OpenAI API** GPT-5.2
- **SQLite** für Datenbankabfragen
- **ChromaDB + LangChain** für RAG-Retrieval
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
│  │ 2. SQL Generation (ReAct + RAG)                 │   │
│  │    → Retrieval-Augmented: Nur relevante Schema  │   │
│  │    → Few-Shot Prompting für Konsistenz          │   │
│  │    → Smart Defaults für vage Begriffe           │   │
│  │    → Temperature=0.2 für Determinismus          │   │
│  └─────────────────────────────────────────────────┘   │
│         │                    │                         │
│         ↓                    ↓                         │
│    ChromaDB            LLM (OpenAI)                    │
│    (Vector Store)      (GPT-4o-mini)                   │
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

### Problem 5: Token-Kosten zu hoch
**Issue**: 8150 Tokens pro Request
**Lösung**: ReAct + RAG Retrieval (-75% Tokens)

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
- ✅ ReAct-basiertes Retrieval (RAG)
- ✅ Few-Shot Prompting
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

### ADR-2: ChromaDB für RAG
**Entscheidung**: Vector-Store für Schema/KB Retrieval
**Gründe**:
- Token-Reduktion
- Bessere Relevanz
- Kostenersparnis

### ADR-3: Query Sessions statt Caching
**Entscheidung**: UUID-basierte Sessions für Paging
**Gründe**:
- Deterministische Results
- Konsistente Pagination
- Sicherere Session-Verwaltung

## 🚀 Deployment

### Docker
```bash
docker-compose up -d
```

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
- ⚠️ Token-Kosten stiegen schnell (vor ReAct-Optimierung)
- ⚠️ Beschädigte Dateien aus dem ChromaDB-Vektor-Store
- ⚠️ Kontinuirlicher Self-Correction-Loop


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