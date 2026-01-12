#!/usr/bin/env python3
"""
Quick-Start Script für BSL Integration

Führt alle Schritte automatisch aus:
1. Generiert BSL aus KB
2. Testet die Integration
3. Führt 10 Evaluierungsfragen aus

Usage:
    python quickstart_bsl.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_NAME = "credit"
DATA_DIR = "mini-interact"
DB_DIR = f"{DATA_DIR}/{DB_NAME}"

KB_PATH = f"{DB_DIR}/{DB_NAME}_kb.jsonl"
MEANINGS_PATH = f"{DB_DIR}/{DB_NAME}_column_meaning_base.json"
SCHEMA_PATH = f"{DB_DIR}/{DB_NAME}_schema.txt"
BSL_OUTPUT = f"{DB_DIR}/{DB_NAME}_bsl.txt"

# Die 10 Evaluierungsfragen
EVAL_QUESTIONS = [
    "Can you show me the top wealthy customers with their financial value? Including their IDs, total assets, total liabilities, the computed net worth value, and their ranking.",
    "Please find all the customer IDs who are highly digital.",
    "Can you identify all customers focused on investments in our database? I need to see their IDs, investment amounts and total assets.",
    "Analyze customer credit scores by credit classification. Show the credit category, and the customers' details for each category.",
    "To analyze customer property leverage, please show the customer ID, property value, mortgage balance, and the calculated ratio.",
    "I want to analyze customer financial standing. Please show the customer identifier, each customer's financial metrics.",
    "To analyze digital engagement trends, please group customers into quarterly cohorts based on their tenure and identify digital natives. For each combination of cohort with whether they are digital natives, show the cohort quarter, bool value, the cohort size, engagement score, the percentage of the cohort with high engagement, and high-engagement percentage broken down by digital native status.",
    "I need to analyze debt burden across different customer segments. Can you provide a summary for each segment with relevant debt metrics? Also add a grant total row. Exclude any customer segment with few customers and order the results.",
    "For each customer, show their ID, liquid and total assets, liquidity measure, monthly income, investment amount and label of their investment potential.",
    "To pinpoint customers who might be facing financial hardship, I'd like to see their customer ID, the calculated vulnerability score, their net worth, delinquency count, and late payment count. Only output the customers with signs of financial hardship."
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def check_files_exist():
    """Check if all required files exist"""
    print_header("Step 1: Checking Required Files")
    
    files = {
        "KB": KB_PATH,
        "Meanings": MEANINGS_PATH,
        "Schema": SCHEMA_PATH
    }
    
    all_exist = True
    for name, path in files.items():
        if os.path.exists(path):
            print(f"✅ {name}: {path}")
        else:
            print(f"❌ {name} NOT FOUND: {path}")
            all_exist = False
    
    if not all_exist:
        print("\n❌ Missing required files. Please check your data directory.")
        sys.exit(1)
    
    print("\n✅ All required files found!")

def generate_bsl():
    """Generate BSL from KB"""
    print_header("Step 2: Generating Business Semantics Layer")
    
    if os.path.exists(BSL_OUTPUT):
        response = input(f"BSL already exists at {BSL_OUTPUT}. Regenerate? (y/n): ")
        if response.lower() != 'y':
            print("Skipping BSL generation.")
            return
    
    print(f"📝 Generating BSL from:")
    print(f"   KB: {KB_PATH}")
    print(f"   Meanings: {MEANINGS_PATH}")
    print(f"   Output: {BSL_OUTPUT}")
    
    # Import the BSL builder
    try:
        from bsl_builder import BSLBuilder
        
        builder = BSLBuilder(KB_PATH, MEANINGS_PATH, SCHEMA_PATH)
        builder.build_bsl(BSL_OUTPUT)
        
        print(f"\n✅ BSL generated successfully!")
        print(f"📄 Location: {BSL_OUTPUT}")
        
        # Show BSL preview
        with open(BSL_OUTPUT, 'r', encoding='utf-8') as f:
            preview = f.read(500)
        print(f"\n📋 BSL Preview (first 500 chars):")
        print(f"{preview}...\n")
        
    except ImportError:
        print("❌ bsl_builder.py not found. Please ensure it's in the same directory.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating BSL: {str(e)}")
        sys.exit(1)

def test_bsl_loading():
    """Test if BSL can be loaded"""
    print_header("Step 3: Testing BSL Loading")
    
    try:
        with open(BSL_OUTPUT, 'r', encoding='utf-8') as f:
            bsl_content = f.read()
        
        print(f"✅ BSL loaded successfully")
        print(f"📊 Size: {len(bsl_content)} characters")
        print(f"📊 Lines: {len(bsl_content.splitlines())} lines")
        
        # Check for key sections
        sections = [
            "IDENTITY SYSTEM RULES",
            "AGGREGATION DETECTION RULES",
            "BUSINESS LOGIC RULES",
            "JSON FIELD EXTRACTION RULES",
            "JOIN CHAIN RULES"
        ]
        
        print(f"\n📋 Checking BSL Sections:")
        for section in sections:
            if section in bsl_content:
                print(f"   ✅ {section}")
            else:
                print(f"   ⚠️  {section} - NOT FOUND")
        
    except Exception as e:
        print(f"❌ Error loading BSL: {str(e)}")
        sys.exit(1)

def run_evaluation_questions():
    """Run the 10 evaluation questions"""
    print_header("Step 4: Running Evaluation Questions")
    
    print("🧪 Testing with 10 evaluation questions...")
    print("⚠️  Make sure your API is running: python main.py\n")
    
    proceed = input("Is the API running on http://localhost:8000? (y/n): ")
    if proceed.lower() != 'y':
        print("Please start the API first with: python main.py")
        return
    
    try:
        import requests
        
        results = []
        
        for i, question in enumerate(EVAL_QUESTIONS, 1):
            print(f"\n{'─'*70}")
            print(f"Question {i}/10:")
            print(f"{question[:80]}...")
            
            try:
                response = requests.post(
                    'http://localhost:8000/query',
                    json={
                        'question': question,
                        'database': DB_NAME,
                        'use_react': True,
                        'page_size': 10
                    },
                    timeout=60
                )
                
                result = response.json()
                
                # Extract key info
                sql = result.get('generated_sql', 'ERROR')
                row_count = result.get('row_count', 0)
                validation = result.get('validation', {})
                is_valid = validation.get('is_valid', False)
                confidence = result.get('confidence', 0.0)
                
                print(f"✓ SQL Generated: {sql[:100]}...")
                print(f"✓ Rows: {row_count}")
                print(f"✓ Valid: {is_valid}")
                print(f"✓ Confidence: {confidence:.2f}")
                
                # Check BSL compliance
                checklist = result.get('validation_checklist', {})
                if checklist:
                    print(f"✓ BSL Compliance:")
                    for key, value in checklist.items():
                        status = "✅" if value else "❌"
                        print(f"   {status} {key}: {value}")
                
                results.append({
                    'question_num': i,
                    'question': question,
                    'sql': sql,
                    'row_count': row_count,
                    'is_valid': is_valid,
                    'confidence': confidence,
                    'checklist': checklist
                })
                
            except requests.exceptions.Timeout:
                print(f"❌ Timeout - Question took too long")
                results.append({
                    'question_num': i,
                    'error': 'Timeout'
                })
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                results.append({
                    'question_num': i,
                    'error': str(e)
                })
        
        # Save results
        results_file = f"{DB_DIR}/evaluation_results_with_bsl.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print(f"📊 Evaluation Complete!")
        print(f"📄 Results saved to: {results_file}")
        
        # Summary
        valid_count = sum(1 for r in results if r.get('is_valid', False))
        error_count = sum(1 for r in results if 'error' in r)
        avg_confidence = sum(r.get('confidence', 0) for r in results if 'confidence' in r) / len(results)
        
        print(f"\n📈 Summary:")
        print(f"   ✅ Valid SQL: {valid_count}/10")
        print(f"   ❌ Errors: {error_count}/10")
        print(f"   📊 Avg Confidence: {avg_confidence:.2f}")
        
    except ImportError:
        print("❌ 'requests' library not found. Install with: pip install requests")
    except Exception as e:
        print(f"❌ Evaluation failed: {str(e)}")

def show_next_steps():
    """Show next steps"""
    print_header("Next Steps")
    
    print("""
✅ BSL Integration Complete!

📝 What to do next:

1. Review the generated BSL:
   cat {bsl_output}

2. Compare results before/after BSL:
   - Check evaluation_results_with_bsl.json
   - Look for improvements in the 3 failure modes:
     * Identity leakage (CU vs CS)
     * Aggregation failure (missing GROUP BY)
     * Semantic drift (wrong business rules)

3. For your presentation, highlight:
   - BSL as a "Business Semantics Layer" technique
   - Explicit rule representation vs implicit learning
   - Reproducibility (other teams can use BSL builder)
   - Evaluation methodology (10 questions before/after)

4. If results aren't perfect yet:
   - Review BSL rules and refine if needed
   - Check if prompts properly reference BSL
   - Look at LLM's "bsl_rules_applied" in responses

📚 Key Files:
   - BSL: {bsl_output}
   - Results: {db_dir}/evaluation_results_with_bsl.json
   - Prompts: llm/prompts.py (updated with BSL awareness)
""".format(bsl_output=BSL_OUTPUT, db_dir=DB_DIR))

# ============================================================================
# MAIN
# ============================================================================

def main():
    print_header("🚀 BSL Quick-Start Script")
    
    print("""
This script will:
1. Check if all required files exist
2. Generate Business Semantics Layer (BSL)
3. Test BSL loading
4. Run 10 evaluation questions
5. Show results and next steps
""")
    
    proceed = input("Continue? (y/n): ")
    if proceed.lower() != 'y':
        print("Exiting.")
        sys.exit(0)
    
    # Run all steps
    check_files_exist()
    generate_bsl()
    test_bsl_loading()
    run_evaluation_questions()
    show_next_steps()
    
    print("\n✅ All done!\n")

if __name__ == '__main__':
    main()