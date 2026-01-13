# Architektur-Entscheidungen & Historie (RAG/ReAct/Routing → BSL-first)

## Ziel dieses Dokuments
Dieses Dokument fasst die frueheren Architekturansaetze und die heutigen Entscheidungen
zusammen. Es ist als Begruendung fuer Design-Entscheidungen gedacht und liefert Kontext
fuer Stakeholder, die Wert auf Stabilitaet, Wartbarkeit und Nachvollziehbarkeit legen.

Dieses Dokument dokumentiert die Migration von einer komplexen Multi-Database-Architektur
mit RAG/ReAct-Retrieval hin zu einem fokussierten Single-Database-Ansatz mit Business
Semantics Layer (BSL). Die Entscheidung wurde basierend auf Projekt-Feedback und 
architektonischen Ueberlegungen getroffen.

---

## Vorher: Routing + ReAct/RAG (Ursprüngliche Architektur)

### Ausgangslage
Die initiale Architektur wurde entworfen, um mehrere Datenbanken zu unterstuetzen und
Token-Kosten durch gezieltes Retrieval zu reduzieren. Das System sollte skalierbar und
flexibel sein.

### Bausteine der alten Architektur

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

---

## Warum wir das geaendert haben (Entscheidungsgrundlagen)

### 1) Scope-Fit: Projekt-Feedback des Professors

**Ausloeser**: Waehrend der Projektphase wurde durch den Professor (IT-Architektur PhD)
Feedback gegeben: **"Es geht nur um die Credit-DB und einer der besten Ansätze wäre ein
BSL (Business Semantics Layer)."**

**Analyse**:
- Das Projekt nutzt faktisch **nur** die Credit-Datenbank (credit.sqlite)
- Multi-Database-Routing brachte keinen Mehrwert, aber zusaetzliche Komplexität
- BSL-Ansatz wurde als architektonisch besserer Weg identifiziert

**Entscheidung**: Focus auf Credit-DB, Migration zu BSL-first Architektur

**Architektur-Perspektive**:
- **YAGNI-Prinzip** (You Aren't Gonna Need It): Multi-DB-Support war Over-Engineering
- **KISS-Prinzip** (Keep It Simple, Stupid): Einfache, fokussierte Loesung vor komplexer
  generalisierter Architektur

### 2) Stabilitaet & Nachvollziehbarkeit

**Problem mit ReAct/RAG**:
- **Nicht-deterministische Ergebnisse**: Retrieval-Ergebnisse variieren je nach
  Embedding-Qualität und Vector Store Zustand
- **Schwer reproduzierbar**: Gleiche Frage kann unterschiedliche SQL generieren
- **Evaluation-Problem**: Fuer Evaluation und Praesentation ist eine reproduzierbare
  Pipeline essentiell
- **Debugging-Schwierigkeit**: Fehler sind schwer nachvollziehbar (warum wurde dieser
  Chunk retrieved?)

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

## Heute: BSL-first, Full Schema, Single-DB (Aktuelle Architektur)

### Aktueller Zustand
Die neue Architektur fokussiert sich auf **Stabilitaet, Nachvollziehbarkeit und 
Wartbarkeit** statt auf Optimierungen fuer Multi-DB-Szenarien.

**Kernkomponenten**:
- **Single-DB**: Immer `credit.sqlite` (kein Routing mehr)
- **Keine RAG/Vector Store**: Vollstaendiges Schema + Meanings + BSL im Prompt
- **Keine ReAct-Schleife**: Direkte SQL-Generierung plus Validierung
- **BSL-first**: Business Semantics Layer hat hoechste Prioritaet im Prompt

### Pipeline (Aktuell, 6 Phasen)

**Phase 1: Context Loading**
- **Schema**: Vollstaendiges Schema (7.5 KB) aus `credit_schema.txt`
- **Meanings**: Vollstaendige Spalten-Definitionen (15 KB) aus `credit_column_meaning_base.json`
- **BSL**: Business Semantics Layer (generiert aus KB + Meanings) aus `credit_bsl.txt`
- **KB**: Knowledge Base wird geladen, aber nicht mehr in SQL-Prompts verwendet (nur fuer
  Ambiguity Detection)

**Phase 2: Ambiguity Detection (parallel zu Phase 3)**
- LLM-basierte Erkennung mehrdeutiger Fragen
- Laeuft parallel zur SQL-Generierung (kein Blocking)
- Wenn mehrdeutig: Hinweis wird mitgeschickt, aber Pipeline laeuft weiter

**Phase 3: SQL-Generierung (BSL-first)**
- **Prompt-Struktur** (in dieser Reihenfolge):
  1. BSL Overrides (hoechste Prioritaet)
  2. Business Semantics Layer (kritische Regeln)
  3. Vollstaendiges Schema + Beispieldaten
  4. Spalten-Bedeutungen (Meanings)
  5. Nutzer-Frage
- **Direkte Generierung**: Keine ReAct-Schleife, direkt SQL generieren
- **BSL-Compliance**: LLM muss BSL-Regeln befolgen (Identity System, Aggregation Patterns,
  Business Rules)

**Phase 4: SQL-Validierung (2-Ebenen)**
- **Level 1: SQL Guard** (Regex-basiert, ~10ms)
  - Nur SELECT/WITH erlaubt
  - Keine INSERT/UPDATE/DELETE/DROP
  - Nur bekannte Tabellen
  - Max. 1 Statement
- **Level 2: LLM Validation** (Semantisch, ~1-2s)
  - JOIN-Validierung (Foreign Key Chain)
  - Aggregation-Korrektheit (GROUP BY)
  - Spalten-Qualifizierung (table.column)
  - JSON-Pfad-Validierung

**Phase 5: SQL-Ausfuehrung mit Paging**
- SQLite Query ausfuehren
- Paging: LIMIT + OFFSET
- Query-Sessions: UUID-basierte Sessions fuer konsistentes Paging

**Phase 6: Ergebnis-Zusammenfassung (Optional)**
- LLM erstellt natuerlichsprachliche Zusammenfassung
- Fallback: Wenn LLM-Call fehlschlaegt, alternative Zusammenfassung

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

## Trade-offs (bewusst akzeptiert)

### Pro (Vorteile der neuen Architektur)

1. **Weniger Moving Parts**
   - Kein Vector Store, keine LangChain-Abhaengigkeiten
   - Einfacher zu warten und zu erklären
   - Weniger Fehlerquellen

2. **Konsistente und nachvollziehbare Ergebnisse**
   - Deterministisch: Gleiche Frage + gleicher BSL = gleiche SQL
   - Reproduzierbar: Wichtig fuer Evaluation und Praesentation
   - Nachvollziehbar: BSL-Regeln sind explizit dokumentiert

3. **Bessere Debugbarkeit**
   - Fehler sind einfacher nachzuvollziehen (welche BSL-Regel wurde verletzt?)
   - BSL-Regeln koennen direkt geprueft werden (Plain-Text)
   - Keine "Black Box" (Vector Store Embeddings)

4. **Wartbarkeit**
   - BSL-Regeln koennen direkt editiert werden
   - Keine Re-Indexierung notwendig
   - Einfache Dateien statt komplexe Dependencies

5. **Auditability**
   - Business Rules sind explizit dokumentiert
   - Domain-Experten koennen BSL-Regeln pruefen
   - Wichtig fuer Compliance

6. **Professor-Feedback umgesetzt**
   - Fokus auf Credit-DB (wie vom Professor empfohlen)
   - BSL-Ansatz als "bester Ansatz" umgesetzt

### Contra (Nachteile der neuen Architektur)

1. **Hoeherer Token-Verbrauch**
   - Vollstaendiges Schema (7.5 KB) + Meanings (15 KB) + BSL (~10 KB) 
    = ~32.5 KB pro Prompt
   - Alte Architektur: ~2 KB (nur relevante Chunks)
   - **Aber**: Fuers Credit-DB-Projekt akzeptabel (Schema ist nicht riesig)

2. **Skalierung auf viele DBs benoetigt spaetere Erweiterung**
   - Multi-DB-Support waere spaeter moeglich
   - Fuer aktuellen Projekt-Scope nicht notwendig (YAGNI-Prinzip)

3. **Weniger "moderne" Technologie**
   - Keine RAG/Vector Store (weniger "buzzword-compliant")
   - **Aber**: Einfacher und stabiler

### Entscheidungsgrundlage (IT-Architektur-Perspektive)

**1. Komplexitaet vs. Stabilitaet**
- **Entscheidung**: Stabilitaet geht vor Optimierung
- **Begruendung**: Fuer Evaluation und Praesentation ist Reproduzierbarkeit kritisch
- **Trade-off**: Akzeptiert hoeheren Token-Verbrauch fuer Stabilitaet

**2. Scope-Fit (YAGNI-Prinzip)**
- **Entscheidung**: Single-DB Fokus in der Projektphase
- **Begruendung**: Projekt nutzt faktisch nur Credit-DB
- **Professor-Feedback**: "Es geht nur um die Credit-DB"

**3. Auditability (Compliance-Perspektive)**
- **Entscheidung**: BSL macht Regeln explizit und pruefbar
- **Begruendung**: Business Rules muessen von Domain-Experten geprueft werden koennen
- **Vorteil**: BSL ist Plain-Text, nicht in Embeddings versteckt

**4. Wartbarkeit (Maintenance-Perspektive)**
- **Entscheidung**: Einfache Architektur vor komplexer
- **Begruendung**: Weniger Moving Parts = weniger Maintenance-Overhead
- **Vorteil**: BSL-Regeln koennen direkt editiert werden

**5. Determinismus (Production-Perspektive)**
- **Entscheidung**: Reproduzierbare Ergebnisse vor nicht-deterministischen Optimierungen
- **Begruendung**: Wichtig fuer Evaluation und Debugging
- **Vorteil**: Gleiche Frage = gleiche SQL (deterministisch)

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
