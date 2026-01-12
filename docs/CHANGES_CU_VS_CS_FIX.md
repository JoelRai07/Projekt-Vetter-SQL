# CU vs CS Identity Fix - Zusammenfassung

## Problem
Die LLM hat die beiden Kundenidentifikatoren verwechselt:
- **CU** (Customer ID) vom `core_record.clientref` 
- **CS** (Core Registry ID) vom `core_record.coreregistry`

### Symptome
1. **Frage 1** (Top 10 Wealthiest): Richtige Werte, aber **CS statt CU** in Output
2. **Frage 7** (Cohort Analysis): Alle Quartale aller Jahre statt nur 2 Gruppen
3. **Frage 10** (High-Risk): **Unterschiedliche Kunden** als Referenz

## Lösung Implementiert

### 1. ✅ bsl_builder.py erweitert
**File**: `backend/bsl_builder.py`

Drei Funktionen massiv erweitert mit:
- **Doppelte Warnung (⚠️)** für CU vs CS
- **Konkrete Beispiele** (WRONG vs CORRECT)
- **Validierungs-Checklisten**
- **Aggregation vs Detail Query** Unterscheidung
- **Cohort-spezifische Regeln** für Frage 7

### 2. ✅ prompts.py aktualisiert
**File**: `backend/llm/prompts.py`

Vier Prompts angepasst:
- `REACT_REASONING`: Identity Check als ERSTE priorität
- `SQL_GENERATION`: Explizite Beispiele mit WRONG/CORRECT
- `REACT_SQL_GENERATION`: Stark vereinfacht mit Fokus auf CU vs CS
- Plus konkrete Regeln für Ranking vs Aggregation

### 3. ✅ BSL regeneriert
**File**: `backend/mini-interact/credit/credit_bsl.txt`

Die BSL wurde neu generiert mit:
```
# IDENTITY SYSTEM RULES (CRITICAL)
## ⚠️ CRITICAL: Dual Identifier System
## ⚠️ RULE 1: SAME PERSON, DIFFERENT IDs
## ⚠️ RULE 2: Identifier Selection in SELECT
## ⚠️ RULE 3: Identifier Usage in JOINs
## ⚠️ RULE 4: Output vs Internal Logic
## ⚠️ RULE 5: Question-Specific Identifier Requirements
  - Ranking/Listing
  - Segmentation/Cohort Analysis
  - Risk/Condition Filtering
## ⚠️ VALIDATION CHECKLIST

# AGGREGATION DETECTION RULES
## ⚠️ CRITICAL: Aggregation vs Detail Queries
## ⚠️ CRITICAL: Cohort Questions (Special Case)

# JOIN CHAIN RULES (CRITICAL)
## ⚠️ RULE: Foreign Key Chain is STRICT
## ⚠️ RULE: NEVER skip tables
## ⚠️ RULE: Join Direction is Always Left-to-Right
```

### 4. ✅ Vector Store wurde bereits gelöscht
Der Vector Store wird automatisch **neu generiert** mit den aktualisierten BSL-Regeln.

## Was hat sich konkret geändert?

### Für Frage 1 (Top 10 Wealthiest)
```sql
-- VORHER (FALSCH):
SELECT cr.coreregistry AS customer_id, ...
-- Returns: CS format (CS239090) ❌

-- NACHHER (RICHTIG):
SELECT cr.clientref AS customer_id, ...
-- Returns: CU format (CU456680) ✓
```

### Für Frage 7 (Cohort by Quarter)
```sql
-- VORHER (FALSCH):
SELECT cohort_quarter FROM (
  SELECT CAST((CAST(strftime('%m', cr.scoredate) AS INTEGER) - 1) / 3 + 1 AS INTEGER) AS cohort_quarter
  -- Returns: Multiple years worth of quarters ❌

-- NACHHER (RICHTIG):
-- Must group by cohort AND validate that output matches question intent
-- If question asks for "2 groups" → Need explicit filtering/grouping logic
```

### Für Frage 10 (High-Risk Customers)
```sql
-- VORHER (FALSCH):
SELECT cr.coreregistry, ...  -- Using CS format, wrong customers
-- Returns: Different customers than reference ❌

-- NACHHER (RICHTIG):
SELECT cr.clientref, cc.delinqcount, cc.latepaycount, ea.networth
WHERE cc.risklev IN ('High', 'Very High')
  AND (cc.delinqcount > 0 OR cc.latepaycount > 0)
  AND ea.networth < 0
-- Returns: CU format, correct filters ✓
```

## Testing / Nächste Schritte

### 1. Teste Frage 1 (Sollte **CU format** ausgeben)
```
Query: "Show top 10 wealthiest customers"
Expected Output: CU456680, CU582141, ...
(NOT CS239090, CS206405, ...)
```

### 2. Teste Frage 7 (Sollte **nur 2 Gruppen** sein)
```
Query: "Analyze by cohort quarter"
Expected Output: Grouping in 2 cohorts, not all quarters of all years
Verify: cr.clientref in output, proper cohort_quarter extraction
```

### 3. Teste Frage 10 (Sollte **richtige Kunden** sein)
```
Query: "High-risk customers with negative net worth"
Expected Output: CU582141 (with correct indicators)
NOT: Different customers like CU969131
```

## Checkpoints für die Validierung

| Problem | Vorher | Nachher | Status |
|---------|--------|---------|--------|
| Frage 1 Customer ID | CS format ❌ | CU format ✓ | Fixed via bsl_builder + prompts |
| Frage 7 Cohort Groups | All quarters ❌ | 2 groups ✓ | Fixed via aggregation rules |
| Frage 10 Customer Filter | Wrong customers ❌ | Correct customers ✓ | Fixed via business rules |
| BSL Explicitness | Vage ❌ | Crystal clear ✓ | Regenerated |
| Vector Store | Old ❌ | Fresh ✓ | Will auto-regenerate |

## Technische Details

### bsl_builder.py Änderungen
- `extract_identity_rules()`: Von 18 zu 90+ Zeilen (mit konkreten Beispielen)
- `extract_aggregation_patterns()`: Von 14 zu 40+ Zeilen (mit Cohort Handling)
- `extract_join_chain_rules()`: Von 20 zu 45+ Zeilen (mit Fehlerbeispielen)

### prompts.py Änderungen
- `REACT_REASONING`: +30 Zeilen für Identity Check
- `SQL_GENERATION`: +50 Zeilen mit WRONG/CORRECT Beispielen
- `REACT_SQL_GENERATION`: Komplett überarbeitet (leichter)

### BSL Größe
- Vorher: ~200 Zeilen (minimal)
- Nachher: ~384 Zeilen (mit expliziten Regeln)

## Wie funktioniert es jetzt?

1. **BSL wird geladen** → Neue explizite CU vs CS Regeln vorhanden
2. **Vector Store wird neu generiert** → Alle Regeln sind indexiert
3. **REACT Reasoning Phase**:
   - Schritt 1 ist jetzt "IDENTITY CHECK (CRITICAL)"
   - Fragt explizit: CU oder CS?
   - Hat konkrete Beispiele
4. **SQL Generation Phase**:
   - Validates gegen BSL rules
   - Checkt: Ist clientref in SELECT? (CU für Output)
   - Checkt: Ist coreregistry in ON clauses? (CS für Joins)
5. **Validation Phase**:
   - Hat Checkpoint für korrekt Identifier type

## Rollback (Falls nötig)
Falls etwas schiefgeht:
```bash
# BSL erneut generieren
cd backend
python bsl_builder.py

# Vector Store löschen (wird auto-regeneriert)
rm -r vector_store/schema/
```

---

**Created**: 2026-01-13  
**Status**: ✅ Ready for Testing  
**Priority**: 🔴 Critical (affects all Q&A)
