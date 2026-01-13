from functools import lru_cache
from cachetools import TTLCache
import hashlib
import uuid
from database.manager import DatabaseManager
from utils.context_loader import load_context_files

# Cache for schemas (rarely change, cache indefinitely)
@lru_cache(maxsize=32)
def get_cached_schema(db_path: str) -> str:
    db_manager = DatabaseManager(db_path)
    return db_manager.get_schema_and_sample()

# Cache for meanings (TTL = 1 hour)
meanings_cache = TTLCache(maxsize=32, ttl=3600)

# Query result caching (TTL = 5 minutes)
query_cache = TTLCache(maxsize=100, ttl=300)
query_session_cache = TTLCache(maxsize=200, ttl=3600)

def get_cached_meanings(db_name: str, data_dir: str = "mini-interact") -> str:
    """Returns cached or fresh meanings text"""
    cache_key = f"{db_name}_meanings"
    if cache_key in meanings_cache:
        return meanings_cache[cache_key]
    
    _kb_text, meanings_text, _bsl_text = load_context_files(
        db_name,
        data_dir,
        include_kb=False,
    )
    meanings_cache[cache_key] = meanings_text
    return meanings_text

def get_cached_query_result(question: str, database: str):
    """Get cached query result by question and database"""
    query_hash = hashlib.md5(f"{question}_{database}".encode()).hexdigest()
    return query_cache.get(query_hash)

def cache_query_result(question: str, database: str, result):
    """Cache a query result"""
    query_hash = hashlib.md5(f"{question}_{database}".encode()).hexdigest()
    query_cache[query_hash] = result

def create_query_session(database: str, sql: str, question: str | None = None) -> str:
    """Create a new query session and return session ID"""
    query_id = uuid.uuid4().hex
    query_session_cache[query_id] = {
        "database": database,
        "sql": sql,
        "question": question,
    }
    return query_id

def get_query_session(query_id: str):
    """Get query session by ID"""
    return query_session_cache.get(query_id)

