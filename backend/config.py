import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Zentrale Konfiguration"""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")

    # Pfade
    DATA_DIR = "mini-interact"

    # Ergebnisse
    MAX_RESULT_ROWS = 100
    
    # Validierung
    if not OPENAI_API_KEY:
        raise ValueError("FEHLER: OPENAI_API_KEY ist nicht gesetzt!")
