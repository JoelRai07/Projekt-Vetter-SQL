# Analyse der Logs: 10 Fragen und ihre Probleme

## Übersicht Foreign Key Beziehungen

Wichtig für JOIN-Bedingungen:
1. `employment_and_income.emplcoreref` → `core_record.coreregistry`
2. `expenses_and_assets.expemplref` → `employment_and_income.emplcoreref`
3. `bank_and_transactions.bankexpref` → `expenses_and_assets.expemplref`
4. `credit_and_compliance.compbankref` → `bank_and_transactions.bankexpref`
5. `credit_accounts_and_history.histcompref` → `credit_and_compliance.compbankref`

## Detaillierte Analyse der 10 Fragen

### Frage 1: "Can you show me the top wealthy customers with their financial value?"
**Status: ⚠️ TEILWEISE RICHTIG**
- **Generiert**: `SELECT expemplref AS customer_id, totassets, totliabs, (totassets - totliabs) AS net_worth FROM expenses_and_assets ORDER BY net_worth DESC`
- **Erwartet**: RANK() OVER (ORDER BY ... DESC NULLS FIRST) AS networth_rank, LIMIT 10
- **Problem**: Fehlt RANK() Funktion und LIMIT 10
- **Validation**: ✅ SQL ist valide (aber unvollständig)
- **Ausführung**: ✅ Erfolgreich (100 von 1000 Zeilen)

---

### Frage 2: "Please find all the customer IDs who are highly digital"
**Status: ⚠️ TEILWEISE RICHTIG**
- **Erste Generierung**: Falsche JOINs (`cr.coreregistry = cc.compbankref`, `cc.compbankref = bt.bankexpref`)
- **Korrigiert zu**: `SELECT bt.bankexpref AS customer_id FROM bank_and_transactions bt WHERE json_extract(bt.chaninvdatablock, '$.onlineuse') = 'High' AND json_extract(bt.chaninvdatablock, '$.mobileuse') = 'High'`
- **Erwartet**: Zusätzlich `json_extract(bt.chaninvdatablock, '$.autopay') = 'Yes'`
- **Problem**: Fehlt `autopay = 'Yes'` Bedingung
- **Validation**: ✅ Korrigiert akzeptiert
- **Ausführung**: ✅ Erfolgreich (109 Zeilen, aber fehlende Bedingung)

---

### Frage 3: "Can you identify all customers focused on investments..."
**Status: ⚠️ TEILWEISE RICHTIG**
- **Generiert**: `SELECT expemplref, investamt, totassets FROM expenses_and_assets WHERE investamt > 0.3 * totassets`
- **Erwartet**: JOIN mit `bank_and_transactions`, Filter auf `investport IN ('Moderate', 'Aggressive') AND investexp = 'Extensive'`
- **Problem**: 
  - Fehlt JOIN mit `bank_and_transactions`
  - Fehlt Filter auf `investport` und `investexp` aus JSON
- **Validation**: ✅ SQL ist valide
- **Ausführung**: ✅ Erfolgreich (700 Zeilen, aber falsche Logik)

---

### Frage 4: "Analyze customer credit scores by credit classification..."
**Status: ❌ FALSCH**
- **Erste Generierung**: Falsche JOINs (`cc.compbankref = cr.clientref`, `cc.compbankref = cah.histcompref`)
- **Korrigiert zu**: `SELECT CASE ... END AS credit_category, cr.clientref, ... FROM credit_and_compliance cc JOIN core_record cr ON cc.compbankref = cr.clientref`
- **Erwartet**: Nur `credit_and_compliance`, GROUP BY credit_category, COUNT und AVG
- **Problem**: 
  - Falsche JOINs (sollte keine JOINs benötigen)
  - Zeigt Kundendetails statt Aggregation
- **Validation**: ✅ Korrigiert akzeptiert
- **Ausführung**: ✅ Erfolgreich (aber falsches Ergebnis)

---

### Frage 5: "To analyze customer property leverage..."
**Status: ✅ RICHTIG (nach Korrektur)**
- **Erste Generierung**: Falsche JOINs mit `core_record` und `employment_and_income`
- **Korrigiert zu**: CTE mit JSON-Extraktion aus `expenses_and_assets.propfinancialdata`
- **Erwartet**: CTE mit JSON-Extraktion, LTV-Berechnung, Filter auf NOT NULL
- **Problem**: Erste Version hatte falsche JOINs, Korrektur funktionierte
- **Validation**: ✅ Korrigiert akzeptiert
- **Ausführung**: ✅ Erfolgreich

---

### Frage 6: "I want to analyze customer financial standing..."
**Status: ❌ FALSCH**
- **Erste Generierung**: Falsche JOINs (`cr.clientref = ea.expemplref`, `cr.clientref = cah.histcompref`)
- **Korrigiert zu**: `SELECT ea.expemplref AS customer_id, ea.networth, ei.debincratio, ei.mthincome, ea.totassets, ea.totliabs FROM expenses_and_assets ea JOIN employment_and_income ei ON ea.expemplref = ei.emplcoreref`
- **Erwartet**: JOIN mit `core_record`, Ausgabe `clientref`, Berechnung `totassets - totliabs AS net_worth`
- **Problem**: 
  - Zeigt `expemplref` statt `clientref`
  - Fehlt JOIN mit `core_record`
  - Verwendet `networth` statt Berechnung
- **Validation**: ✅ Korrigiert akzeptiert
- **Ausführung**: ✅ Erfolgreich (aber falsche Spalten)

---

### Frage 7: "To analyze digital engagement trends..."
**Status: ❌ FEHLGESCHLAGEN**
- **Generiert**: Fehlende Tabellenqualifizierung für `chaninvdatablock` (sollte `bt.chaninvdatablock` sein)
- **Fehler**: `no such column: chaninvdatablock`
- **Erwartet**: 
  - CTE mit JOINs: `core_record` → `credit_accounts_and_history` → `bank_and_transactions`
  - JSON-Extraktion aus `bt.chaninvdatablock`
  - Komplexe Berechnungen (Cohort, CES, etc.)
- **Problem**: 
  - Fehlende Tabellenqualifizierung
  - Falsche JOIN-Bedingungen
  - Komplexe Logik nicht korrekt implementiert
- **Validation**: ⚠️ SQL ist valide (aber falsch)
- **Ausführung**: ❌ Exception: `no such column: chaninvdatablock`

---

### Frage 8: "I need to analyze debt burden across different customer segments..."
**Status: ❌ FEHLGESCHLAGEN**
- **Erste Generierung**: Falsche JOINs, fehlende Spalte `totliabs` (sollte aus `expenses_and_assets` kommen)
- **Korrigiert**: UNION ALL mit unterschiedlichen Spaltenanzahlen
- **Erwartet**: Komplexe CTE-Struktur mit Medians, TDSR-Berechnung, Grand Total
- **Problem**: 
  - UNION ALL: erste SELECT hat 4 Spalten, zweite SELECT hat 3 Spalten
  - HAVING ohne GROUP BY im zweiten SELECT
  - Sehr komplexe Query nicht korrekt implementiert
- **Validation**: ❌ SQL Validation fehlgeschlagen
- **Ausführung**: ❌ Nicht ausgeführt

---

### Frage 9: "For each customer, show their ID, liquid and total assets..."
**Status: ⚠️ TEILWEISE RICHTIG**
- **Erste Generierung**: Falsche JOINs (`ei.employerref = c.coreregistry`)
- **Korrigiert zu**: `SELECT ea.expemplref AS customer_id, ea.liqassets, ea.totassets, (ea.liqassets / NULLIF(ei.mthincome, 0)) AS liquidity_measure, ei.mthincome, ea.investamt, CASE ... END AS investment_potential FROM expenses_and_assets ea JOIN employment_and_income ei ON ea.expemplref = ei.emplcoreref`
- **Erwartet**: 
  - ALR = `liqassets / totassets` (nicht `liqassets / mthincome`)
  - `clientref` statt `expemplref`
  - `target_status` statt `investment_potential` mit anderen Bedingungen
- **Problem**: 
  - Falsche Liquiditätsberechnung
  - Falsche Spaltenausgabe
  - Falsche CASE-Logik
- **Validation**: ✅ Korrigiert akzeptiert
- **Ausführung**: ✅ Erfolgreich (aber falsche Metriken)

---

### Frage 10: "To pinpoint customers who might be facing financial hardship..."
**Status: ❌ FEHLGESCHLAGEN**
- **Erste Generierung**: Falsche JOINs (`ei.emplcoreref = ea.expemplref` sollte korrekt sein, aber `cc.compbankref = cr.clientref` ist falsch)
- **Korrigiert**: CTE mit falschen JOINs, Column 'delinqcount' nicht grouped
- **Erwartet**: 
  - JOIN: `core_record` → `employment_and_income` → `expenses_and_assets` → `credit_and_compliance`
  - JOIN-Bedingung: `cc.compbankref = ei.emplcoreref` (über `bank_and_transactions` Kette)
  - Filter: `FVS > 0.7 AND (delinqcount > 0 OR latepaycount > 0) AND net_worth < 0`
- **Problem**: 
  - Falsche JOIN-Bedingungen (sollte über `bank_and_transactions` Kette gehen)
  - Korrektur-Loop schlug fehl
- **Validation**: ❌ SQL Validation fehlgeschlagen
- **Ausführung**: ❌ Nicht ausgeführt

---

## Zusammenfassung der Hauptprobleme

### 1. **Foreign Key JOIN-Bedingungen werden nicht korrekt verwendet**
   - Häufig werden JOINs erraten statt die FOREIGN KEY Constraints zu verwenden
   - Problem: `cr.clientref = ea.expemplref` (falsch) statt über `emplcoreref` Kette
   - Problem: `cc.compbankref = cr.clientref` (falsch) statt über `bank_and_transactions` Kette

### 2. **JSON-Pfade werden aus falschen Tabellen extrahiert**
   - `chaninvdatablock` ist in `bank_and_transactions`, nicht in `core_record`
   - Fehlende Tabellenqualifizierung: `chaninvdatablock` statt `bt.chaninvdatablock`

### 3. **Komplexe Queries werden nicht vollständig umgesetzt**
   - UNION ALL mit unterschiedlichen Spaltenanzahlen
   - HAVING ohne GROUP BY
   - CTEs werden nicht korrekt strukturiert

### 4. **Vollständigkeit der Filter wird übersehen**
   - Frage 2: Fehlt `autopay = 'Yes'`
   - Frage 3: Fehlen JSON-Filter auf `investport` und `investexp`

### 5. **Falsche Metriken/Berechnungen**
   - Frage 9: Liquidity = `liqassets / mthincome` statt `liqassets / totassets`
   - Frage 6: Verwendet `networth` Spalte statt Berechnung `totassets - totliabs`

### 6. **Fehlende Aggregations-Funktionen**
   - Frage 1: Fehlt `RANK() OVER (...)`
   - Frage 4: Zeigt Details statt Aggregationen

### 7. **Falsche Spaltenausgabe**
   - Verwendet `expemplref` statt `clientref` (wenn `core_record` benötigt wird)

