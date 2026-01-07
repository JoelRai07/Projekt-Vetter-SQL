from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    question: str
    database: Optional[str] = None
    auto_select: bool = True
    page: int = 1  # Paging: Seitenzahl
    page_size: int = 100  # Paging: Zeilen pro Seite
    use_react: bool = True  # ReAct + Retrieval Modus
    query_id: Optional[str] = None  # Session-ID fuer deterministisches Paging

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
    query_id: Optional[str] = None
    # Paging-Felder
    page: int = 1
    page_size: int = 100
    total_pages: Optional[int] = None
    total_rows: Optional[int] = None
    has_next_page: bool = False
    has_previous_page: bool = False
    notice: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None

class RouteRequest(BaseModel):
    question: str

class RouteResponse(BaseModel):
    question: str
    selected_database: Optional[str] = None
    confidence: float = 0.0
    ambiguity_check: Optional[AmbiguityResult] = None
    error: Optional[str] = None
