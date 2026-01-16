# Inkonsistenzen-Check: Dokumentation vs. Code

**Datum**: Januar 2026  
**Zweck**: Systematische Prüfung aller 5 Hauptdokumente auf Inkonsistenzen mit der tatsächlichen Code-Architektur

---

## 📋 Geprüfte Dokumente

1. PROJEKT_ABGABE.md
2. ARCHITEKTUR_UND_PROZESSE_NEU.md
3. ARCHITEKTUR_ENTSCHEIDUNGEN.md
4. Für_Präsi_NEU.md
5. BSL_GUIDE.md

---

## ✅ Tatsächliche Backend-Architektur (Code-Realität)

### Existierende Module/Dateien:
```
backend/
├── main.py                    ✅ FastAPI App, Pipeline-Orchestrierung
├── config.py                  ✅ Config, OPENAI_API_KEY, DEFAULT_DATABASE
├── models.py                  ✅ Pydantic Models (QueryRequest, QueryResponse, etc.)
├── bsl_builder.py             ✅ BSL-Generierung aus KB + Meanings
├── database/
│   └── manager.py             ✅ DatabaseManager, Query-Ausführung, Paging
├── llm/
│   ├── generator.py           ✅ OpenAIGenerator: SQL-Gen, Validation, Ambiguity
│   └── prompts.py             ✅ SystemPrompts (SQL_GENERATION, SQL_VALIDATION, etc.)
└── utils/
    ├── cache.py               ✅ Caching für Schema, Meanings, Results
    ├── context_loader.py      ✅ load_context_files()
    ├── query_optimizer.py     ✅ QueryOptimizer (analyze_query_plan)
    └── sql_guard.py           ✅ enforce_safety(), enforce_known_tables()
```

### NICHT existierende Module (werden manchmal erwähnt):
- ❌ `utils/consistency_checker.py` - existiert nicht
- ❌ `llm/question_classifier.py` - existiert nicht
- ❌ Separate BSL-Module in `bsl/rules/` - BSL ist eine Textdatei, keine Python-Module

---

## 🔍 Gefundene Inkonsistenzen

### 1. Query Optimizer Erwähnung

**Problem**: Query Optimizer wird in manchen Dokumenten erwähnt, aber kaum erklärt

**Code-Realität**:
- ✅ Existiert: `utils/query_optimizer.py`
- ✅ Wird verwendet in `main.py` (Zeile 438-443)
- ⚠️ Wird aber nur zur Analyse verwendet (nicht zur aktiven Optimierung)

**Betroffene Dokumente**:
- PROJEKT_ABGABE.md: Nicht explizit erwähnt in Komponenten-Liste
- ARCHITEKTUR_UND_PROZESSE_NEU.md: Nicht in Komponenten-Tabelle
- Für_Präsi_NEU.md: Nicht erwähnt
- ARCHITEKTUR_ENTSCHEIDUNGEN.md: Nicht erwähnt

**Empfehlung**: Entweder vollständig dokumentieren oder als "optional/intern" markieren

---

### 2. Pipeline-Phasen Konsistenz

**Problem**: Unterschiedliche Phasen-Zählungen/-Namen in Dokumenten

**Tatsächlicher Ablauf** (basierend auf `main.py`):
1. Context Loading (Schema, Meanings, BSL, KB)
2. Ambiguity Detection (parallel zu SQL-Generation)
3. SQL Generation (mit integrierter Intent-Erkennung und BSL-Compliance-Checks)
4. SQL Validation (SQL Guard + LLM Validation)
5. Query Execution (mit Paging)
6. Result Summarization (optional)

**Dokumente sagen**:
- PROJEKT_ABGABE.md: "6-Phasen Pipeline" ✅ Konsistent
- ARCHITEKTUR_UND_PROZESSE_NEU.md: "6 Phasen" ✅ Konsistent
- Für_Präsi_NEU.md: "6 Phasen" ✅ Konsistent

**Aber**: Die Phase 2/3 Benennung ist unterschiedlich:
- Manche sagen "Question Classification" → sollte "Intent-Erkennung & BSL-Compliance" sein
- BSL-Generierung ist eigentlich Phase 1 (parallel zu Context Loading), nicht Phase 3

**Empfehlung**: Konsistente Phase-Namen und -Reihenfolge in allen Dokumenten

---

### 3. BSL-Generierung Timing

**Problem**: Dokumente sagen "Phase 3: BSL-Generierung", aber BSL wird vor SQL-Generation geladen

**Code-Realität** (`main.py` Zeile 208):
```python
kb_text, meanings_text, bsl_text = load_context_files(selected_database, Config.DATA_DIR)
```
→ BSL wird in Phase 1 (Context Loading) geladen, nicht erst in Phase 3

**Betroffene Dokumente**:
- Alle 5 Dokumente zeigen BSL-Generierung als separate Phase

**Empfehlung**: Klarstellen, dass BSL zur Laufzeit geladen wird (aus `credit_bsl.txt`), nicht generiert wird. Die Generierung erfolgt offline durch `bsl_builder.py`.

---

### 4. Version-Nummern Inkonsistenz

**Problem**: Unterschiedliche Version-Nummern in verschiedenen Dokumenten

**Code-Realität**:
- `main.py` Zeile 37: `version="2.1.0"`
- `main.py` Zeile 77: `version="2.1.0"`

**Dokumente sagen**:
- PROJEKT_ABGABE.md Zeile 6: `Version: X.0.0 (BSL-first)`
- ARCHITEKTUR_ENTSCHEIDUNGEN.md: `Version: X.0.0 (BSL-first mit modularen Regeln)`
- Für_Präsi_NEU.md Zeile 6: `Version: X.0.0 (BSL-first)`

**Empfehlung**: Konsistente Versionsnummern (wahrscheinlich X.0.0 für die Dokumentation, da das die Projekt-Version ist)

---

### 5. LLM Model Name

**Problem**: Unterschiedliche Model-Namen

**Code-Realität**:
- `config.py`: Wird aus `.env` geladen (Config.OPENAI_MODEL)
- Dokumente erwähnen verschiedene Model-Namen

**Dokumente sagen**:
- PROJEKT_ABGABE.md: "OpenAI GPT-5.2" ❌ (existiert nicht)
- ARCHITEKTUR_UND_PROZESSE_NEU.md: "OpenAI GPT-5.2" ❌
- Für_Präsi_NEU.md: "OpenAI GPT-5.2" ❌

**Empfehlung**: Korrekte Model-Bezeichnung verwenden (z.B. "GPT-4" oder "GPT-4o" oder tatsächlich verwendetes Modell) oder generisch "OpenAI LLM" sagen

---

### 6. "3-Level Validation" vs. "2-Level"

**Problem**: ADR-004 beschreibt "3-Level Validation", aber Level 3 existiert nicht klar als separate Ebene

**Code-Realität**:
- **Level 1**: `utils/sql_guard.py` - `enforce_safety()`, `enforce_known_tables()` ✅
- **Level 2**: `llm/generator.py` - `validate_sql()` ✅
- **Level 3**: BSL-Compliance ist Teil von Level 2, nicht separate Ebene ❓

**Dokumente sagen**:
- PROJEKT_ABGABE.md ADR-004: "3 Ebenen" (Level 1, 2, 3)
- ARCHITEKTUR_ENTSCHEIDUNGEN.md: "3 Ebenen"
- Aber: PROJEKT_ABGABE.md wurde korrigiert zu "2-Level" in der Tabelle

**Empfehlung**: Konsistent als "2-Level" beschreiben, mit BSL-Compliance als Teil von Level 2

---

### 7. Cache-Struktur Details

**Problem**: Caching wird erwähnt, aber Details fehlen

**Code-Realität** (`utils/cache.py`):
- `get_cached_schema()` - LRU-Cache für Schema
- `get_cached_meanings()` - TTL-Cache für Meanings
- `get_cached_query_result()` - Query-Result-Caching
- `create_query_session()`, `get_query_session()` - Session-Management für Paging

**Dokumente**: Erwähnen Caching, aber Details variieren

**Empfehlung**: Konsistente Beschreibung der Cache-Arten (LRU vs. TTL)

---

### 8. Query Optimizer vs. Query Optimization

**Problem**: Query Optimizer wird verwendet, aber nicht klar, was er macht

**Code-Realität** (`main.py` Zeile 438-443):
```python
optimizer = QueryOptimizer(db_path)
query_plan = optimizer.analyze_query_plan(generated_sql)
if query_plan.get("full_table_scan") and query_plan.get("suggestions"):
    # Nur Hinweise ausgeben, keine aktive Optimierung
```

**Dokumente**: Erwähnen "Query Optimization", aber nicht klar als "Analyse/Hinweise" vs. "aktive Optimierung"

**Empfehlung**: Klarstellen, dass Query Optimizer nur analysiert und Hinweise gibt, nicht aktiv optimiert

---

### 9. Self-Correction Loop

**Problem**: Self-Correction wird im Code verwendet, aber wenig dokumentiert

**Code-Realität** (`main.py` Zeile 312-334, 460-537):
- `generate_sql_with_correction()` wird verwendet bei niedriger Confidence oder Validation-Fehlern
- Max 2 Iterationen

**Dokumente**: Erwähnen es teilweise, aber nicht als klare Phase/Feature

**Empfehlung**: Als Teil der SQL-Generierung dokumentieren (Self-Correction bei Problemen)

---

### 10. Temperature-Einstellungen

**Problem**: Dokumente erwähnen `temperature=0.2` oder `temperature=0`, aber Code zeigt `temperature=0`

**Code-Realität** (`llm/generator.py` Zeile 36):
```python
temperature=0,
```

**Dokumente**:
- ARCHITEKTUR_ENTSCHEIDUNGEN.md: "Temperature=0.2"
- PROJEKT_ABGABE.md: Nicht explizit erwähnt
- BSL_GUIDE.md: "temperature=0" ✅

**Empfehlung**: Konsistent `temperature=0` dokumentieren

---

## 📊 Zusammenfassung der Inkonsistenzen

| # | Inkonsistenz | Schweregrad | Betroffene Dokumente |
|---|--------------|-------------|---------------------|
| 1 | Query Optimizer nicht in Komponenten-Listen | 🟡 Niedrig | Alle außer BSL_GUIDE |
| 2 | Pipeline-Phasen-Namen variieren | 🟡 Niedrig | Alle 5 |
| 3 | BSL-Generierung Timing (Phase 1 vs. Phase 3) | 🟡 Niedrig | Alle 5 |
| 4 | Version-Nummern unterschiedlich | 🟡 Niedrig | Alle 5 |
| 5 | LLM Model "GPT-5.2" (existiert nicht) | 🔴 Hoch | PROJEKT_ABGABE, ARCHITEKTUR_UND_PROZESSE, Für_Präsi |
| 6 | "3-Level" vs. "2-Level" Validation | 🟡 Niedrig | PROJEKT_ABGABE, ARCHITEKTUR_ENTSCHEIDUNGEN |
| 7 | Cache-Struktur Details fehlen | 🟢 Sehr niedrig | Alle 5 |
| 8 | Query Optimizer nur Analyse, nicht Optimierung | 🟡 Niedrig | Alle 5 |
| 9 | Self-Correction wenig dokumentiert | 🟡 Niedrig | Alle 5 |
| 10 | Temperature 0.2 vs. 0 | 🟢 Sehr niedrig | ARCHITEKTUR_ENTSCHEIDUNGEN |

---

## 🔧 Empfohlene Korrekturen (Priorität)

### 🔴 Hoch-Priorität:
1. **LLM Model Name korrigieren**: "GPT-5.2" → korrektes Modell oder generisch "OpenAI LLM"

### 🟡 Mittel-Priorität:
2. **Pipeline-Phasen konsistent benennen**: Einheitliche Phase-Namen in allen Dokumenten
3. **BSL-Loading klarstellen**: BSL wird geladen, nicht generiert zur Laufzeit
4. **Version-Nummern vereinheitlichen**: Konsistente Version in allen Dokumenten
5. **Query Optimizer dokumentieren oder entfernen**: Entweder vollständig dokumentieren oder als "intern" markieren

### 🟢 Niedrig-Priorität:
6. **Temperature konsistent dokumentieren**: `temperature=0`
7. **Self-Correction als Feature dokumentieren**: Klar als Teil der Robustheit beschreiben

---

**Letztes Update**: Januar 2026  
**Status**: Analyse abgeschlossen, Korrekturen empfohlen
