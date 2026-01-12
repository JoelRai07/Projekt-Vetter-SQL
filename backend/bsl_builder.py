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
            "# IDENTITY SYSTEM RULES",
            "",
            "## Dual Identifier System",
            "This database uses TWO identifiers per customer:",
            "- **CU format** (e.g., CU456680): Customer ID from `core_record.clientref`",
            "- **CS format** (e.g., CS239090): Core Registry ID from `core_record.coreregistry`",
            "",
            "## Critical Rule: Both refer to the SAME person, but appear in different contexts.",
            "",
            "## Table-to-Identifier Mapping:",
            "- `core_record.clientref` → Use when question asks for 'customer ID'",
            "- `core_record.coreregistry` → Use as PRIMARY KEY for joins",
            "",
            "## When to use which:",
            "1. If the question explicitly says 'customer ID' → Use `clientref` (CU format)",
            "2. If joining tables or using as primary key → Use `coreregistry` (CS format)",
            "3. If uncertain → Default to `clientref` for end-user queries",
            ""
        ]
        return rules
    
    def extract_aggregation_patterns(self, kb_entries: List[Dict]) -> List[str]:
        """Extract aggregation patterns from KB"""
        rules = [
            "# AGGREGATION DETECTION RULES",
            "",
            "## Keywords that REQUIRE GROUP BY:",
            "- 'by category', 'by segment', 'for each', 'breakdown', 'summary'",
            "- 'analyze ... by', 'group into', 'cohorts'",
            "",
            "## Keywords that require RANKING (ORDER BY + LIMIT):",
            "- 'top N', 'highest', 'lowest', 'best', 'worst'",
            "",
            "## Keywords that require ROW-LEVEL output:",
            "- 'show all', 'list each', 'find customers where', 'identify'",
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
            "# JOIN CHAIN RULES",
            "",
            "## Foreign Key Chain:",
            "```",
            "core_record.coreregistry",
            "  ↓ (FK)",
            "employment_and_income.emplcoreref",
            "  ↓ (FK)",
            "expenses_and_assets.expemplref",
            "  ↓ (FK)",
            "bank_and_transactions.bankexpref",
            "  ↓ (FK)",
            "credit_and_compliance.compbankref",
            "  ↓ (FK)",
            "credit_accounts_and_history.histcompref",
            "```",
            "",
            "## Rule: NEVER skip tables in the chain",
            "If you need columns from `core_record` and `credit_accounts_and_history`,",
            "you MUST join ALL intermediate tables.",
            "",
            "## Correct Join Pattern:",
            "```sql",
            "FROM core_record cr",
            "JOIN employment_and_income ei ON cr.coreregistry = ei.emplcoreref",
            "JOIN expenses_and_assets ea ON ei.emplcoreref = ea.expemplref",
            "JOIN bank_and_transactions bt ON ea.expemplref = bt.bankexpref",
            "JOIN credit_and_compliance cc ON bt.bankexpref = cc.compbankref",
            "JOIN credit_accounts_and_history cah ON cc.compbankref = cah.histcompref",
            "```",
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