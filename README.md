# Text2SQL System - Projekt-Vetter-SQL

Ein vollständiges System zur Übersetzung von natürlicher Sprache in SQL-Abfragen.

## 🚀 Quick Start

### Backend starten
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend starten
```bash
cd frontend
npm install
npm run dev
```

## 📚 Dokumentation

**Vollständige Dokumentation**: Siehe [DOKUMENTATION.md](./DOKUMENTATION.md)

Die Dokumentation erklärt:
- ✅ **Was** wurde gebaut (Projektübersicht)
- ✅ **Wofür** wurde es gebaut (Anwendungsfälle)
- ✅ **Wozu** wurde es gebaut (Ziele)
- ✅ **Wie** funktioniert es (Architektur, Datenfluss, Code)
- ✅ **Warum** wurden bestimmte Technologien/Entscheidungen getroffen

## 🏗️ Architektur

```
Frontend (React) → FastAPI Backend → OpenAI GPT-4o-mini → SQLite Database
```

## ✨ Features

- 🤖 **Automatische SQL-Generierung** aus natürlicher Sprache
- 🔍 **Ambiguity Detection** - Erkennt mehrdeutige Fragen
- ✅ **Multi-Layer Validation** - Sicherheit + Korrektheit
- 📄 **Paging** - Navigation durch große Ergebnis-Sets
- 📊 **Result Summarization** - Verständliche Zusammenfassungen
- 🔒 **SQL Guard** - Sicherheitsprüfungen

## 🛠️ Technologie-Stack

**Backend:**
- FastAPI (REST API)
- OpenAI GPT-4o-mini (LLM)
- SQLite (Datenbank)
- Pydantic (Validierung)

**Frontend:**
- React (UI)
- Vite (Build Tool)

## 📖 Verwendung

1. Öffne Frontend im Browser
2. Stelle eine Frage in natürlicher Sprache
3. System generiert SQL und zeigt Ergebnisse
4. Navigiere durch Seiten bei großen Ergebnissen

**Beispiel-Fragen:**
- "Zeige alle Kunden mit Einkommen über 50000"
- "Berechne den Durchschnitt des Net Worth"
- "Welche Kunden haben die höchste Debt-to-Income-Ratio?"

## 📁 Projektstruktur

```
backend/
├── main.py              # FastAPI App
├── models.py            # Pydantic Models
├── database/            # Database Manager
├── llm/                 # LLM Generator & Prompts
└── utils/               # Helper Functions

frontend/
├── src/
│   ├── App.jsx         # Main Component
│   └── App.css         # Styles
└── package.json
```

## 🔐 Sicherheit

- **SQL Guard**: Verhindert gefährliche Operationen (DELETE, DROP, etc.)
- **Table Validation**: Prüft ob nur bekannte Tabellen verwendet werden
- **LLM Validation**: Semantische Validierung der generierten SQL

## 📝 License

Projekt für DHBW Stuttgart - Projekt Modul

---

**Für detaillierte Informationen siehe [DOKUMENTATION.md](./DOKUMENTATION.md)**
