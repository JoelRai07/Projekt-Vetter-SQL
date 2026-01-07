# Database Routing (v6.0.0)

## Kurzbeschreibung

Die Version 6.0.0 führt ein LLM-gestütztes Database-Routing ein. Ziel ist es, die passende Beispiel-Datenbank automatisch auszuwählen, wenn der User keine `database` im Request angibt oder `auto_select` aktiviert hat.

## Warum
- Vereinfachtes Onboarding für neue Nutzer
- Keine manuelle DB-Auswahl mehr bei vielen Demo-DBs (z.B. `museum`, `credit`, `crypto`)

## Verhalten / Ablauf
1. Backend listet verfügbare DBs unter `Config.DATA_DIR`.
2. Für jede DB wird ein kurzes Profil erstellt (`schema_snippet`, `kb_snippet`, `meanings_snippet`).
3. Das LLM (Generator.route_database) bewertet die Profile und gibt `selected_database` und `confidence` zurück.
4. Ist `confidence` >= `ROUTE_CONFIDENCE_THRESHOLD` → DB wird automatisch gewählt.
5. Ist `confidence` < `ROUTE_CONFIDENCE_THRESHOLD` → Rückgabe eines `AmbiguityResult` mit Klärungsfragen.

## Implementierung (Backend)
- Funktionen/Module:
  - `list_available_databases()` — Liest `Config.DATA_DIR` und findet DB-Ordner mit `<name>.sqlite`.
  - `build_database_profiles(db_names)` — Generiert pro DB ein kurzes Profil (Schema/KB/Meanings Snippets).
  - `route_database` — LLM-Aufruf, der anhand der Profile die beste DB auswählt.
- Konfiguration:
  - `Config.DATA_DIR` (z.B. `mini-interact`)
  - `ROUTE_CONFIDENCE_THRESHOLD` (siehe `backend/main.py`)
- DB-Pfad-Pattern:
  - `os.path.join(Config.DATA_DIR, db_name, f"{db_name}.sqlite")`

## API
- `POST /route`
  - Input: `{ "question": "..." }` + optionales Profil-Array
  - Output: `{ "selected_database": "museum", "confidence": 0.82 }` oder Ambiguity-Objekt

## Fehler & Fallbacks
- Fehlende DB: Sauberer Fehler mit Hinweis auf `Config.DATA_DIR`.
- Niedrige Confidence: AmbiguityResult mit Nachfragen statt falscher automatischer Wahl.

## Hinweise für Frontend
- Frontend kann `POST /route` verwenden, um die Dropdown-Auswahl vorzubelegen.
- Bei AmbiguityResult: UI sollte Klärungsfragen anzeigen und Benutzerwahl erlauben.

## Code-Locations
- `backend/main.py` — Routing-Flow, `list_available_databases`, `build_database_profiles`
- `backend/config.py` — `Config.DATA_DIR`
- `backend/llm/generator.py` — ggf. `route_database`-Aufruf

## Vorteile
- Bessere UX
- Geringerer Einstiegsaufwand
- Konsistente DB-Auswahl bei häufiger Nutzung

## Mögliche Erweiterungen
- Caching der Profil-Scores
- Opt-in/Opt-out für automatisches Routing per ENV
- UI-Feedback: warum eine DB gewählt wurde (Top-3 Gründe)
