import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Zentrale Konfiguration"""
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.5-flash"

    # Pfade
    DATA_DIR = "mini-interact"

    # Ergebnisse
    MAX_RESULT_ROWS = 100
    
    # Validierung
    if not OPENAI_API_KEY:
        raise ValueError("FEHLER: OPENAI_API_KEY ist nicht gesetzt!")
