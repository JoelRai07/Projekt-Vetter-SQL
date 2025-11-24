# ChatWithYourData – Text2SQL Projekt 📌

## Übersicht

Dieses Projekt wurde im Rahmen des Moduls "Projekt" an der DHBW Stuttgart entwickelt. Ziel ist es, eine Anwendung zu erstellen, die es Nutzer:innen ermöglicht, natürliche Sprache zu verwenden, um SQL-Abfragen automatisch zu generieren und eine Datenbank abzufragen. Dazu wird ein Large Language Model (LLM) eingebunden, das Text → SQL übersetzt.

Das Projekt basiert auf dem Benchmark-Datensatz **BIRD-INTERACT (mini-interact)**. Die Hauptaufgabe besteht darin, die bereitgestellten Fragen korrekt zu beantworten, indem die Anwendung dynamisch SQL-Abfragen erzeugt und ausführt.

## 🎯 Projektziele

- Entwicklung eines funktionierenden Text2SQL-Prototyps
- Nutzung moderner LLM-Technologien zur automatischen SQL-Generierung
- Erstellung einer Architektur, die Frontend, Backend, LLM und Datenbank verbindet
- Umsetzung der im Modul geforderten Methoden des Software Engineerings, Projektmanagements und Teamarbeit

## 🧠 Motivation

Daten sind das Gold des 21. Jahrhunderts – jedoch ist SQL für viele Mitarbeitende eine Hürde. Moderne KI-Modelle ermöglichen es, natürliche Sprache effizient zu interpretieren.

Mit diesem Projekt helfen wir Unternehmen dabei, **data-driven** zu werden, indem wir die Distanz zwischen Mensch und Datenbank reduzieren.

## 🛠️ Technologie-Stack

### Backend

- **Node.js / Express**
- Anbindung eines LLM (z. B. GPT-4.1, GPT-4o-mini, o3-mini, Claude 3.5 Sonnet)
- **SQLite** für den mini-interact Datensatz
- SQL Execution Layer

### Frontend

- Einfaches Chat-Interface (z. B. **React**)
- Anfrage → Backend → Antwortfluss

### Weitere Tools

- **GitHub** (Versionierung, Projektmanagement)
- ggf. **n8n** für explorative Low-Code-Prototypen

## 🧪 Datensatz

- **Mini-Interact Benchmark Datensatz der BIRD-Initiative**
- **Fragen:** `mini_interact.jsonl` (instance_id: credit_1 – credit_10)
- **Datenbank:** `credit.sqlite`

### Zusatzinfos:

- `credit_column_meaning_base.json`
- `credit_kb.jsonl`

**Wichtig:** Die offiziellen Lösungen liegen in Moodle und dürfen nicht dem LLM zugänglich gemacht werden.

## ⚙️ Funktionsweise

1. **Nutzer gibt natürliche Sprache ein** → z. B.  
   _„Wie viele Kund:innen haben einen Kredit über 10.000 Euro?“_

2. **Backend verarbeitet Eingabe**
   - Fragt LLM mit Schema + Prompt + Few-Shot-Beispielen an
   - LLM generiert SQL

3. **Backend führt SQL aus**
   - SQLite-Abfrage

4. **Backend gibt Antwort zurück**
   - Ergebnis wird ins Frontend zurückgespielt

  ## 📝 Architekturentscheidungen (ADR)

Beispielhafte Entscheidungen:

- Warum wir OpenAI/Claude als LLM gewählt haben
- Warum wir Few-Shot Prompting statt Fine-Tuning nutzen
- Wahl von Express.js statt Python FastAPI
- Sicherheitsüberlegungen (kein Zugriff auf Lösungen)

## 🧪 Tests

- **SQL-Ausführungstests**
- **Validierung der generierten Queries**
- **Evaluation der LLM-generierten Antworten**
- **Handling von Edge Cases** (invalid SQL, leere Antworten, etc.)

## 🚧 Bekannte Limitierungen

- LLM kann SQL halluzinieren
- Fehlende Kontextinformation → komplexe Joins schwierig
- Performance abhängig vom LLM
- Kein Fine-Tuning auf BIRD-Datensatz

## 🚀 Erweiterungsmöglichkeiten

- Unterstützung mehrerer Datenbanken (DB-Auswahlproblem lösen)
- Automatisierte Schema-Extraktion
- SQL-Korrektur mittels Self-Refinement
- Integration Open-Source-LLMs (Llama 3.1 / Qwen / DeepSeek) via Ollama
- Low-Code Automation Layer mit n8n

## 📅 Projektmanagement-Komponenten

- **Gruppengröße:** ~5 Studierende
- **Tickets zu:** Frontend, Backend, LLM-Anbindung, Testing, Evaluation, Doku
- **Regelmäßige Sprint Reviews**
- **Nutzung eines Kanban-Boards**
- **Abschlusspräsentation:** 20 Min + 10 Min Q&A

## 🧭 Selbstreflexion (für die Abgabe)

- Was lief gut?
- Was hat nicht gut funktioniert?
- Wie könnte man im nächsten Projekt besser zusammenarbeiten?
- Welche Rolle habe ich im Team eingenommen?

## 📖 Lizenz

Dieses Projekt dient ausschließlich zu Studienzwecken an der DHBW Stuttgart.

## 👥 Team

Tim Kühne, Dominik Ruoff, Joel Martinez, Umut Polat, Sören Frank
