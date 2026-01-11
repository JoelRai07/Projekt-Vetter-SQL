# Database Routing (v2.1.0)

## Kurzbeschreibung

Das System implementiert ein **LLM-gestütztes Database Routing**, das automatisch die passende Datenbank auswählt, wenn der Nutzer keine explizite DB-Auswahl trifft oder `auto_select=true` setzt. Dies vereinfacht das Onboarding und ermöglicht eine transparente Multi-DB-Nutzung.

## Warum
- **Vereinfachtes Onboarding** für neue Nutzer (keine manuelle DB-Auswahl nötig)
- **Automatische DB-Erkennung** bei vagen Anfragen
- **Ambiguity Detection** → Klärungsfragen statt stiller Fehler
- **Fallback-Mechanismus** wenn Confidence zu niedrig ist

## Ablauf - Zwei Routing-Modi

### Modus 1: Standalone `/route` Endpoint

```
POST /route
Input:  { "question": "Zeige mir Kreditrisiken" }

1. Backend listet verfügbare DBs unter Config.DATA_DIR
2. Für jede DB wird Profil erstellt (schema_snippet, kb_snippet, meanings_snippet)
3. LLM bewertet Profile anhand der Frage
4. Rückgabe: selected_database + confidence

Output: 
{
  "selected_database": "credit",
  "confidence": 0.82,
  "question": "Zeige mir Kreditrisiken"
}

oder bei niedriger Confidence:
{
  "selected_database": null,
  "confidence": 0.35,
  "ambiguity_check": {
    "is_ambiguous": true,
    "reason": "Datenbank unklar",
    "questions": ["Verfügbare Datenbanken: credit, museum, ..."]
  }
}
```

### Modus 2: Automatisches Routing in `/query`

Das **Routing ist in den `/query` Endpoint integriert**:

```
POST /query
Input: 
{
  "question": "Zeige mir Kreditrisiken",
  "database": null,          // ← Nicht gesetzt
  "auto_select": true        // ← oder true
}

Ablauf:
1. Backend prüft: Ist database gesetzt UND auto_select=false?
   - JA → Routing **überspringen**, direkt zur SQL-Generierung
   - NEIN → Weiter zu Schritt 2

2. Routing durchführen (wie /route):
   - DB-Profile erstellen
   - LLM bewerten
   - confidence >= THRESHOLD (0.55)?
     - JA → DB auswählen, SQL generieren
     - NEIN → AmbiguityResult zurückgeben, STOP
     
3. Falls routing erfolgreich:
   - Weiter mit SQL-Generierung
   - Cache prüfen (5 Min TTL)
   - Query ausführen & Ergebnisse paginieren
```

## Implementierung Details

### Funktionen & Module

| Funktion | Datei | Zweck |
|----------|-------|-------|
| `list_available_databases()` | `backend/main.py` L61-72 | Liest `Config.DATA_DIR`, findet DB-Ordner mit `<name>.sqlite` |
| `build_database_profiles()` | `backend/main.py` L74-92 | Erstellt Profil pro DB (schema/kb/meanings snippets) |
| `route_database()` (async) | `backend/main.py` L121-166 | FastAPI `/route` Endpoint |
| `route_database()` (Aufruf in `/query`) | `backend/main.py` L213-255 | Auto-Routing integriert in Query-Pipeline |
| `llm_generator.route_database()` | `backend/llm/generator.py` L222-244 | Kernlogik: LLM bewertet Profile, gibt selected_database + confidence |
| `get_query_session()` / `create_query_session()` | `backend/utils/cache.py` | Session-Management für Paging & Kontext |

### Konfiguration & Thresholds

```python
CONFIDENCE_THRESHOLD_LOW = 0.4        # Sehr niedriges Vertrauen
ROUTE_CONFIDENCE_THRESHOLD = 0.55     # Schwellenwert für Auto-Routing
MAX_PROFILE_SCHEMA_CHARS = 1500       # Limit für Schema-Snippet
MAX_PROFILE_KB_CHARS = 1200           # Limit für KB-Snippet
MAX_PROFILE_MEANINGS_CHARS = 1200     # Limit für Meanings-Snippet
```

### DB-Pfad-Pattern

```python
# Beispiel: Datenbank "credit" aus Config.DATA_DIR="mini-interact"
db_path = os.path.join("mini-interact", "credit", "credit.sqlite")
# Ergebnis: mini-interact/credit/credit.sqlite
```

### Profil-Struktur

```python
profile = {
    "database": "credit",
    "schema_snippet": "CREATE TABLE core_record (id INT, ...) [first 1500 chars]",
    "kb_snippet": "• DTI: Debt-to-Income Ratio ...\n• CUR: Credit Utilization ... [first 1200 chars]",
    "meanings_snippet": "• id: Customer ID, unique key\n• debincratio: Debt-to-Income ... [first 1200 chars]"
}
```

## API Response-Modelle

### RouteResponse (für `/route`)

```json
{
  "question": "Zeige mir Kreditrisiken",
  "selected_database": "credit",
  "confidence": 0.82,
  "ambiguity_check": null,
  "error": null
}
```

### QueryResponse (für `/query` mit Auto-Routing)

```json
{
  "question & Limitierungen

### ✅ Vorteile

- **Bessere UX**: Nutzer müssen DB nicht manuell auswählen
- **Schnelle Onboarding**: Multi-DB-System ist transparent
- **Robust**: Fallback auf AmbiguityResult statt stiller Fehler
- **Kosteneffizient**: Routing wird gecacht (1h TTL), Profile sind klein (max 4.2 KB zusammen)
- **Paging-Optimierung**: Sessions ermöglichen Routing-Übersprung bei Pagination

### ⚠️ Limitierungen

- **LLM-abhängig**: Routing-Qualität hängt von OpenAI Modell ab
- **Cross-DB-Anfragen**: Nicht unterstützt (eine Query = eine DB)
- **Profile-Größe**: Großschriftschemata können gekürzt werden (MAX_PROFILE_*_CHARS)
- **Confidence ist subjektiv**: Schwellenwert (0.55) ist empirisch gewählt

## Mögliche Erweiterungen

- [ ] **Caching der Routing-Scores** – Profile-Scores zwischen Sessions teilen
- [ ] **Opt-in/Opt-out per ENV** – `ENABLE_AUTO_ROUTING=false`
- [ ] **UI-Feedback**: Warum wurde DB gewählt? (Top-3 Gründe)
- [ ] **Kontextuelle DB-Erinnerung**: "Bei letzter Frage zu 'credit'..." → Default setzen
- [ ] **Cross-DB-Joins**: Mehrere DBs in einer Query (Advanced
  "total_rows": 47,
  "has_next_page": false,
  "has_previous_page": false
}
```

## Integration mit Query-Session & Paging

Das Routing ist **eng mit dem Session-Management verknüpft**:

```
Erste Anfrage:
POST /query { question: "...", database: null, auto_select: true }
  → Routing durchführen → DB auswählen
  → SQL generieren, ausführen
  → query_id erstellen (für Paging)
  → Seite 1 zurückgeben

Paging-Anfrage:
POST /query { question: "...", query_id: "a1b2c3d4...", page: 2 }
  → Session abrufen (query_id → { database, sql, question })
  → Routing **überspringen** (bereits gemacht!)
  → Seite 2 ausführen
  → Ergebnisse zurückgeben
```

**Wichtig**: Ist eine `query_id` vorhanden, wird Routing übersprungen! Dies spart ~2-3 Sekunden pro Paging-Request.

## Fehler & Fallbacks

| Szenario | Verhalten |
|----------|-----------|
| Keine DBs unter `Config.DATA_DIR` | Error: `"Keine Datenbanken gefunden..."` |
| LLM-Fehler beim Routing | Error: `"Routing fehlgeschlagen: ..."` + Exception |
| Confidence < THRESHOLD (0.55) | AmbiguityResult mit Klärungsfragen |
| query_id ungültig/abgelaufen | Error: `"Unbekannte query_id"` (Session TTL: 1 Stunde) |
| DB-Wechsel mid-Paging | Error: `"query_id passt nicht zur angefragten DB"` |

## Frontend-Integration

### Usecase 1: Dropdown-Vorauswahl (mit `/route`)

```javascript
// Nutzer tippt Frage ein, soll Dropdown-Auswahl vorgefüllt werden
const response = await fetch('/route', {
  method: 'POST',
  body: JSON.stringify({ question: userInput })
});
const { selected_database, confidence } = await response.json();

if (confidence > 0.55) {
  dropdown.value = selected_database; // Vorauswahl
} else {
  showAmbiguityDialog(response.ambiguity_check);
}
```

### Usecase 2: Automatisches Routing (mit `/query`)

```javascript
// Nutzer sendet Frage ohne DB-Auswahl
const response = await fetch('/query', {
  method: 'POST',
  body: JSON.stringify({
    question: userInput,
    database: null,
    auto_select: true
  })
});

if (response.ambiguity_check) {
  showAmbiguityDialog(response.ambiguity_check);
} else {
  displayResults(response.results, response.query_id);
}
```

### Usecase 3: Paging mit Session

```javascript
// Nutzer navigiert zu Seite 2
const response = await fetch('/query', {
  method: 'POST',
  body: JSON.stringify({
    question: userInput,
    query_id: savedQueryId,  // ← Session-ID
    page: 2,
    page_size: 100
  })
});
// Routing wird automatisch übersprungen!
displayResults(response.results);
```

## Vorteile
- Bessere UX
- Geringerer Einstiegsaufwand
- Konsistente DB-Auswahl bei häufiger Nutzung

## Mögliche Erweiterungen
- Caching der Profil-Scores
- Opt-in/Opt-out für automatisches Routing per ENV
- UI-Feedback: warum eine DB gewählt wurde (Top-3 Gründe)
