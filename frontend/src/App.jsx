import { useState, useRef, useEffect } from "react";
import "./App.css";

function SunIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="4.5" />
      <line x1="12" y1="2" x2="12" y2="5" />
      <line x1="12" y1="19" x2="12" y2="22" />
      <line x1="4.22" y1="4.22" x2="6.34" y2="6.34" />
      <line x1="17.66" y1="17.66" x2="19.78" y2="19.78" />
      <line x1="2" y1="12" x2="5" y2="12" />
      <line x1="19" y1="12" x2="22" y2="12" />
      <line x1="4.22" y1="19.78" x2="6.34" y2="17.66" />
      <line x1="17.66" y1="6.34" x2="19.78" y2="4.22" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24">
      <path d="M21 14.5A8.5 8.5 0 0 1 10.23 3.06 7 7 0 1 0 21 14.5z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24">
      <path d="M5 4l14 8-14 8V4z" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg className="icon-sm" viewBox="0 0 24 24">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="icon-sm" viewBox="0 0 24 24">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  const textareaRef = useRef(null);
  const messagesEndRef = useRef(null);
  const isDark = theme === "dark";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [question]);

  const toggleTheme = () => {
    setTheme(isDark ? "light" : "dark");
  };

  const simulateAPICall = async (userQuestion) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const responses = [
      {
        sql: "SELECT name, email, created_at FROM users WHERE status = 'active' ORDER BY created_at DESC LIMIT 10;",
        result:
          "Ich habe 10 aktive Benutzer gefunden. Die neuesten sind: Max Müller (max@example.com), Anna Schmidt (anna@example.com), und Peter Weber (peter@example.com). Alle wurden in den letzten 30 Tagen erstellt.",
        tableData: [
          { name: "Max Müller", email: "max@example.com", created_at: "2025-11-20" },
          { name: "Anna Schmidt", email: "anna@example.com", created_at: "2025-11-18" },
          { name: "Peter Weber", email: "peter@example.com", created_at: "2025-11-15" },
        ],
      },
      {
        sql: "SELECT COUNT(*) as total, AVG(amount) as avg_amount FROM orders WHERE date >= '2025-11-01';",
        result:
          "Im November 2025 wurden insgesamt 1.247 Bestellungen mit einem Durchschnittswert von 89,42 € erfasst.",
        tableData: [{ total: 1247, avg_amount: "89.42 €" }],
      },
    ];

    return responses[Math.floor(Math.random() * responses.length)];
  };

  const handleSubmit = async () => {
    if (!question.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: "user",
      content: question.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setIsLoading(true);

    try {
      const response = await simulateAPICall(question);

      const assistantMessage = {
        id: Date.now() + 1,
        type: "assistant",
        content: response.result,
        sql: response.sql,
        tableData: response.tableData,
        showSQL: false,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: "error",
        content:
          "Es gab ein Problem bei der Verarbeitung Ihrer Anfrage. Bitte versuchen Sie es erneut.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleSQL = (messageId) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, showSQL: !msg.showSQL } : msg))
    );
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const exampleQuestions = [
    "Zeige mir alle aktiven Benutzer",
    "Wie viele Bestellungen gab es diesen Monat?",
    "Welche Produkte sind am beliebtesten?",
  ];

  return (
    <div className={`app ${isDark ? "dark" : "light"}`}>
      <header className="header">
        <div className="brand">Projekt-Vetter-Version-1.0.1</div>
        <button
          type="button"
          className="theme-btn"
          onClick={toggleTheme}
          aria-label={isDark ? "Helles Design" : "Dunkles Design"}
        >
          {isDark ? <SunIcon /> : <MoonIcon />}
        </button>
      </header>

      <main className="main">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="hero">
              <h1 className="hero-title">Welche Frage haben Sie?</h1>
              <p className="hero-subtitle">
                Formulieren Sie Ihre Frage in natürlicher Sprache – wir übernehmen die Übersetzung
                in Datenabfragen.
              </p>
              <div className="examples">
                {exampleQuestions.map((q, i) => (
                  <button key={i} className="example-btn" onClick={() => setQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.type}`}>
                  <div className="message-label">
                    {msg.type === "user" ? "Sie" : msg.type === "error" ? "Fehler" : "Assistent"}
                  </div>
                  <div className="message-content">
                    <div>{msg.content}</div>

                    {msg.tableData && (
                      <div className="data-table">
                        <table>
                          <thead>
                            <tr>
                              {Object.keys(msg.tableData[0]).map((key) => (
                                <th key={key}>{key}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {msg.tableData.map((row, i) => (
                              <tr key={i}>
                                {Object.values(row).map((val, j) => (
                                  <td key={j}>{val}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {msg.sql && (
                      <div className="sql-section">
                        <button className="sql-toggle" onClick={() => toggleSQL(msg.id)}>
                          <CodeIcon />
                          {msg.showSQL ? "SQL ausblenden" : "SQL anzeigen"}
                        </button>
                        {msg.showSQL && (
                          <div className="sql-code">
                            <button
                              className="copy-btn"
                              onClick={() => copyToClipboard(msg.sql, msg.id)}
                            >
                              {copiedId === msg.id ? <CheckIcon /> : <CopyIcon />}
                              {copiedId === msg.id ? "Kopiert!" : ""}
                            </button>
                            <pre>{msg.sql}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="message assistant">
                  <div className="message-label">Assistent</div>
                  <div className="loading">
                    <div className="loading-dots">
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                    </div>
                    <span>Denkt nach...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              className="input"
              placeholder="Stellen Sie eine Frage zu Ihren Daten…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isLoading}
            />
            <button
              type="button"
              className="send-btn"
              onClick={handleSubmit}
              disabled={!question.trim() || isLoading}
            >
              <SendIcon />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
