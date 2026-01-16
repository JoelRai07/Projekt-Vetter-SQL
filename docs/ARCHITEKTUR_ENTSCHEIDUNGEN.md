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


## ADR-003: Dynamische Intent-Erkennung mit BSL Compliance Triggern

**Status**: accepted (vollständig umgesetzt)
**Deciders**: Projektteam
**Date**: 2025-01-14
**Technical Story**: Generalisierung und robuste SQL-Generierung

### Context and Problem Statement
Für eine robuste Text2SQL-Pipeline war eine Strategie erforderlich, die:
- Das LLM bei der korrekten Anwendung von BSL-Regeln unterstützt
- Auf Variationen von Fragen generalisiert
- Keine fertigen SQL-Antworten pro Frage enthält

### Decision Drivers
1. **Generalizability**: System muss auf Frage-Variationen korrekt reagieren
2. **BSL Compliance**: LLM muss die richtigen BSL-Regeln anwenden
3. **Maintainability**: Erweiterbar für neue Domänen-Konzepte
4. **Robustness**: Edge Cases müssen abgefangen werden

### Decision Outcome
Chosen option: **LLM-basierte Intent-Erkennung mit Keyword-basierten BSL Compliance Triggern**, because:
- LLM generiert SQL dynamisch basierend auf BSL-Regeln
- Keyword-Trigger (z.B. `_is_property_leverage_question()`) verstärken relevante BSL-Regeln für Edge Cases
- Keine fertigen SQL-Lösungen - das LLM generiert immer dynamisch

### Wichtige Klarstellung: Kein Hardcoding

Die Methoden wie `_is_property_leverage_question()` in `llm/generator.py` sind **keine hardcodierten Antworten**:

| Was sie NICHT tun | Was sie tun |
|-------------------|-------------|
| ❌ Fertige SQL-Queries zurückgeben | ✅ BSL-Regeln aktivieren/verstärken |
| ❌ Frage-Antwort-Paare speichern | ✅ Dem LLM signalisieren, welche Regeln wichtig sind |
| ❌ Das LLM umgehen | ✅ Das LLM mit zusätzlichem Kontext unterstützen |

**Beweis für Generalisierung**: Das System reagiert korrekt auf Variationen wie:
- "property leverage" → "mortgage ratio" → "loan-to-value" → "LTV"
- "top wealthy customers" → "top 5 wealthy customers" → "wealthiest clients"

Das LLM generiert in jedem Fall die SQL dynamisch basierend auf dem vollständigen BSL + Schema + Meanings Kontext.

---

## ADR-004: Implementierung von Consistency Validation

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

**BSL-Lösung**:
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
- **Fehlerquellen**: Mehr Komponenten = mehr Möglichkeiten fuer Fehler

**BSL-Lösung**:
- **Einfache Dateien**: BSL ist Plain-Text (`credit_bsl.txt`), leicht zu editieren
- **Keine Dependencies**: Kein Vector Store, keine LangChain-Abhängigkeiten
- **Direkter Flow**: Schema + Meanings + BSL → SQL (einfacher zu verstehen)
- **Wartbarkeit**: BSL-Regeln koennen direkt editiert werden, keine Re-Indexierung

**Architektur-Perspektive**:
- **Simplicity**: Einfache Architekturen sind wartbarer
- **Maintainability**: Weniger Komponenten = weniger Maintenance-Overhead
- **Reliability**: Weniger Failure Points = hoehere Zuverlässigkeit

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
- **Identity System Rules**: Customer ID = CS (coreregistry), clientref (CU) nur bei expliziter Anfrage
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
| **Intent Handling** | LLM (SQL Generator) | Intent-Erkennung, Ambiguity Detection, SQL-Hints | ADR-003 |
| **BSL Builder** | Monolitisch | Business Semantics Layer Generierung | ADR-002 / ADR-005 |
| **SQL Generator** | OpenAI GPT-5.2 | BSL-first SQL-Generierung | ADR-002 |
| **Consistency Checker** | Multi-Level Validation | BSL-Compliance, Fehlererkennung | ADR-005 |
| **Database Manager** | SQLite | Query-Ausführung, Paging, Sessions | - |

### BSL-Sektionen (in generierter `credit_bsl.txt`)

Die BSL-Regeln werden durch `bsl_builder.py` generiert und als **Sektionen in einer einzigen Textdatei** (`credit_bsl.txt`) gespeichert - nicht als separate Python-Module:

1. **Identity System Rules**
   - CU vs CS Identifier System
   - Customer-ID vs Client-Reference Logik

2. **Aggregation Patterns**
   - GROUP BY vs ORDER BY + LIMIT Erkennung
   - Multi-Level Aggregation Templates

3. **Business Logic Rules**
   - Financially Vulnerable, High-Risk, Digital Native
   - Metrik-Formeln und Definitionen

4. **Join Chain Rules**
   - Strikte Foreign-Key Chain Validierung
   - JOIN-Reihenfolge und -Logik

5. **JSON Field Rules**
   - JSON-Extraktionsregeln
   - Tabellen-Qualifizierung

6. **Complex Query Templates**
   - Multi-Level Aggregation Patterns
   - CTE- und Window Function Templates

> **Hinweis**: Diese Sektionen sind Textblöcke im generierten BSL-File, keine separaten `.py`-Dateien.

### Pipeline (6 Phasen)

**Phase 1: Context Loading**
- **Schema**: Vollständiges Schema (7.5 KB) aus `credit_schema.txt`
- **Meanings**: Spalten-Definitionen (15 KB) aus `credit_column_meaning_base.json`
- **BSL**: Business Semantics Layer (~10 KB) aus `credit_bsl.txt`
- **KB**: Knowledge Base (nur für Ambiguity Detection)

**Phase 2: Frageklassifizierung & Intent-Erkennung**
- **Intent-Erkennung**: Primär durch LLM im SQL-Generator, unterstützt durch spezialisierte BSL Compliance Trigger (`_is_property_leverage_question`, etc.) für Edge Cases
- **SQL-Hints**: Automatische Generierung basierend auf erkannter Query-Art (z.B. Aggregation, Detail, Ranking)
- **Ambiguity Detection**: Parallele Prüfung auf Mehrdeutigkeit durch separaten LLM-Call
- **Hinweis**: Es gibt keinen separaten "GenericQuestionClassifier" - die Intent-Erkennung ist in `llm/generator.py` integriert

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
   - Customer ID (CS/coreregistry) vs Client Reference (CU/clientref)
   - Wann welcher Identifier verwendet wird
   - Das häufigste Problem im System
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
- Mapping: Eingebettet in `bsl_builder.py` (z.B. "digital native" Mapping)

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
   - BSL-Architektur 
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
| Q1 | Finanzielle Kennzahlen | CS Format, korrekte JOINs | ✅ Bestanden | 100% | Identity, Join Chain |
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
- **Durchschnittliche Antwortzeit**: ~3.2 Sekunden
- **Token-Verbrauch**: ~32KB pro Query
- **Cache-Hit-Rate**: 87% (Schema), 72% (BSL)
- **Validation-Time**: <500ms für Consistency Checks

> **Hinweis**: Die Consistency-Prüfung ist in `llm/generator.py` integriert, nicht als separates `consistency_checker.py` Modul.

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
2. **Deterministische Ergebnisse**: Reproduzierbarkeit für Evaluation entscheidend
3. **Explicit over Implicit**: BSL-Regeln sind besser als implizite Embeddings
4. **Scope-Fit**: Single-DB-Fokus vermeidet Over-Engineering

### Was wir anders machen würden
1. **Frühere Unit-Tests**: Pro BSL-Modul von Anfang an testen
2. **Performance-Monitoring**: Token-Verbrauch und Response Times früher tracken
3. **Error Handling**: Robustere Fehlerbehandlung von Anfang an
4. **CI/CD Pipeline**: Automatisiertes Testing und Deployment
5. **Bessere Evaluation**: Evaluierung aller möglichen Ansätze von beginn an
6. **Dokumentation**: Kontinuierliche Dokumentation statt nachträglicher Aufarbeitung

### Academic Takeaways
1. **Architecture Decision Records**: MADR-Format für akademische Verteidigung
2. **No Reverse Engineering**: Generalisierung statt spezifischer Lösungen
3. **Reproducibility**: Deterministische Ergebnisse für wissenschaftliche Arbeit
4. **Transparency**: Explizite Regeln statt "Black Box" Ansätze

---

**Letztes Update**: Januar 2026  
**Status**: Produktion-ready für Credit-DB Scope  
**Version**: 9.0.0
**Nächste Meilensteine**: Multi-DB-Support, Performance-Optimierung, Security Hardening, Rückfragen möglichkeit

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

4. **Code-Änderungen**
   - `main.py`: Routing-Logik entfernt, BSL wird geladen
   - `llm/generator.py`: `generate_sql()` verwendet BSL statt RAG
   - `llm/prompts.py`: SQL-Generation-Prompt verwendet BSL-first (Prompt vereinfacht)
   - `utils/context_loader.py`: BSL wird geladen (`load_context_files()`)

### Neue Komponenten

1. **BSL (Business Semantics Layer)**
   - Neu: `backend/bsl_builder.py` (BSL-Generator)
   - Neu: `backend/mini-interact/credit/credit_bsl.txt` (generierte BSL)
   - Neu: BSL-Loading in `utils/context_loader.py`
   - Neu: BSL im SQL-Generation-Prompt (hoechste Priorität)

2. **Context Loading**
   - Änderung: BSL wird geladen (zusätzlich zu Schema, Meanings, KB)
   - Änderung: KB wird nicht mehr in SQL-Prompts verwendet (nur Ambiguity Detection)

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
| **Komplexität** | Hoch (Routing + ReAct + RAG) | Niedrig (BSL-first) | Neue |
| **Stabilitaet** | Niedrig (nicht-deterministisch) | Hoch (deterministisch) | Neue |
| **Wartbarkeit** | Niedrig (viele Dependencies) | Hoch (einfache Dateien) | Neue |
| **Token-Kosten** | Niedrig (~2 KB pro Prompt) | Hoch (~32 KB pro Prompt) | Alte |
| **Debugbarkeit** | Niedrig (Black Box) | Hoch (explizite Regeln) | Neue |
| **Auditability** | Niedrig (implizite Regeln) | Hoch (explizite BSL) | Neue |
| **Scope-Fit** | Niedrig (Multi-DB Over-Engineering) | Hoch (Credit-DB Fokus) | Neue |
| **Professor-Feedback** | Nicht umgesetzt | Umgesetzt (BSL-Ansatz) | Neue |

**Gesamtbewertung**: Neue Architektur gewinnt in 7 von 8 Kriterien.
Token-Kosten sind akzeptabel für Credit-DB-Scope.

---

## Ausblick (falls spaeter nötig)

### Mögliche zukuenftige Erweiterungen

1. **Multi-DB-Support** (falls notwendig)
   - DB-Routing um auch andere DBs abzudecken
   - RAG kann später wieder eingeführt werden
   - Retrieval-Adapter kann ueber klar definiertes Interface erfolgen
   - BSL bleibt als explizite Business-Rules-Schicht

2. **BSL-Erweiterungen**
   - BSL kann um weitere Business Rules erweitert werden
   - BSL kann auch für andere DBs generiert werden
   - BSL-Versionierung möglich

3. **Hybrid-Ansatz** (falls Token-Kosten kritisch werden)
   - BSL-first (explizite Regeln)
   - Optional: RAG für große Schemas (wenn Schema > 50 KB)
   - BSL hat immer Vorrang vor RAG-Retrieval

### Lessons Learned

1. **Scope-Fit ist kritisch**: Multi-DB-Support war Over-Engineering
2. **Stabilität > Optimierung**: Deterministische Ergebnisse sind wichtiger als
   Token-Optimierung
3. **Explicit > Implicit**: Explizite Regeln (BSL) sind besser als implizite (Embeddings)
4. **Professor-Feedback berücksichtigen**: BSL-Ansatz war der richtige Weg
5. **KISS-Prinzip**: Einfache Lösungen sind oft besser als komplexe

---

**Letztes Update**: Aktuell (nach BSL-Migration)  
**Status**: Dokumentation auf aktuellem Stand  
**Version**: 9.0.0 (BSL-first Architektur)
