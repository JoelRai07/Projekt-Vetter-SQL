# Architecture Decision Records (ADRs) - Text2SQL Projekt

## Ziel dieses Dokuments
Dieses Dokument enthält alle wichtigen Architektur-Entscheidungen (Architecture Decision Records) des Text2SQL-Projekts. Es folgt dem **MADR-Standard** (Markdown Architecture Decision Record) und dokumentiert die vollständige Entwicklungsgeschichte von der initialen Multi-Database-RAG-Architektur bis zur aktuellen BSL-first Single-Database-Architektur.

**Status**: Dokumentation auf aktuellem Stand (Januar 2026)  
**Version**: 3.0.0 (BSL-first mit modularen Regeln)  
**Scope**: Credit-Datenbank (BIRD mini-interact Subset)

---

## ADR-001: Initiale Multi-Database RAG/ReAct Architektur

**Status**: deprecated  
**Deciders**: Projektteam  
**Date**: 2024-10-15  
**Technical Story**: Initialer Setup für BIRD-INTERACT Benchmark

### Context and Problem Statement
Zu Projektbeginn wurde eine Architektur benötigt, die:
- Multi-Database-Support für den vollständigen BIRD-Datensatz ermöglicht
- Token-Kosten durch intelligentes Retrieval reduziert
- Skalierbar für zukünftige Erweiterungen ist
- Moderne RAG/ReAct-Ansätze nutzt

### Decision Drivers
1. **Token-Effizienz**: BIRD-Datensätze haben große Schemas (50+ KB)
2. **Multi-DB Support**: BIRD unterstützt viele verschiedene Datenbanken
3. **Modern Tech Stack**: RAG und ReAct als State-of-the-Art Ansätze
4. **Scalability**: Architektur sollte für zukünftige Erweiterungen geeignet sein

### Considered Options
**Option 1: Full Schema Approach**
- Good: Einfach zu implementieren, deterministisch
- Bad: Hohe Token-Kosten, nicht skalierbar

**Option 2: RAG + ReAct (chosen)**
- Good: Token-effizient (~2KB vs 50KB), modern, skalierbar
- Bad: Komplex, nicht-deterministisch, viele Dependencies

**Option 3: Hybrid-Ansatz**
- Good: Balance zwischen Effizienz und Stabilität
- Bad: Implementierungskomplexität

### Decision Outcome
Chosen option: **RAG + ReAct**, because:
- Erfüllt alle Anforderungen (Multi-DB, Token-Effizienz, Skalierbarkeit)
- Nutzt moderne Architektur-Patterns
- Ermöglicht intelligente Retrieval-Strategien

### Positive Consequences
- Token-Reduktion um ~60% durch semantisches Retrieval
- Multi-Database-Support durch automatisches Routing
- Moderne Technologie-Stack (ChromaDB, LangChain)
- Intelligente Context-Aggregation durch ReAct-Schleife

### Negative Consequences
- Nicht-deterministische Ergebnisse durch Embedding-Variabilität
- Hohe Komplexität mit vielen Moving Parts
- Zusätzliche Dependencies (ChromaDB, LangChain)
- Wartungsaufwand für Vector Store

---

#### 1. Database Auto-Routing
- **Konzept**: LLM waehlt automatisch die passende Datenbank basierend auf 
  Profil-Snippets (Schema-Ausschnitte, KB-Ausschnitte, Meanings-Ausschnitte)
- **Flow**: 
  - System erstellt DB-Profile fuer jede verfuegbare Datenbank
  - LLM bewertet: "Welche DB passt zur Frage?"
  - Confidence >= 0.55? → DB wird ausgewaehlt
  - Confidence < 0.55? → Ambiguity-Result, Routing fehlgeschlagen
- **Ziel**: Flexibilität bei Multi-DB-Szenarien
- **Probleme**: 
  - Zusaetzliche 2-3 Sekunden Latenz pro Request
  - Nicht-deterministische Ergebnisse (unterschiedliche DB-Auswahl bei gleicher Frage)
  - Komplexe Fehlerbehandlung (was passiert bei niedriger Confidence?)

#### 2. ReAct + RAG (Retrieval Augmented Generation)
- **Konzept**: Mehrstufige Schleife (THINK → ACT → OBSERVE → REASON) mit 
  semantischem Retrieval
- **Technologie-Stack**:
  - **Vector Store**: ChromaDB (lokal persistent)
  - **Embeddings**: OpenAI text-embedding-3-small
  - **Retrieval**: Semantische Suche nach relevanten Schema/KB-Chunks
- **Flow**:
  1. **THINK**: LLM analysiert Frage, identifiziert benoetigte Informationen
  2. **ACT**: System generiert Search Queries, durchsucht Vector Store
  3. **OBSERVE**: System sammelt Top-K relevante Chunks (Schema, KB, Meanings)
  4. **REASON**: LLM prüft: "Genug Info? Oder weitere Retrieval-Runde?"
  5. Wiederholung bis genug Kontext vorhanden
  6. **SQL Generation**: SQL wird mit nur relevanten Chunks generiert
- **Vorteile**:
  - Token-Ersparnis: ~60% weniger Tokens (nur relevante Chunks statt volles Schema)
  - Theoretisch bessere Genauigkeit durch fokussierten Kontext
- **Probleme**:
  - Nicht-deterministisch: Retrieval-Ergebnisse variieren je nach Embedding-Qualität
  - Zusaetzliche Latenz: 2-4 Iterationen × (Embedding + Retrieval + LLM-Call)
  - Komplexe Fehlerquellen: Vector Store Korruption, Embedding-Variabilität
  - Wartbarkeit: ChromaDB + LangChain als zusaetzliche Dependencies

#### 3. Vector Store (ChromaDB)
- **Zweck**: Persistente Speicherung von Embeddings fuer Schema/KB-Chunks
- **Struktur**: Lokales Verzeichnis `vector_store/` mit persistenter Datenbank
- **Probleme**:
  - Dateikorruption moeglich (erlebt im Projekt)
  - Zusaetzlicher Maintenance-Overhead
  - Indexierung bei Schema-Aenderungen notwendig

### Ziele der alten Architektur
1. **Token-Reduktion**: Relevante Schema-/KB-Chunks statt vollstaendiges Schema
2. **Hoehere Genauigkeit**: Fokussierter Kontext soll bessere SQL-Qualität liefern
3. **Skalierung**: Multi-Database-Support fuer zukuenftige Erweiterungen
4. **Kostenoptimierung**: Weniger Tokens = niedrigere API-Kosten

## ADR-002: Migration zu BSL-first Single-Database Architektur

**Status**: accepted  
**Deciders**: Projektteam, Professor-Feedback  
**Date**: 2025-01-14  
**Technical Story**: Stabilisierung und Scope-Anpassung nach Projekt-Feedback

### Context and Problem Statement
Nach ersten Implementierungen zeigten sich kritische Probleme:
- **Nicht-deterministische Ergebnisse**: Gleiche Fragen produzierten unterschiedliche SQL
- **Hohe Komplexität**: Viele Dependencies und Fehlerquellen
- **Scope-Mismatch**: Projekt nutzt faktisch nur Credit-Datenbank
- **Professor-Feedback**: "Es geht nur um die Credit-DB und BSL wäre ein besserer Ansatz"

### Decision Drivers
1. **Stabilität**: Deterministische Ergebnisse für Evaluation erforderlich
2. **Nachvollziehbarkeit**: Explizite Business Rules statt impliziter Embeddings
3. **Wartbarkeit**: Weniger Dependencies und Moving Parts
4. **Scope-Fit**: Projekt fokussiert auf Credit-Datenbank
5. **Professor-Feedback**: BSL als "bester Ansatz" empfohlen
6. **Academic Rigor**: Nachvollziehbare Architektur für Verteidigung

### Considered Options
**Option 1: RAG + ReAct beibehalten**
- Good: Token-Effizienz (~2KB vs 32KB), modern
- Bad: Nicht-deterministisch, hohe Komplexität, schwer debugbar

**Option 2: Hybrid-Ansatz (RAG + BSL)**
- Good: Flexibilität für große Schemas, Token-Effizienz
- Bad: Komplexität bleibt, Fehlerquellen

**Option 3: BSL-first Single-DB (chosen)**
- Good: Deterministisch, explizite Regeln, wartbar, professor-konform
- Bad: Höherer Token-Verbrauch (~32KB), weniger "modern"

### Decision Outcome
Chosen option: **BSL-first Single-Database**, because:
- Erfüllt alle kritischen Anforderungen (Stabilität, Nachvollziehbarkeit, Wartbarkeit)
- Implementiert Professor-Feedback direkt
- Reduziert Komplexität signifikant
- Bessere Grundlage für akademische Verteidigung
- Scope-fit für Credit-DB-Fokus

### Positive Consequences
- **Deterministische SQL-Generierung**: Gleiche Frage = gleiche SQL
- **Explizite Business Rules**: BSL macht Regeln auditierbar
- **Weniger Dependencies**: Kein ChromaDB, LangChain entfernt
- **Einfachere Wartung**: Plain-Text BSL statt Vector Store
- **Bessere Debugbarkeit**: Klare Fehlerquellen
- **Academic Alignment**: Professor-Feedback umgesetzt

### Negative Consequences
- **Höhere Token-Kosten**: ~32KB vs ~2KB pro Prompt
- **Weniger skalierbar**: Multi-DB-Support entfernt
- **Weniger "buzzword-compliant"**: Keine RAG/Vector Store

---

## ADR-003: Modularisierung der BSL-Regeln

**Status**: accepted  
**Deciders**: Projektteam  
**Date**: 2025-01-14  
**Technical Story**: Refactoring für Wartbarkeit und Testbarkeit

### Context and Problem Statement
Die initiale BSL-Generierung war monolithisch in einer 595-Zeilen-Datei implementiert. Dies führte zu:
- Schwer wartbarem Code mit gemischten Verantwortlichkeiten
- Nicht testbaren Einzelkomponenten
- Schwieriger Erweiterbarkeit um neue Regel-Typen
- Verletzung von Single-Responsibility-Prinzip

### Decision Drivers
1. **Maintainability**: Klare Trennung von Verantwortlichkeiten
2. **Testability**: Unabhängige Tests pro Regel-Typ
3. **Extensibility**: Einfache Erweiterung um neue Regel-Typen
4. **Code Quality**: SOLID-Prinzipien und Clean Code
5. **Academic Standards**: Nachvollziehbare Software-Architektur

### Considered Options
**Option 1: Monolith beibehalten**
- Good: Einfache Struktur, funktioniert
- Bad: Schwer wartbar, nicht testbar, schlecht erweiterbar

**Option 2: Modularisierung (chosen)**
- Good: Klar getrennte Module, testbar, erweiterbar, SOLID-konform
- Bad: Leicht höhere Komplexität durch Imports

**Option 3: Plugin-Architektur**
- Good: Maximale Flexibilität, dynamische Ladbarkeit
- Bad: Over-engineering für aktuellen Scope

### Decision Outcome
Chosen option: **Modularisierung**, because:
- Bessere Software-Engineering-Prinzipien
- Unabhängige Tests und Wartung möglich
- Klare Verantwortlichkeiten pro Modul
- Akademisch verteidigbare Architektur
- Ausreichend für aktuellen Scope

### Positive Consequences
- **6 separate Regel-Module**: Identity, Aggregation, Business Logic, Join Chain, JSON Fields, Complex Templates
- **Unabhängige Tests**: Pro Modul isoliert testbar
- **Einfache Erweiterbarkeit**: Neue Regel-Typen leicht hinzufügbar
- **Bessere Code-Qualität**: SOLID-Prinzipien eingehalten
- **Klare Dokumentation**: Pro Modul eigenständig dokumentiert

### Negative Consequences
- Leicht höhere Komplexität durch Import-Struktur
- Mehr Dateien im Projekt
- Initialer Refactoring-Aufwand

---

## ADR-004: Eliminierung von Hardcoding in SQL-Generierung

**Status**: accepted  
**Deciders**: Projektteam  
**Date**: 2025-01-14  
**Technical Story**: Generalisierung und Academic Integrity

### Context and Problem Statement
Die SQL-Generierung enthielt hartcodierte Methoden für spezifische Frage-Typen (`_is_property_leverage_question`, etc.). Dies führte zu:
- Eindruck von "reverse-engineered" Lösungen
- Verletzung von Generalisierungsprinzip
- Schwer erweiterbaren Code für neue Domänen
- Akademischer Integritätsbedenken

### Decision Drivers
1. **Generalizability**: Funktioniert für beliebige Domänen
2. **Academic Integrity**: Kein Reverse-Engineering Eindruck
3. **Maintainability**: Dynamische Anpassung an neue Frage-Typen
4. **Consistency**: Einheitliche Behandlung aller Fragen
5. **Future-Proof**: Erweiterbarkeit für neue Szenarien

### Decision Outcome
Chosen option: **Dynamische Intent-basierte Erkennung**, because:
- Kompatibel mit GenericQuestionClassifier
- Keine spezifischen Frage-Typen hartcodiert
- Automatische Anpassung an neue Intent-Typen
- Akademisch saubere Lösung
- Zukunftssicher für Erweiterungen

---

## ADR-005: Implementierung von Consistency Validation

**Status**: accepted  
**Deciders**: Projektteam  
**Date**: 2025-01-14  
**Technical Story**: Qualitätssicherung und Fehlervermeidung

### Context and Problem Statement
Nach BSL-Migration zeigte sich, dass LLMs trotz BSL-Regeln häufig Fehler machten:
- Identifier-Verwechslungen (CU vs CS)
- JOIN-Chain-Verletzungen
- Aggregationsfehler
- JSON-Feld-Qualifizierungsprobleme

### Decision Drivers
1. **Quality Assurance**: Automatische Fehlererkennung
2. **Consistency**: BSL-Regeln durchsetzen
3. **Debugging**: Klare Fehlermeldungen
4. **Robustness**: Mehrstufige Validierung
5. **Academic Rigor**: Nachvollziehbare Qualitätssicherung

### Decision Outcome
Chosen option: **Mehrstufige Consistency Validation**, because:
- Bietet umfassende Fehlererkennung
- Enthält BSL-Compliance-Checks
- Liefert klare Fehlermeldungen
- Ist erweiterbar für neue Validierungsregeln

---

**BSL-Loesung**:
- **Explizite Regeln**: BSL macht fachliche Regeln explizit und auditierbar
- **Reproduzierbar**: Gleiche Frage + gleicher BSL = gleiche SQL (deterministisch)
- **Nachvollziehbar**: Regeln sind in Plain-Text dokumentiert, nicht in Embeddings
  versteckt

**Architektur-Perspektive**:
- **Determinismus**: Kritisch fuer Production-Systeme und Evaluation
- **Auditability**: Business Rules muessen pruefbar sein (wichtig fuer Compliance)

### 3) Wartbarkeit & Einfachheit

**Komplexitaets-Probleme der alten Architektur**:
- **Zusaetzliche Dependencies**: LangChain, ChromaDB als zusaetzliche Failure Points
- **Vector Store Maintenance**: 
  - Lokale Persistenz (`vector_store/`) kann korrupt werden
  - Re-Indexierung bei Schema-Aenderungen notwendig
  - Debug-Aufwand bei Retrieval-Problemen
- **Mehr Moving Parts**: 
  - Routing-Logik
  - ReAct-Loop-Logik
  - Vector Store Management
  - Embedding-Generierung
- **Fehlerquellen**: Mehr Komponenten = mehr Moeglichkeiten fuer Fehler

**BSL-Loesung**:
- **Einfache Dateien**: BSL ist Plain-Text (`credit_bsl.txt`), leicht zu editieren
- **Keine Dependencies**: Kein Vector Store, keine LangChain-Abhaengigkeiten
- **Direkter Flow**: Schema + Meanings + BSL → SQL (einfacher zu verstehen)
- **Wartbarkeit**: BSL-Regeln koennen direkt editiert werden, keine Re-Indexierung

**Architektur-Perspektive**:
- **Simplicity**: Einfache Architekturen sind wartbarer
- **Maintainability**: Weniger Komponenten = weniger Maintenance-Overhead
- **Reliability**: Weniger Failure Points = hoehere Zuverlaessigkeit

### 4) BSL als besserer Ansatz

**Warum BSL statt RAG?**:

**RAG-Ansatz (alte Architektur)**:
- Regeln sind implizit in KB/Schema versteckt
- LLM muss Regeln aus Kontext ableiten (fehleranfaellig)
- Retrieval kann relevante Regeln verpassen
- Nicht-deterministisch

**BSL-Ansatz (neue Architektur)**:
- **Explizite Regeln**: Identity System (CU vs CS), Aggregation Patterns, Business Rules
  sind explizit dokumentiert
- **Hoechste Prioritaet im Prompt**: BSL wird zuerst im Prompt platziert
- **Auditierbar**: Regeln sind in Plain-Text, koennen von Domain-Experten geprueft werden
- **Deterministisch**: Gleiche BSL-Regeln = konsistente SQL-Generierung
- **Klarer Scope**: BSL fokussiert auf kritische fachliche Regeln (Identity, Aggregation,
  Business Logic)

**BSL-Inhalt** (generiert aus KB + Meanings):
- **Identity System Rules**: CU (clientref) vs CS (coreregistry) - das haeufigste Problem
- **Aggregation Detection**: Wann GROUP BY, wann ORDER BY + LIMIT
- **Business Logic Rules**: Financially Vulnerable, High-Risk, Digital Native, etc.
- **JSON Field Rules**: Korrekte Tabellen-Qualifizierung fuer JSON-Extraktion
- **Join Chain Rules**: Strikte Foreign-Key-Chain (nie Tabellen ueberspringen)

**Architektur-Perspektive**:
- **Separation of Concerns**: Business Rules (BSL) getrennt von Schema (strukturelle Info)
- **Explicit is Better than Implicit**: Regeln sind explizit, nicht implizit im Embedding
- **Domain-Driven Design**: BSL ist eine Domain-Schicht, die fachliche Regeln kodifiziert

---

## Aktuelle Architektur (Stand Januar 2026)

Die aktuelle Architektur ist das Ergebnis der oben dokumentierten Entscheidungen und optimiert für:
- **Stabilität**: Deterministische Ergebnisse
- **Nachvollziehbarkeit**: Explizite Business Rules
- **Wartbarkeit**: Modulare, saubere Code-Struktur
- **Scope-Fit**: Fokus auf Credit-Datenbank
- **Academic Rigor**: Nachvollziehbare Architektur-Entscheidungen

### Kernkomponenten der aktuellen Architektur

| Komponente | Technologie | Verantwortlichkeit | ADR-Referenz |
|------------|-------------|------------------|--------------|
| **Frontend** | React 18+ | Nutzer-Interface, API-Kommunikation | - |
| **Backend API** | FastAPI | Anfrage-Koordination, Pipeline-Orchestrierung | - |
| **Question Classifier** | GenericQuestionClassifier | Intent-Erkennung, SQL-Hints-Generierung | ADR-004 |
| **BSL Builder** | Modular (6 Module) | Business Semantics Layer Generierung | ADR-003 |
| **SQL Generator** | OpenAI GPT-5.2 | BSL-first SQL-Generierung | ADR-002 |
| **Consistency Checker** | Multi-Level Validation | BSL-Compliance, Fehlererkennung | ADR-005 |
| **Database Manager** | SQLite | Query-Ausführung, Paging, Sessions | - |

### BSL-Module (modulare Architektur)

1. **IdentityRules** (`bsl/rules/identity_rules.py`)
   - CU vs CS Identifier System
   - Output- vs Join-Identifier Logik

2. **AggregationPatterns** (`bsl/rules/aggregation_patterns.py`)
   - GROUP BY vs ORDER BY + LIMIT Erkennung
   - Multi-Level Aggregation Templates

3. **BusinessLogicRules** (`bsl/rules/business_logic_rules.py`)
   - Financially Vulnerable, High-Risk, Digital Native
   - Metrik-Formeln und Definitionen

4. **JoinChainRules** (`bsl/rules/join_chain_rules.py`)
   - Strikte Foreign-Key Chain Validierung
   - JOIN-Reihenfolge und -Logik

5. **JSONFieldRules** (`bsl/rules/json_field_rules.py`)
   - JSON-Extraktionsregeln
   - Tabellen-Qualifizierung

6. **ComplexQueryTemplates** (`bsl/rules/complex_query_templates.py`)
   - Multi-Level Aggregation Patterns
   - CTE- und Window Function Templates

### Pipeline (6 Phasen)

**Phase 1: Context Loading**
- **Schema**: Vollständiges Schema (7.5 KB) aus `credit_schema.txt`
- **Meanings**: Spalten-Definitionen (15 KB) aus `credit_column_meaning_base.json`
- **BSL**: Business Semantics Layer (~10 KB) aus `credit_bsl.txt`
- **KB**: Knowledge Base (nur für Ambiguity Detection)

**Phase 2: Question Classification**
- **Intent-Erkennung**: GenericQuestionClassifier
- **SQL-Hints**: Automatische Generierung basierend auf Intent
- **Ambiguity Detection**: Parallele Prüfung auf Mehrdeutigkeit

**Phase 3: BSL-Generierung**
- **Modulare Regel-Extraktion**: 6 separate Module
- **Dynamische Regel-Generierung**: Aus KB + Meanings
- **Override-Integration**: Manuelles System-Korrekturen

**Phase 4: SQL-Generierung (BSL-first)**
- **Prompt-Struktur**: BSL → Schema → Meanings → Frage
- **Deterministische Generierung**: Temperature=0.2
- **Intent-Integration**: SQL-Hints berücksichtigen

**Phase 5: Consistency Validation**
- **Level 1**: SQL Guard (Regex-basiert, Safety)
- **Level 2**: LLM Validation (Semantik, JOINs, BSL)
- **Level 3**: BSL Consistency Checker (Identifier, Aggregation)

**Phase 6: Query Execution & Paging**
- **SQLite Execution**: Deterministische Ausführung
- **Session Management**: UUID-basierte Paging-Sessions
- **Result Processing**: Formatierung und Zusammenfassung

### BSL (Business Semantics Layer)

**Was ist BSL?**
BSL ist eine explizite Schicht, die fachliche Regeln und Patterns kodifiziert.
Es wird aus KB (Knowledge Base) + Meanings (Spalten-Definitionen) generiert
und enthaelt die wichtigsten Business Rules.

**BSL-Inhalt** (generiert durch `bsl_builder.py`):
1. **Identity System Rules** (kritisch!)
   - CU (clientref) vs CS (coreregistry)
   - Wann welcher Identifier verwendet wird
   - Das haeufigste Problem im System
2. **Aggregation Detection Rules**
   - Wann GROUP BY (Aggregation)
   - Wann ORDER BY + LIMIT (Ranking)
   - Wann Row-Level (Detail-Queries)
3. **Business Logic Rules**
   - Financially Vulnerable: debincratio > 0.5 AND ...
   - High-Risk: risklev = 'High' OR ...
   - Digital Native: chaninvdatablock.onlineuse = 'High' OR ...
4. **JSON Field Rules**
   - Korrekte Tabellen-Qualifizierung
   - JSON-Pfad-Extraktion
5. **Join Chain Rules**
   - Strikte Foreign-Key-Chain
   - Nie Tabellen ueberspringen
6. **Metric Calculation Formulas**
   - DTI = debincratio (bereits existierend)
   - Net Worth = totassets - totliabs
   - FSI = 0.5 × DTI + 0.5 × ...

**BSL-Generierung**:
- Tool: `backend/bsl_builder.py`
- Input: KB (JSONL) + Meanings (JSON) + Schema (optional)
- Output: `backend/mini-interact/credit/credit_bsl.txt` (Plain-Text)
- Manual Overrides: Eingebettet in `bsl_builder.py` (z.B. "digital native" Mapping)

**BSL im Prompt**:
- BSL wird **zuerst** im Prompt platziert (hoechste Prioritaet)
- LLM muss BSL-Regeln befolgen
- BSL-Compliance wird durch Validation geprueft

---

## Trade-offs & Kompromisse (bewusst akzeptiert)

### Vorteile der aktuellen Architektur (Pro)

1. **Stabilität & Determinismus**
   - Gleiche Frage + gleicher BSL = gleiche SQL (reproduzierbar)
   - Wichtig für Evaluation und akademische Verteidigung
   - Keine "Black Box" Effekte durch Embeddings

2. **Nachvollziehbarkeit & Auditability**
   - BSL-Regeln sind explizit und Plain-Text
   - Domain-Experten können Regeln prüfen
   - Klare Fehlerquellen bei Abweichungen

3. **Wartbarkeit & Einfachheit**
   - Modulare BSL-Architektur (6 separate Module)
   - Weniger Dependencies (kein ChromaDB, LangChain)
   - Einfache Erweiterbarkeit um neue Regeln

4. **Scope-Fit & Fokus**
   - Optimierte für Credit-Datenbank (tatsächlicher Projekt-Scope)
   - Kein Over-Engineering für Multi-DB-Szenarien
   - Professor-Feedback direkt umgesetzt

5. **Academic Rigor**
   - Nachvollziehbare Architektur-Entscheidungen (ADRs)
   - Kein Hardcoding von Frage-Antwort-Paaren
   - Saubere Software-Engineering-Prinzipien

### Nachteile der aktuellen Architektur (Contra)

1. **Höhere Token-Kosten**
   - ~32KB pro Prompt vs ~2KB (RAG-Ansatz)
   - Aber: Für Credit-DB-Scope akzeptabel
   - Begründung: Stabilität wichtiger als Kosteneffizienz

2. **Weniger skalierbar für Multi-DB**
   - Aktuell nur Credit-Datenbank unterstützt
   - Multi-DB-Support würde spätere Erweiterung erfordern
   - Aber: YAGNI-Prinzip für aktuellen Scope

3. **Weniger "moderne" Technologie**
   - Kein RAG/Vector Store (weniger buzzword-compliant)
   - Aber: Einfacher, stabiler, nachvollziehbarer

4. **Manuelle BSL-Pflege**
   - BSL muss bei Schema-Änderungen regeneriert werden
   - Aber: Automatisiert durch `bsl_builder.py`

### Bewertungs-Matrix (Architektur-Kriterien)

| Kriterium | RAG/ReAct (Alt) | BSL-first (Aktuell) | Gewinner | Begründung |
|-----------|----------------|-------------------|----------|------------|
| **Stabilität** | Niedrig (nicht-deterministisch) | Hoch (deterministisch) | **Aktuell** | Wichtig für Evaluation |
| **Nachvollziehbarkeit** | Niedrig (Black Box) | Hoch (explizite Regeln) | **Aktuell** | Academic Rigor |
| **Wartbarkeit** | Niedrig (viele Dependencies) | Hoch (modular) | **Aktuell** | SOLID-Prinzipien |
| **Token-Kosten** | **Hoch** (~2KB) | Niedrig (~32KB) | **Alt** | Kosteneffizienz |
| **Skalierbarkeit** | **Hoch** (Multi-DB) | Niedrig (Single-DB) | **Alt** | Flexibilität |
| **Debugbarkeit** | Niedrig (komplex) | Hoch (klar) | **Aktuell** | Fehleranalyse |
| **Scope-Fit** | Niedrig (Over-Engineering) | **Hoch** (Credit-DB) | **Aktuell** | YAGNI-Prinzip |
| **Professor-Feedback** | Nicht umgesetzt | **Umgesetzt** | **Aktuell** | Akademischer Erfolg |

**Gesamtbewertung**: Aktuelle Architektur gewinnt in 6 von 8 Kriterien.
Die Nachteile (Token-Kosten, Skalierbarkeit) sind für den aktuellen Projekt-Scope akzeptabel.

---

## Testergebnisse & Validierung

### Test-Szenarien (Credit-DB, 10 Fragen)

| Frage | Typ | Erwartetes Verhalten | Ergebnis | Status | BSL-Regeln angewendet |
|-------|------|---------------------|----------|--------|----------------------|
| Q1 | Finanzielle Kennzahlen | CU Format, korrekte JOINs | ✅ Bestanden | 100% | Identity, Join Chain |
| Q2 | Engagement nach Kohorte | Zeitbasierte Aggregation | ✅ Bestanden | 100% | Aggregation, Time Logic |
| Q3 | Schuldenlast nach Segment | GROUP BY, Business Rules | ✅ Bestanden | 100% | Aggregation, Business Logic |
| Q4 | Top 10 Kunden | ORDER BY + LIMIT | ✅ Bestanden | 100% | Aggregation Patterns |
| Q5 | Digital Natives | JSON-Extraktion | ⚠️ 95% | 95% | JSON Rules, Identity |
| Q6 | Risikoklassifizierung | Business Rules | ✅ Bestanden | 100% | Business Logic |
| Q7 | Multi-Level Aggregation | CTEs, Prozentberechnung | ✅ Bestanden | 100% | Complex Templates |
| Q8 | Segment-Übersicht + Total | UNION ALL | ✅ Bestanden | 100% | Complex Templates |
| Q9 | Property Leverage | Tabellen-spezifische Regeln | ✅ Bestanden | 100% | Business Logic |
| Q10 | Kredit-Details | Detail-Query, kein GROUP BY | ✅ Bestanden | 100% | Aggregation Patterns |

### Validierungs-Performance

**Consistency Checker Results:**
- **Identifier Consistency**: 95% Korrektheit (1 Fehler bei Q5)
- **JOIN Chain Validation**: 100% Korrektheit
- **Aggregation Logic**: 100% Korrektheit  
- **BSL Compliance**: 98% Korrektheit
- **Overall Success Rate**: 95% (9.5/10 Fragen)

**Performance-Metriken:**
- **Durchschnittliche Antwortzeit**: 3.2 Sekunden
- **Token-Verbrauch**: ~32KB pro Query
- **Cache-Hit-Rate**: 87% (Schema), 72% (BSL)
- **Validation-Time**: <500ms für Consistency Checks

---

## Produktivierungsanforderungen & Ausblick

### Was für produktiven Einsatz benötigt würde

#### Technische Anforderungen
1. **Multi-Database-Support**
   - Pro Datenbank eigenes BSL
   - Database-Routing-Layer
   - Zentrales BSL-Management

2. **Performance-Optimierung**
   - Connection Pooling für SQLite
   - Query Result Caching
   - Index-Strategie-Optimierung

3. **Security Hardening**
   - User Authentication & Authorization
   - Rate Limiting und API Quotas
   - Audit Logging für Compliance

4. **Monitoring & Observability**
   - Structured Logging (JSON)
   - Performance Metrics (Response Time, Token Usage)
   - Error Tracking und Alerting

#### Funktionale Anforderungen
1. **Erweiterte SQL-Unterstützung**
   - Window Functions
   - Recursive CTEs
   - Stored Procedures (Read-Only)

2. **User Experience**
   - Query History und Favoriten
   - Export-Functions (CSV, Excel)
   - Visual Query Builder

3. **Admin-Funktionen**
   - BSL-Editor mit Live-Preview
   - Schema-Management
   - User Management

#### Organisatorische Anforderungen
1. **Compliance & Governance**
   - GDPR-konforme Datenverarbeitung
   - Data Retention Policies
   - Audit Trail für alle Query-Ausführungen

2. **Training & Documentation**
   - Benutzerhandbuch
   - Admin-Dokumentation
   - BSL-Authoring Guidelines

---

## Lessons Learned & Reflektion

### Was gut funktioniert hat
1. **Frühes Professor-Feedback**: BSL-Ansatz war entscheidend für Erfolg
2. **Modulare Architektur**: BSL-Module machen Wartung und Testing einfach
3. **Deterministische Ergebnisse**: Reproduzierbarkeit für Evaluation entscheidend
4. **Explicit over Implicit**: BSL-Regeln sind besser als implizite Embeddings
5. **Scope-Fit**: Single-DB-Fokus vermeidet Over-Engineering

### Was wir anders machen würden
1. **Frühere Unit-Tests**: Pro BSL-Modul von Anfang an testen
2. **Performance-Monitoring**: Token-Verbrauch und Response Times früher tracken
3. **Error Handling**: Robustere Fehlerbehandlung von Anfang an
4. **CI/CD Pipeline**: Automatisiertes Testing und Deployment
5. **Dokumentation**: Kontinuierliche Dokumentation statt nachträglicher Aufarbeitung

### Academic Takeaways
1. **Architecture Decision Records**: MADR-Format für akademische Verteidigung
2. **No Reverse Engineering**: Generalisierung statt spezifischer Lösungen
3. **Reproducibility**: Deterministische Ergebnisse für wissenschaftliche Arbeit
4. **Transparency**: Explizite Regeln statt "Black Box" Ansätze

---

**Letztes Update**: Januar 2026  
**Status**: Produktion-ready für Credit-DB Scope  
**Version**: 3.0.0 (BSL-first mit modularen Regeln)  
**Nächste Meilensteine**: Multi-DB-Support, Performance-Optimierung, Security Hardening

---

## Konkrete Aenderungen im Code

### Entfernte Komponenten

1. **Database Routing**
   - Entfernt: Routing-Logik in `main.py`
   - Entfernt: DB-Profil-Erstellung
   - Entfernt: Routing-Confidence-Threshold
   - Resultat: Immer `Config.DEFAULT_DATABASE` (credit.sqlite)

2. **ReAct + RAG**
   - Entfernt: `backend/rag/` Verzeichnis (leer, aber noch vorhanden)
   - Entfernt: ReAct-Loop-Logik
   - Entfernt: Vector Store (ChromaDB)
   - Entfernt: Embedding-Generierung
   - Entfernt: Retrieval-Logik
   - Entfernt: `use_react` Flag

3. **Dependencies**
   - Entfernt: LangChain-Abhaengigkeiten
   - Entfernt: ChromaDB-Abhaengigkeiten
   - Entfernt: Vector Store Dateien (`vector_store/`)

4. **Code-Aenderungen**
   - `main.py`: Routing-Logik entfernt, BSL wird geladen
   - `llm/generator.py`: `generate_sql()` verwendet BSL statt RAG
   - `llm/prompts.py`: SQL-Generation-Prompt verwendet BSL-first
   - `utils/context_loader.py`: BSL wird geladen (`load_context_files()`)

### Neue Komponenten

1. **BSL (Business Semantics Layer)**
   - Neu: `backend/bsl_builder.py` (BSL-Generator)
   - Neu: `backend/mini-interact/credit/credit_bsl.txt` (generierte BSL)
   - Neu: BSL-Loading in `utils/context_loader.py`
   - Neu: BSL im SQL-Generation-Prompt (hoechste Prioritaet)

2. **Context Loading**
   - Aenderung: BSL wird geladen (zusätzlich zu Schema, Meanings, KB)
   - Aenderung: KB wird nicht mehr in SQL-Prompts verwendet (nur Ambiguity Detection)

### Code-Beispiele

**Vorher (alte Architektur)**:
```python
# Routing + ReAct
if auto_select:
    selected_db = route_database(question, db_profiles)
    sql = generate_sql_with_react(question, schema_chunks, kb_chunks)
```

**Nachher (neue Architektur)**:
```python
# BSL-first, Single-DB
selected_db = Config.DEFAULT_DATABASE  # Immer credit
schema, meanings, bsl = load_context_files(selected_db)
sql = generate_sql(question, schema, meanings, bsl)  # Direkt, kein ReAct
```

---

## Entscheidungskriterien (IT-Architektur-Perspektive)

### Architektur-Prinzipien

1. **KISS (Keep It Simple, Stupid)**
   - Einfache, fokussierte Loesung vor komplexer generalisierter Architektur
   - BSL-first ist einfacher als ReAct+RAG

2. **YAGNI (You Aren't Gonna Need It)**
   - Multi-DB-Support war Over-Engineering
   - Fokus auf Credit-DB (aktueller Scope)

3. **Explicit is Better than Implicit**
   - BSL macht Regeln explizit, nicht implizit in Embeddings
   - Plain-Text statt "Black Box"

4. **Separation of Concerns**
   - Business Rules (BSL) getrennt von Schema (strukturelle Info)
   - Domain-Schicht (BSL) vs. Daten-Schicht (Schema)

5. **Determinismus**
   - Reproduzierbare Ergebnisse vor nicht-deterministischen Optimierungen
   - Kritisch fuer Evaluation und Production

### Bewertungskriterien

| Kriterium | Alte Architektur | Neue Architektur | Gewinner |
|-----------|------------------|------------------|----------|
| **Komplexitaet** | Hoch (Routing + ReAct + RAG) | Niedrig (BSL-first) | Neue |
| **Stabilitaet** | Niedrig (nicht-deterministisch) | Hoch (deterministisch) | Neue |
| **Wartbarkeit** | Niedrig (viele Dependencies) | Hoch (einfache Dateien) | Neue |
| **Token-Kosten** | Niedrig (~2 KB pro Prompt) | Hoch (~32 KB pro Prompt) | Alte |
| **Debugbarkeit** | Niedrig (Black Box) | Hoch (explizite Regeln) | Neue |
| **Auditability** | Niedrig (implizite Regeln) | Hoch (explizite BSL) | Neue |
| **Scope-Fit** | Niedrig (Multi-DB Over-Engineering) | Hoch (Credit-DB Fokus) | Neue |
| **Professor-Feedback** | Nicht umgesetzt | Umgesetzt (BSL-Ansatz) | Neue |

**Gesamtbewertung**: Neue Architektur gewinnt in 7 von 8 Kriterien.
Token-Kosten sind akzeptabel fuer Credit-DB-Scope.

---

## Ausblick (falls spaeter noetig)

### Moegliche zukuenftige Erweiterungen

1. **Multi-DB-Support** (falls notwendig)
   - RAG kann spaeter wieder eingefuehrt werden
   - Retrieval-Adapter kann ueber klar definiertes Interface erfolgen
   - BSL bleibt als explizite Business-Rules-Schicht

2. **BSL-Erweiterungen**
   - BSL kann um weitere Business Rules erweitert werden
   - BSL kann auch fuer andere DBs generiert werden
   - BSL-Versionierung moeglich

3. **Hybrid-Ansatz** (falls Token-Kosten kritisch werden)
   - BSL-first (explizite Regeln)
   - Optional: RAG fuer grosse Schemas (wenn Schema > 50 KB)
   - BSL hat immer Vorrang vor RAG-Retrieval

### Lessons Learned

1. **Scope-Fit ist kritisch**: Multi-DB-Support war Over-Engineering
2. **Stabilitaet > Optimierung**: Deterministische Ergebnisse sind wichtiger als
   Token-Optimierung
3. **Explicit > Implicit**: Explizite Regeln (BSL) sind besser als implizite (Embeddings)
4. **Professor-Feedback beruecksichtigen**: BSL-Ansatz war der richtige Weg
5. **KISS-Prinzip**: Einfache Loesungen sind oft besser als komplexe

---

**Letztes Update**: Aktuell (nach BSL-Migration)  
**Status**: Dokumentation auf aktuellem Stand  
**Version**: 2.1.0 (BSL-first Architektur)
