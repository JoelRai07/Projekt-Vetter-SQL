"""
Script zum Testen von Text2SQL mit den 10 Fragen aus Fragen.txt
"""

import requests
import json
import time
from pathlib import Path

# API-Konfiguration
API_URL = "http://localhost:8000/query"
OUTPUT_DIR = Path("../test_results")
OUTPUT_DIR.mkdir(exist_ok=True)

# Die 10 Fragen aus Fragen.txt
QUESTIONS = [
    "Can you show me the top wealthy customers with their financial value? Including their IDs, total assets, total liabilities, the computed net worth value, and their ranking.",
    "Please find all the customer IDs who are highly digital.",
    "Can you identify all customers focused on investments in our database? I need to see their IDs, investment amounts and total assets.",
    "Analyze customer credit scores by credit classification. Show the credit category, and the customers' details for each category.",
    "To analyze customer property leverage, please show the customer ID, property value, mortgage balance, and the calculated ratio.",
    "I want to analyze customer financial standing. Please show the customer identifier, each customer's financial metrics.",
    "To analyze digital engagement trends, please group customers into quarterly cohorts based on their tenure and identify digital natives. For each combination of cohort with whether they are digital natives, show the cohort quarter, bool value, the cohort size, engagement score, the percentage of the cohort with high engagement, and high-engagement percentage broken down by digital native status.",
    "I need to analyze debt burden across different customer segments. Can you provide a summary for each segment with relevant debt metrics? Also add a grant total row. Exclude any customer segment with few customers and order the results.",
    "For each customer, show their ID, liquid and total assets, liquidity measure, monthly income, investment amount and label of their investment potential.",
    "To pinpoint customers who might be facing financial hardship, I'd like to see their customer ID, the calculated vulnerability score, their net worth, delinquency count, and late payment count. Only output the customers with signs of financial hardship.",
]


def test_question(question_num, question_text):
    """
    Testet eine einzelne Frage gegen die API
    
    Args:
        question_num: Nummer der Frage (1-10)
        question_text: Der Fragetext
    
    Returns:
        dict mit Ergebnis oder None bei Fehler
    """
    print(f"\n{'='*80}")
    print(f"Frage {question_num}/10: {question_text[:60]}...")
    print(f"{'='*80}")
    
    try:
        # API-Request
        payload = {
            "question": question_text,
            "database": "credit",
            "page": 1,
            "page_size": 50
        }
        
        print(f"📤 Sende Request an {API_URL}...")
        response = requests.post(API_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        # Ausgabe der Ergebnisse
        print(f"✅ Status: {response.status_code}")
        print(f"📊 Rows zurückgegeben: {result.get('row_count', 0)}")
        
        if result.get('generated_sql'):
            print(f"\n🔧 Generierte SQL:")
            print(f"{result['generated_sql']}")
        
        if result.get('error'):
            print(f"\n❌ Fehler: {result['error']}")
        
        if result.get('explanation'):
            print(f"\n📝 Erklärung: {result['explanation']}")
        
        # Speichere Details in JSON
        output_file = OUTPUT_DIR / f"question_{question_num:02d}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Ergebnis gespeichert: {output_file}")
        
        return result
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Fehler: Kann nicht zu {API_URL} verbinden.")
        print(f"   Stelle sicher, dass der Backend-Server läuft: python main.py")
        return None
    
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout: Request zu lange ({120}s)")
        return None
    
    except Exception as e:
        print(f"❌ Fehler: {type(e).__name__}: {e}")
        return None


def main():
    """Hauptfunktion: Testet alle 10 Fragen"""
    print("\n" + "="*80)
    print("🧪 Text2SQL Test Suite - 10 Fragen")
    print("="*80)
    print(f"API-URL: {API_URL}")
    print(f"Output-Dir: {OUTPUT_DIR}")
    print(f"Anzahl Fragen: {len(QUESTIONS)}")
    
    # Überprüfe, ob API erreichbar ist
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("\n✅ API ist erreichbar")
        else:
            print(f"\n⚠️  API antwortet mit Status {response.status_code}")
    except:
        print("\n❌ API ist nicht erreichbar! Starten Sie den Backend-Server:")
        print("   cd backend && python main.py")
        return
    
    # Teste alle Fragen
    results = []
    start_time = time.time()
    
    for i, question in enumerate(QUESTIONS, 1):
        result = test_question(i, question)
        results.append({
            'question_num': i,
            'question': question,
            'result': result
        })
        
        # Kurze Pause zwischen Requests
        if i < len(QUESTIONS):
            time.sleep(1)
    
    # Zusammenfassung
    elapsed = time.time() - start_time
    print(f"\n\n{'='*80}")
    print("📊 ZUSAMMENFASSUNG")
    print(f"{'='*80}")
    print(f"⏱️  Gesamtzeit: {elapsed:.2f} Sekunden")
    print(f"📈 Fragen verarbeitet: {len(QUESTIONS)}")
    
    successful = sum(1 for r in results if r['result'] is not None and not r['result'].get('error'))
    print(f"✅ Erfolgreich: {successful}")
    print(f"❌ Fehler: {len(results) - successful}")
    
    # Speichere Zusammenfassung
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_questions': len(QUESTIONS),
            'successful': successful,
            'failed': len(results) - successful,
            'elapsed_seconds': elapsed,
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Zusammenfassung gespeichert: {summary_file}")
    print(f"\n💡 Alle Ergebnisse sind in {OUTPUT_DIR} verfügbar")


if __name__ == "__main__":
    main()
