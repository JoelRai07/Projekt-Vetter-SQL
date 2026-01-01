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

# Cache for KB and meanings (TTL = 1 hour)
kb_cache = TTLCache(maxsize=32, ttl=3600)
meanings_cache = TTLCache(maxsize=32, ttl=3600)

def get_cached_kb(db_name: str, data_dir: str) -> str:
    cache_key = f"{db_name}_kb"
    if cache_key in kb_cache:
        return kb_cache[cache_key]
    
    kb_text, meanings_text = load_context_files(db_name, data_dir)
    kb_cache[cache_key] = kb_text
    meanings_cache[f"{db_name}_meanings"] = meanings_text
    return kb_text

def get_cached_meanings(db_name: str, data_dir: str) -> str:
    cache_key = f"{db_name}_meanings"
    if cache_key in meanings_cache:
        return meanings_cache[cache_key]
    
    kb_text, meanings_text = load_context_files(db_name, data_dir)
    kb_cache[f"{db_name}_kb"] = kb_text
    meanings_cache[cache_key] = meanings_text
    return meanings_text

# Query result caching (TTL = 5 minutes)
query_cache = TTLCache(maxsize=100, ttl=300)
query_session_cache = TTLCache(maxsize=200, ttl=3600)

def get_cache_key(question: str, database: str) -> str:
    """Generate cache key from question and database"""
    key_string = f"{database}:{question.lower().strip()}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_cached_query_result(question: str, database: str):
    cache_key = get_cache_key(question, database)
    return query_cache.get(cache_key)

def cache_query_result(question: str, database: str, result: dict):
    cache_key = get_cache_key(question, database)
    query_cache[cache_key] = result

def create_query_session(database: str, sql: str, question: str | None = None) -> str:
    query_id = uuid.uuid4().hex
    query_session_cache[query_id] = {
        "database": database,
        "sql": sql,
        "question": question,
    }
    return query_id

def get_query_session(query_id: str):
    return query_session_cache.get(query_id)

