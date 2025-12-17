from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    question: str
    database: str = "credit"

class AmbiguityResult(BaseModel):
    is_ambiguous: bool
    reason: Optional[str] = None
    questions: List[str] = []

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    severity: str = "low"
    suggestions: List[str] = []

class QueryResponse(BaseModel):
    question: str
    ambiguity_check: Optional[AmbiguityResult] = None
    generated_sql: str
    validation: Optional[ValidationResult] = None
    results: List[Dict[str, Any]]
    row_count: int
    notice: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None
