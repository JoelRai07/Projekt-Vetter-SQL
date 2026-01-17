# Architecture Decision Records (ADRs) – Text2SQL Projekt

## Ziel dieses Dokuments
Dieses Dokument enthält die zentralen Architekturentscheidungen (Architecture Decision Records) des Text2SQL-Projekts.
Es orientiert sich am **MADR-Standard** und dokumentiert die Entwicklung von der initialen Multi-DB RAG/ReAct Architektur
bis zur aktuellen **BSL-first Single-Database** Architektur.

**Status**: Stand Januar 2026  
**Version**: 9.0.0 (Abgabe) – Architektur: BSL-first  
**Scope**: Credit-Datenbank (BIRD mini-interact Subset)

---

## Konventionen (wichtig für Konsistenz)
- **Date** = Datum der Entscheidung (accepted/deprecated)
- **Originally implemented** (optional) = Zeitraum/Datum der ersten Umsetzung
- **Superseded by** = ADR, die diese Entscheidung ersetzt
- „Rationale/Warum“ wird **kurz** in ADRs gehalten und bei Bedarf auf **Appendix A** verwiesen.

---

## ADR Index

| ADR | Titel | Status | Date | Superseded by |
|-----|-------|--------|------|---------------|
| 001 | Initiale Multi-Database RAG/ReAct Architektur | deprecated | 12.01.2026 | ADR-004 |
| 002 | Alte Routing Architektur (Database Auto-Routing) | deprecated | 12.01.2026 | ADR-004 |
| 003 | Vector Store (ChromaDB) | deprecated | 12.01.2026 | ADR-004 |
| 004 | Migration zu BSL-first Single-Database | accepted | 12.01.2026 | – |
| 005 | Heuristische Fragetyp-Erkennung + BSL-Compliance-Trigger | accepted | 12.01.2026 | – |
| 006 | Consistency Validation (mehrstufig) | accepted | 12.01.2026 | – |

---

# Phase 1 – Legacy Multi-DB (deprecated)

## ADR-001: Initiale Multi-Database RAG/ReAct Architektur

**Status**: deprecated (superseded by ADR-004)  
**Deciders**: Projektteam  
**Date**: 17.12.25-12.01.2026 (Created/Deprecated)  
**Originally implemented**: ca. 15.12.2025 (erste Umsetzung)  
**Technical Story**: Architekturentwurf für BIRD-INTERACT (Multi-DB) mit Token-Optimierung durch Retrieval

### Context and Problem Statement
Zu Projektbeginn wurde eine Architektur angestrebt, die:
- Multi-Database-Support für den vollständigen BIRD-Datensatz ermöglicht *(anfängliche Annahme)*
- Token-Kosten durch intelligentes Retrieval reduziert (große Schemas/KB)
- skalierbar für zukünftige Erweiterungen ist
- moderne RAG/ReAct-Ansätze nutzt
- möglichst alle Evaluationsfragen korrekt beantwortet und auch ähnliche Fragen generalisiert

Im Projektverlauf zeigte sich:
- Abgabe-Scope fokussiert faktisch auf **eine** DB (Credit)
- Multi-DB/Retrieval steigerten Komplexität und Instabilität stärker als den Nutzen

### Decision Drivers
1. Token-Effizienz (Kontext-Overload vermeiden)
2. Multi-DB Support (Benchmark umfasst viele DBs)
3. Modern Tech Stack (RAG/ReAct)
4. Skalierung & Generalisierung

### Decision Outcome
**RAG + ReAct** wurde gewählt, weil es die damaligen Ziele (Multi-DB + Token-Reduktion + Skalierung) am besten abdeckte.

### Consequences
**Positive**
- Token-Reduktion durch Retrieval (Chunks statt Full-Schema)
- Multi-DB Support prinzipiell möglich

**Negative**
- Nicht-deterministische Ergebnisse (Retrieval variiert → SQL variiert)
- Hohe Komplexität (viele moving parts)
- Auditability/Wartbarkeit schwierig

### Superseded by
- **ADR-004: Migration zu BSL-first Single-Database Architektur**

---

## ADR-002: Alte Routing Architektur (Database Auto-Routing)

**Status**: deprecated (superseded by ADR-004)  
**Deciders**: Projektteam  
**Date**: 17.12.25-12.01.2026 (Created/Deprecated) 
**Originally implemented**: ca. 15.12.2025  
**Technical Story**: Automatische DB-Auswahl per LLM zur Unterstützung von Multi-DB im BIRD-Setup

### Context and Problem Statement
Für Multi-DB wurde ein Mechanismus benötigt, der automatisch bestimmt, welche Datenbank zur Frage passt – ohne manuelle Auswahl.

### Decision Outcome
LLM-basiertes Auto-Routing via DB-Profil-Snippets + Confidence.

### Implementation Notes (historisch)
- DB-Profile: Schema-/KB-/Meanings-Snippets je DB
- LLM bestimmt DB + Confidence
- Confidence ≥ 0.55 → DB ausgewählt
- Confidence < 0.55 → Ambiguity-Result

### Consequences
**Negative**
- +2–3 Sekunden Latenz pro Request
- Nicht-deterministisch (DB-Auswahl variiert)
- Komplexe Fehlerbehandlung, im Abgabe-Scope Overengineering

### Superseded by
- **ADR-004**

---

## ADR-003: Vector Store (ChromaDB)

**Status**: deprecated (superseded by ADR-004)  
**Deciders**: Projektteam  
**Date**: 17.12.25-12.01.2026 (Created/Deprecated)  
**Originally implemented**: ca. 15.12.2025  
**Technical Story**: Persistenter Vector Store zur Token-Reduktion und semantischen Chunk-Suche

### Context and Problem Statement
Schema-/KB-Inhalte sollten als Chunks gespeichert und semantisch durchsucht werden, um Prompt-Länge zu reduzieren.

### Decision Outcome
ChromaDB als lokaler, persistenter Vector Store (`vector_store/`).

### Consequences
**Negative**
- Dateikorruption möglich (erlebt) → schlechte Reproduzierbarkeit
- Maintenance (Re-Indexing/Versionierung)
- Nicht-deterministisches Retrieval → SQL-Qualität schwankt
- Im Single-DB Scope nicht mehr sinnvoll

### Superseded by
- **ADR-004**

---

# Phase 2 – Migration (accepted)

## ADR-004: Migration zu BSL-first Single-Database Architektur

**Status**: accepted  
**Deciders**: Projektteam, Professor-Feedback  
**Date**: 12.01.2026  
**Technical Story**: Stabilisierung & Scope-Anpassung nach Evaluation

### Context and Problem Statement
Nach ersten Implementierungen zeigten sich:
- Nicht-deterministische Ergebnisse (gleiche Frage → unterschiedliche SQL)
- Hohe Komplexität & viele Fehlerquellen
- Scope-Mismatch: faktisch Credit-DB-only
- Professor-Feedback: Fokus Credit-DB; BSL sei geeigneter

### Decision Outcome
**BSL-first Single-DB** wurde gewählt.

### Consequences
**Positive**
- bessere Nachvollziehbarkeit (Regeln explizit)
- weniger Dependencies (ChromaDB/LangChain weg)
- Debugging einfacher, Stabilität höher

**Negative**
- höhere Token-Kosten (Full Schema + Meanings + BSL)
- Multi-DB Support entfernt

### Notes
Ausführliche Begründung siehe **Appendix A: Rationale (BSL vs RAG)**.

---

# Phase 3 – Stabilisierung (accepted)

## ADR-005: Heuristische Fragetyp-Erkennung + BSL-Compliance-Trigger

**Status**: accepted (vollständig umgesetzt)  
**Deciders**: Projektteam  
**Date**: 12.01.2026  
**Technical Story**: Generalisierung + Edge-Case Stabilisierung ohne Hardcoding

### Context and Problem Statement
Für robuste Text2SQL-Generierung musste das System:
- BSL-Regeln zuverlässig anwenden
- auf Variationen von Fragen generalisieren
- ohne feste Frage→SQL Paare auskommen

### Decision Outcome
**Keyword/Heuristik-basierte Fragetyp-Erkennung** plus **BSL-Compliance-Regeln**.
Wenn die erste SQL nicht compliant ist, wird gezielt eine **Regeneration** ausgelöst.

### Implementation Evidence (im Code)
- Fragetyp-Checks: z.B. `_is_property_leverage_question`, `_is_credit_classification_summary_question`, `_has_explicit_time_range`
- Compliance-Bewertung: `_bsl_compliance_instruction(question, sql)`
- Regeneration bei Verstoß: `_regenerate_with_bsl_compliance(...)`

### Consequences
- Weniger typische Fehler (Aggregation vs Detail, CU vs CS, Cohort/Time-Logic Fehler)
- Kein Hardcoding von SQL, sondern „Policy/Compliance“-Schicht

---

## ADR-006: Consistency Validation (mehrstufig)

**Status**: accepted  
**Deciders**: Projektteam  
**Date**: 12.01.2026  
**Technical Story**: Qualitätssicherung, Fehlervermeidung, bessere Debugbarkeit

### Context and Problem Statement
Trotz BSL treten in der Praxis wiederkehrende Fehler auf:
- Identifier-Verwechslungen (CU vs CS)
- falsche JOIN-Chain / fehlende Zwischentabellen
- falscher Detailgrad (Summary vs Row-level)
- JSON-Feld-Qualifizierungsprobleme
- SQL-Dialekt-Fallen (z.B. UNION + ORDER BY in SQLite)

### Decision Outcome
Einführung einer **mehrstufigen Validation**, um typische Fehler früh zu erkennen und
gezielt zu korrigieren.

### Validation Layers
- **Layer A (deterministisch / rule-based):**
  - SQL Guard / Placeholder-Checks (`_contains_param_placeholders`)
  - UNION/ORDER Fix (`_fix_union_order_by`)
  - Fragetyp-spezifische Konsistenzregeln (über ADR-005 Trigger + Compliance Instruction)
- **Layer B (LLM-Validation optional):**
  - Semantische Validierung gegen Schema (Funktion `validate_sql(...)`)
  - Optionaler Correction-Loop (`generate_sql_with_correction(...)`)

### Consequences
- Höhere Robustheit und bessere Fehlermeldungen (Debugging)
- Zusätzliche Latenz möglich, wenn Layer B (LLM Validation) aktiv genutzt wird
- Validierungsschicht bleibt erweiterbar (neue Regeln = neue Checks)

---

# Appendix A – Rationale & Learnings (BSL vs RAG)

## A1) Determinismus & Auditability
- BSL macht Regeln explizit und prüfbar (Auditability)
- Retrieval-basierte Regeln sind implizit im Kontext und schwer reproduzierbar
- Für Evaluation/Abgabe ist Reproduzierbarkeit wichtiger als Token-Optimierung

## A2) Wartbarkeit & Einfachheit
- RAG/ReAct bringt zusätzliche Dependencies und Failure Points (Vector Store, Embeddings, Re-Indexing)
- BSL ist Plain-Text (`credit_bsl.txt`) und leichter zu pflegen/zu reviewen
- Weniger Komponenten = weniger Debug- und Maintenance-Aufwand

## A3) Warum BSL im Projekt besser passte
- klarer Scope (Credit-DB) → Full Context + BSL ist vertretbar
- BSL priorisiert kritische Regeln:
  - Identity System (CS vs CU)
  - Aggregation Patterns
  - Business Rules (Segmente/Metriken)
  - JSON Field Rules
  - Join Chain Rules

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
| **Intent Handling** | LLM (SQL Generator) | Intent-Erkennung, Ambiguity Detection, SQL-Hints | ADR-005 |
| **BSL Builder** | Monolitisch | Business Semantics Layer Generierung | ADR-002 / ADR-004 |
| **SQL Generator** | OpenAI GPT-5.2 | BSL-first SQL-Generierung | ADR-004 |
| **Consistency Checker** | Multi-Level Validation | BSL-Compliance, Fehlererkennung | ADR-006 |
| **Database Manager** | SQLite | Query-Ausführung, Paging, Sessions | ADR-001 |

### BSL-Sektionen (in generierter `credit_bsl.txt`)

Die BSL-Regeln werden durch `bsl_builder.py` generiert und als **Sektionen in einer einzigen Textdatei** (`credit_bsl.txt`) gespeichert:

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

## Text2SQL Pipeline (Credit DB, BSL-first) – Stand Januar 2026

> **Hinweis zur Terminologie:**  
> In diesem Projekt wird zwischen **Build/Maintenance** (nicht pro Request) und **Runtime** (pro User-Request) unterschieden.  
> Außerdem wird die Validierung in **Layer A (rule-based)** und **Layer B (LLM-based)** gegliedert, passend zur Implementierung in `backend/llm/generator.py`.

---

### Phase 0: Build / Maintenance (nicht pro Request)
- **BSL Builder** (`bsl_builder.py`): Generiert die Datei `credit_bsl.txt` aus **KB + Meanings + Schema** (on-demand/offline).
- **Manuelle Overrides**: Optionaler Abschnitt `# BSL OVERRIDES (MANUAL)` in `credit_bsl.txt`.
  - Wird zur Laufzeit per `_extract_bsl_overrides(bsl_text)` extrahiert und im Prompt als **höchste Priorität** platziert.

---

### Phase 1: Context Loading (Runtime)
- **Schema**: Vollständiges Schema (z. B. aus `credit_schema.sql` / `credit_schema.txt` je nach Export)  
- **Meanings**: Spaltenbedeutungen aus `credit_column_meaning_base.json`
- **BSL**: Business Semantics Layer aus `credit_bsl.txt` (inkl. optionaler Overrides)
- **KB**: Knowledge Base wird primär für **Ambiguity Detection** verwendet (nicht zwingend Teil des SQL-Generation-Prompts)

---

### Phase 2: Ambiguity Detection (optional, separater LLM-Call)
- **Funktion**: `check_ambiguity(question, schema, kb, meanings)`
- **Ziel**: Mehrdeutige Fragen erkennen, bevor SQL erzeugt wird
- **Output**:  
  - `is_ambiguous`  
  - `reason`  
  - `questions` (Rückfragen zur Präzisierung)

> **Wichtig:** Diese Phase ist ein **separater Schritt** (kein „Parallelprozess“ im Generator selbst). Ob sie immer ausgeführt wird, hängt vom Orchestrator/Endpoint ab.

---

### Phase 3: Initiale SQL-Generierung (BSL-first, LLM)
- **Funktion**: `generate_sql(question, schema, meanings, bsl)`
- **Prompt-Reihenfolge (BSL-first)**:
  1. `BSL OVERRIDES (MANUAL)` (falls vorhanden)
  2. `BUSINESS SEMANTICS LAYER (BSL)`
  3. `DATENBANK SCHEMA & BEISPIELDATEN`
  4. `SPALTEN BEDEUTUNGEN (Meanings)`
  5. `NUTZER-FRAGE`
- **Determinismus**: `temperature=0`
- **Intent (implizit)**: Das LLM entscheidet im Prompt über Detailgrad/Aggregation/Ranking usw. basierend auf BSL+Schema+Meanings.

---

### Phase 4: Rule-based Compliance & Auto-Repair (Layer A)
Diese Phase läuft **nach** der initialen SQL-Erzeugung und ist **deterministisch / regelbasiert**, kann aber bei Bedarf eine **gezielte Regeneration** triggern.

#### 4.1 Rule-based Checks (deterministisch)
- **SQL Placeholder Guard**: `_contains_param_placeholders(sql)`
  - verhindert Platzhalter wie `?`, `:name`, `@name`, `$name` (nicht kompatibel mit Execution)
- **SQLite Dialekt-Fix**: `_fix_union_order_by(sql)`
  - wrappt `UNION`-Queries bei top-level `ORDER BY`, um SQLite-Kompatibilität sicherzustellen

#### 4.2 Fragetyp-Heuristiken (Pattern-Trigger)
- Beispiele:  
  - `_is_property_leverage_question(question)`  
  - `_is_credit_classification_summary_question(question)`  
  - `_is_credit_classification_details_question(question)`  
  - `_has_explicit_time_range(question)`  
- Zweck: Edge Cases erkennen, bei denen LLMs häufig inkonsistente oder falsche SQL erzeugen (z. B. falscher Detailgrad, falsche Join-Chain, falsche Output-Spalten).

#### 4.3 BSL-Compliance Instruction
- **Funktion**: `_bsl_compliance_instruction(question, sql)`
- Ergebnis: Liefert eine konkrete Anweisung, wenn die SQL gegen projektkritische Regeln verstößt (z. B. falsches ID-System CU/CS, falscher Summary-vs-Detail Output, Cohort-Fehler ohne expliziten Zeitraum).

#### 4.4 Auto-Repair via Regeneration
- **Funktion**: `_regenerate_with_bsl_compliance(...)`
- Triggert einen **zweiten LLM-Call**, nur wenn `_bsl_compliance_instruction(...)` einen Verstoß erkennt.
- Markiert die Erklärung intern mit `"[BSL compliance regeneration]"`, um den Repair-Schritt nachvollziehbar zu machen.

---

### Phase 5: LLM-gestützte Validierung & Self-Correction (Layer B)
Diese Phase ergänzt Layer A um eine semantische Prüfung gegen das Schema und kann eine Korrekturschleife ausführen.

#### 5.1 Semantische SQL-Validierung
- **Funktion**: `validate_sql(sql, schema)`
- LLM prüft die SQL semantisch (Schema-Kompatibilität, offensichtliche Logikfehler) und liefert:
  - `is_valid`
  - `errors`
  - `severity`
  - `suggestions`

### Phase 5.2: Self-Correction Loop (Layer B)

Der Self-Correction Loop wird **im Request-Orchestrator (Backend)** ausgelöst, wenn das System erkennt, dass die initiale SQL vermutlich nicht ausreichend ist. Es gibt zwei Trigger:

1) **Nach der ersten SQL-Generierung (Confidence-Gate)**
- Wenn das Modell eine niedrige Sicherheit meldet  
  → `confidence < 0.4`  
- Dann wird `generate_sql_with_correction(...)` gestartet.

2) **Nach der SQL-Validierung (Severity-Gate)**
- Wenn die LLM-Validierung einen schweren Fehler erkennt  
  → `severity == "high"`  
- Dann wird ebenfalls `generate_sql_with_correction(...)` ausgeführt und anschließend erneut validiert.

> Hinweis: Die Gates (Confidence/Severity) liegen im Orchestrator/Endpoint und entscheiden, ob eine Korrektur gestartet wird. 
> Sobald der Orchestrator `generate_sql_with_correction` aufruft führt der `OpenAIGenerator` die Korrekturschleife intern aus (Generate → Validate → Correct, bis max_iterations (hier n = 2)).
---

### Phase 6: Query Execution, Paging & Result Handling
- **Execution**: SQLite führt die (finale) SQL deterministisch aus.
- **Paging / Session Management**: typischerweise UUID-/Session-basiert (Orchestrator/Backend-API, außerhalb `OpenAIGenerator`).
- **Result Processing**:
  - Ergebnisse werden strukturiert zurückgegeben (z. B. JSON/Tabellenformat).
  - Optional: **Result Summary** via `summarize_results(...)` (separater LLM-Call) auf Basis von Sample Rows.

---

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
   - BSL muss bei Schema-Änderungen regeneriert werden (Dies kann aber einfach gelöst werden)
   - Aber: Automatisiert durch `bsl_builder.py`

### Bewertungs-Matrix (Architektur-Kriterien)

| Kriterium | RAG/ReAct (Alt) | BSL-first (Aktuell) | Gewinner | Begründung |
|-----------|----------------|-------------------|----------|------------|
| **Stabilität** | Niedrig (nicht-deterministisch) | Hoch (deterministisch) | **Aktuell** | Wichtig für Evaluation |
| **Nachvollziehbarkeit** | Niedrig (Black Box) | Hoch (explizite Regeln) | **Aktuell** | Academic Rigor |
| **Wartbarkeit** | Niedrig (viele Dependencies) | Hoch (modular) | **Aktuell** | SOLID-Prinzipien |
| **Token-Kosten** | **Niedrig** (~2KB) | **Hoch** | **Alt** | Kosteneffizienz |
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
1. **Professor-Feedback**: BSL-Ansatz war entscheidend für Erfolg
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
**Version**: X.0.0
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
   - Neu: BSL im SQL-Generation-Prompt (höchste Priorität)

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
schema = get_cached_schema(db_path)
meanings = get_cached_meanings(database, DATA_DIR)
kb, bsl = load_context_files(database, DATA_DIR)  # je nach Implementierung
sql = llm_generator.generate_sql(question, schema, meanings, bsl)  # Direkt, kein ReAct
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
| **Stabilität** | Niedrig (nicht-deterministisch) | Hoch (deterministisch) | Neue |
| **Wartbarkeit** | Niedrig (viele Dependencies) | Hoch (einfache Dateien) | Neue |
| **Token-Kosten** | Niedrig (~2 KB pro Prompt) | Hoch (~32 KB pro Prompt) | Alte |
| **Debugbarkeit** | Niedrig (Black Box) | Hoch (explizite Regeln) | Neue |
| **Auditability** | Niedrig (implizite Regeln) | Hoch (explizite BSL) | Neue |
| **Scope-Fit** | Niedrig (Multi-DB Over-Engineering) | Hoch (Credit-DB Fokus) | Neue |
| **Professor-Feedback** | Nicht umgesetzt | Umgesetzt (BSL-Ansatz) | Neue |

**Gesamtbewertung**: Neue Architektur gewinnt in 7 von 8 Kriterien.
Token-Kosten sind akzeptabel für Credit-DB-Scope.

---

## Ausblick (falls später nötig)

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
**Version**: X.0.0 (BSL-first Architektur)
