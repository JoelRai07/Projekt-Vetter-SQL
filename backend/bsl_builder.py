"""
Business Semantics Layer (BSL) Builder

Converts implicit knowledge from KB/schema into explicit, LLM-friendly rules.
This ensures Text2SQL systems understand business logic, not just schema.

Usage:
    python bsl_builder.py --db credit --output bsl_credit.txt
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any


class BSLBuilder:
    """Builds a Business Semantics Layer from KB and Schema"""
    
    def __init__(self, kb_path: str, meanings_path: str, schema_path: str):
        self.kb_path = kb_path
        self.meanings_path = meanings_path
        self.schema_path = schema_path
        
    def load_kb(self) -> List[Dict[str, Any]]:
        """Load Knowledge Base entries"""
        entries = []
        with open(self.kb_path, 'r', encoding='utf-8') as f:
            for line in f:
                entries.append(json.loads(line))
        return entries
    
    def load_meanings(self) -> Dict[str, Any]:
        """Load column meanings"""
        with open(self.meanings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_identity_rules(self, meanings: Dict) -> List[str]:
        """Extract rules about identifiers (CU vs CS)"""
        rules = [
            "# IDENTITY SYSTEM RULES (CRITICAL)",
            "",
            "## ⚠️ CRITICAL: Dual Identifier System",
            "This database uses TWO DIFFERENT identifiers per customer:",
            "",
            "### CU Format (Customer ID)",
            "- Format: CU followed by digits (e.g., CU456680, CU582141)",
            "- Source: `core_record.clientref`",
            "- Purpose: Business identifier, used in output/reports",
            "- When to use: Question asks for 'customer ID', 'customer identifier', or 'show customer'",
            "",
            "### CS Format (Core Registry ID)",
            "- Format: CS followed by digits (e.g., CS239090, CS206405)",
            "- Source: `core_record.coreregistry` (PRIMARY KEY)",
            "- Purpose: Technical identifier, used for JOINs and internal references",
            "- When to use: Joining tables, filtering by registry, or technical lookups",
            "",
            "## ⚠️ RULE 1: SAME PERSON, DIFFERENT IDs",
            "Both refer to the SAME person but are INCOMPATIBLE in queries:",
            "- DO NOT SELECT clientref AND coreregistry from same row expecting them to match",
            "- DO NOT use CU format for WHERE clauses on coreregistry",
            "- DO NOT use CS format in output when question asks for 'customer ID'",
            "",
            "## ⚠️ RULE 2: Identifier Selection in SELECT",
            "The SELECT clause determines your output identifier:",
            "",
            "**WRONG Examples (Common Mistakes):**",
            "```sql",
            "SELECT coreregistry FROM core_record;  -- Returns CS format, not CU",
            "SELECT clientref AS customer_id FROM core_record;  -- ✓ Correct, returns CU",
            "```",
            "",
            "**Question: 'Show top 10 wealthiest customers'**",
            "- Output should be: CU format (e.g., CU456680)",
            "- Correct: SELECT cr.clientref AS customer_id, ea.totassets",
            "- WRONG: SELECT cr.coreregistry AS customer_id (returns CS format)",
            "",
            "## ⚠️ RULE 3: Identifier Usage in JOINs",
            "ALL joins use CS format (coreregistry):",
            "```sql",
            "FROM core_record cr",
            "JOIN employment_and_income ei ON cr.coreregistry = ei.emplcoreref  -- Use CS",
            "JOIN expenses_and_assets ea ON ei.emplcoreref = ea.expemplref      -- Use CS chain",
            "```",
            "",
            "## ⚠️ RULE 4: Output vs Internal Logic",
            "When SELECT clause has:",
            "- `cr.clientref` → Output will be CU format ✓",
            "- `cr.coreregistry` → Output will be CS format (usually wrong for 'customer ID')",
            "- `ei.emplcoreref` → This is CS format (for joining, NOT output)",
            "",
            "## ⚠️ RULE 5: Question-Specific Identifier Requirements",
            "",
            "### Question Type: Ranking/Listing (Top N, Highest, Best)",
            "Example: 'Top 10 wealthiest customers'",
            "- Output identifier: clientref (CU format)",
            "- Correct SELECT: cr.clientref, ea.totassets",
            "- Common Error: Selecting coreregistry (returns CS format)",
            "",
            "### Question Type: Segmentation/Cohort Analysis",
            "Example: 'Analyze by cohort quarter'",
            "- Output identifier: clientref (CU format)",
            "- Additional logic: May need to determine cohort_quarter from scoredate",
            "- Correct SELECT: cr.clientref, cohort_quarter, COUNT(*)",
            "- Common Error: Not extracting quarter correctly, wrong identifier",
            "",
            "### Question Type: Risk/Condition Filtering",
            "Example: 'High-risk customers (High risk level, delinquencies, negative net worth)'",
            "- Output identifier: clientref (CU format)",
            "- Additional columns: Risk indicators (delinqcount, risklev, net_worth)",
            "- Correct SELECT: cr.clientref, cc.risklev, cc.delinqcount, net_worth",
            "- Common Error: Using CS format, missing filters, wrong join chain",
            "",
            "## ⚠️ VALIDATION CHECKLIST",
            "Before returning SQL, verify:",
            "1. ☐ Is question asking for 'customer ID'? → SELECT cr.clientref",
            "2. ☐ Are all JOINs using coreregistry (CS)? → Check ON conditions",
            "3. ☐ Does output identifier match question type? → CU for customer queries",
            "4. ☐ If using coreregistry in SELECT, is it intentional? → Usually wrong",
            "5. ☐ Are there different customers in results than reference? → Check identifier type",
            ""
        ]
        return rules
    
    def extract_aggregation_patterns(self, kb_entries: List[Dict]) -> List[str]:
        """Extract aggregation patterns from KB"""
        rules = [
            "# AGGREGATION DETECTION RULES",
            "",
            "## ⚠️ CRITICAL: Aggregation vs Detail Queries",
            "",
            "### Aggregation Queries (Must use GROUP BY)",
            "Keywords that REQUIRE GROUP BY:",
            "- 'by category', 'by segment', 'for each', 'breakdown', 'summary'",
            "- 'analyze ... by', 'group into', 'cohorts'",
            "- 'how many', 'count', 'average', 'total'",
            "",
            "Example: 'Analyze credit scores BY risk level'  → GROUP BY risklev",
            "",
            "### Detail/Ranking Queries (No GROUP BY, use ORDER + LIMIT)",
            "Keywords that require RANKING (ORDER BY + LIMIT):",
            "- 'top N', 'highest', 'lowest', 'best', 'worst'",
            "- 'list top', 'show best', 'find worst'",
            "",
            "Example: 'Top 10 wealthiest customers' → ORDER BY totassets DESC LIMIT 10",
            "⚠️ NOT GROUP BY (each customer appears once, not aggregated)",
            "",
            "### Detail Queries (Row-level, no aggregation)",
            "Keywords that require ROW-LEVEL output:",
            "- 'show all', 'list each', 'find customers where', 'identify'",
            "- 'display', 'retrieve', 'find' (without aggregation keywords)",
            "",
            "Example: 'Find all digital-first customers' → SELECT WHERE (no GROUP BY)",
            "⚠️ Do NOT GROUP BY unless question explicitly asks for breakdown",
            "",
            "## ⚠️ CRITICAL: Cohort Questions (Special Case)",
            "When question asks 'by cohort quarter':",
            "- This is a GROUPING operation",
            "- Must create cohort_quarter variable from scoredate",
            "- Formula: Extract quarter from scoredate (or tenure-based cohort)",
            "- MUST include GROUP BY cohort_quarter",
            "- Each row shows: customer (or cohort indicator), metrics",
            "",
            "## Special Case: Grand Total",
            "If question asks for 'total' AND segment breakdown:",
            "→ Use UNION ALL with aggregated segments + total row",
            ""
        ]
        
        # Add calculated metrics that require aggregation
        calc_metrics = [m for m in kb_entries if m.get('type') == 'calculation_knowledge']
        if calc_metrics:
            rules.append("## Calculated Metrics (may require aggregation):")
            for metric in calc_metrics[:5]:  # Top 5 examples
                rules.append(f"- {metric['knowledge']}: {metric['definition'][:100]}...")
            rules.append("")
        
        return rules
    
    def extract_business_rules(self, kb_entries: List[Dict]) -> List[str]:
        """Extract business logic rules"""
        rules = [
            "# BUSINESS LOGIC RULES",
            ""
        ]
        
        # Domain knowledge (filters and conditions)
        domain_rules = [m for m in kb_entries if m.get('type') == 'domain_knowledge']
        
        if domain_rules:
            rules.append("## Customer Segmentation Rules:")
            for rule in domain_rules:
                name = rule['knowledge']
                definition = rule['definition']
                rules.append(f"### {name}")
                rules.append(f"{definition}")
                rules.append("")
        
        # Value illustrations (thresholds)
        value_rules = [m for m in kb_entries if m.get('type') == 'value_illustration']
        if value_rules:
            rules.append("## Value Interpretation Guidelines:")
            for rule in value_rules[:5]:  # Top 5
                rules.append(f"- {rule['knowledge']}: {rule['definition'][:150]}...")
            rules.append("")
        
        return rules
    
    def extract_json_field_rules(self, meanings: Dict) -> List[str]:
        """Extract rules for JSON column handling"""
        rules = [
            "# JSON FIELD EXTRACTION RULES",
            "",
            "## Important: JSON columns must be qualified with table name",
            ""
        ]
        
        # Find JSON columns
        json_cols = {k: v for k, v in meanings.items() 
                     if isinstance(v, dict) and 'fields_meaning' in v}
        
        for key, value in json_cols.items():
            db, table, column = key.split('|')
            rules.append(f"### {table}.{column} (JSONB)")
            rules.append(f"{value.get('column_meaning', '')}")
            rules.append("")
            rules.append("**Fields:**")
            
            fields = value.get('fields_meaning', {})
            for field, desc in fields.items():
                if isinstance(desc, dict):
                    rules.append(f"- `{field}` (nested):")
                    for subfield, subdesc in desc.items():
                        rules.append(f"  - `{subfield}`: {subdesc}")
                else:
                    rules.append(f"- `{field}`: {desc}")
            
            rules.append("")
            rules.append(f"**Example extraction:**")
            rules.append(f"```sql")
            rules.append(f"json_extract({table}.{column}, '$.{list(fields.keys())[0]}')")
            rules.append(f"```")
            rules.append("")
        
        return rules
    
    def extract_join_chain_rules(self) -> List[str]:
        """Extract FK chain rules from schema"""
        rules = [
            "# JOIN CHAIN RULES (CRITICAL)",
            "",
            "## ⚠️ RULE: Foreign Key Chain is STRICT",
            "The data model enforces a rigid chain. NEVER skip or reorder:",
            "",
            "```",
            "core_record (coreregistry PRIMARY KEY)",
            "  ↓ FK: coreregistry = emplcoreref",
            "employment_and_income (emplcoreref PRIMARY KEY)",
            "  ↓ FK: emplcoreref = expemplref",
            "expenses_and_assets (expemplref PRIMARY KEY)",
            "  ↓ FK: expemplref = bankexpref",
            "bank_and_transactions (bankexpref PRIMARY KEY)",
            "  ↓ FK: bankexpref = compbankref",
            "credit_and_compliance (compbankref PRIMARY KEY)",
            "  ↓ FK: compbankref = histcompref",
            "credit_accounts_and_history (histcompref PRIMARY KEY)",
            "```",
            "",
            "## ⚠️ RULE: NEVER skip tables in the chain",
            "If you need columns from Table A and Table C:",
            "- You MUST include ALL intermediate tables (A → B → C)",
            "- Skipping breaks the FK relationships",
            "",
            "Example: Need `core_record.clientref` AND `credit_accounts_and_history.custlifeval`",
            "→ MUST include ALL 5 intermediate JOINs",
            "",
            "## ⚠️ RULE: Join Direction is Always Left-to-Right",
            "```sql",
            "FROM core_record cr",
            "JOIN employment_and_income ei ON cr.coreregistry = ei.emplcoreref",
            "JOIN expenses_and_assets ea ON ei.emplcoreref = ea.expemplref",
            "JOIN bank_and_transactions bt ON ea.expemplref = bt.bankexpref",
            "JOIN credit_and_compliance cc ON bt.bankexpref = cc.compbankref",
            "JOIN credit_accounts_and_history cah ON cc.compbankref = cah.histcompref",
            "```",
            "",
            "## ⚠️ RULE: Common Mistakes",
            "**WRONG:** `ON cc.compbankref = ei.emplcoreref` (skips ea, bt)",
            "**WRONG:** `ON cr.coreregistry = cc.compbankref` (skips all intermediate)",
            "**CORRECT:** Follow the chain exactly as shown above",
            "",
            "## ✓ When You Can Stop the Chain",
            "You can stop at an intermediate table if you don't need downstream data:",
            "- Need core_record + employment_and_income? → Join to employment_and_income, stop",
            "- Need core_record + expenses_and_assets? → Join through employment_and_income",
            "",
            "But if you jump across the chain (e.g., core → credit_compliance), it fails.",
            ""
        ]
        return rules
    
    def build_bsl(self, output_path: str):
        """Build complete BSL document"""
        print("🔨 Building Business Semantics Layer...")
        
        # Load data
        kb_entries = self.load_kb()
        meanings = self.load_meanings()
        
        # Build sections
        bsl_content = [
            "# BUSINESS SEMANTICS LAYER (BSL)",
            "# Credit Database - Text2SQL Knowledge Base",
            "",
            "This document contains explicit business rules and patterns for generating correct SQL.",
            "It was auto-generated from the knowledge base and schema.",
            "",
            "---",
            ""
        ]
        
        # Add each section
        bsl_content.extend(self.extract_identity_rules(meanings))
        bsl_content.extend(self.extract_aggregation_patterns(kb_entries))
        bsl_content.extend(self.extract_business_rules(kb_entries))
        bsl_content.extend(self.extract_json_field_rules(meanings))
        bsl_content.extend(self.extract_join_chain_rules())
        
        # Add metric formulas section
        bsl_content.extend([
            "# METRIC CALCULATION FORMULAS",
            "",
            "When a question asks for a calculated metric, use these exact formulas:",
            ""
        ])
        
        calc_metrics = [m for m in kb_entries if m.get('type') == 'calculation_knowledge']
        for metric in calc_metrics:
            bsl_content.append(f"## {metric['knowledge']}")
            bsl_content.append(f"**Definition:** {metric['description']}")
            bsl_content.append(f"**Formula:** {metric['definition']}")
            bsl_content.append("")
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(bsl_content))
        
        print(f"✅ BSL saved to: {output_path}")
        print(f"📊 Sections generated:")
        print(f"   - Identity Rules")
        print(f"   - Aggregation Patterns")
        print(f"   - Business Logic Rules")
        print(f"   - JSON Field Rules")
        print(f"   - Join Chain Rules")
        print(f"   - {len(calc_metrics)} Metric Formulas")


def main():
    parser = argparse.ArgumentParser(description='Build Business Semantics Layer')
    parser.add_argument('--kb', required=True, help='Path to KB JSONL file')
    parser.add_argument('--meanings', required=True, help='Path to meanings JSON file')
    parser.add_argument('--schema', required=True, help='Path to schema SQL file')
    parser.add_argument('--output', required=True, help='Output BSL file path')
    
    args = parser.parse_args()
    
    builder = BSLBuilder(args.kb, args.meanings, args.schema)
    builder.build_bsl(args.output)


if __name__ == '__main__':
    # Example usage without CLI
    builder = BSLBuilder(
        kb_path='mini-interact/credit/credit_kb.jsonl',
        meanings_path='mini-interact/credit/credit_column_meaning_base.json',
        schema_path='mini-interact/credit/credit_schema.sql'
    )
    builder.build_bsl('mini-interact/credit/credit_bsl.txt')