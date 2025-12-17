try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_chroma import Chroma
except ImportError:
    # Fallback für ältere Versionen
    try:
        from langchain.embeddings import OpenAIEmbeddings
        from langchain.vectorstores import Chroma
    except ImportError:
        raise ImportError(
            "Bitte installieren Sie langchain-openai und langchain-community: "
            "pip install langchain-openai langchain-community chromadb"
        )

import sqlite3
import json
import os
from typing import List, Dict, Optional
from config import Config


class SchemaRetriever:
    """Retrieval-System für Schema und Knowledge Base mit Vector Store"""
    
    def __init__(self, db_path: str, persist_dir: str = "./vector_store/schema"):
        self.db_path = db_path
        self.embeddings = OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY)
        self.persist_dir = persist_dir
        
        # Erstelle Verzeichnisse
        schema_dir = f"{persist_dir}/schema"
        kb_dir = f"{persist_dir}/kb"
        meanings_dir = f"{persist_dir}/meanings"
        
        os.makedirs(schema_dir, exist_ok=True)
        os.makedirs(kb_dir, exist_ok=True)
        os.makedirs(meanings_dir, exist_ok=True)
        
        # Vector Stores initialisieren
        self.schema_store = Chroma(
            persist_directory=schema_dir,
            embedding_function=self.embeddings
        )
        self.kb_store = Chroma(
            persist_directory=kb_dir,
            embedding_function=self.embeddings
        )
        self.meanings_store = Chroma(
            persist_directory=meanings_dir,
            embedding_function=self.embeddings
        )
        
        # Indexiere Schema beim ersten Mal (falls noch nicht indexiert)
        if len(self.schema_store.get()['ids']) == 0:
            self._index_schema()
    
    def _index_schema(self):
        """Indexiere Schema in Chunks (pro Tabelle ein Chunk)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_chunks = []
        metadata_list = []
        
        for (table_name,) in tables:
            # CREATE Statement
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            create_result = cursor.fetchone()
            if not create_result:
                continue
            create_stmt = create_result[0]
            
            # Spalten-Info
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()
            column_info = ", ".join([f"{col[1]} ({col[2]})" for col in columns])
            
            # Sample Row
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            row = cursor.fetchone()
            sample = ""
            if row:
                columns_names = [desc[0] for desc in cursor.description]
                row_dict = dict(zip(columns_names, row))
                sample = json.dumps(row_dict, default=str, ensure_ascii=False)
            
            # Chunk erstellen
            chunk_text = f"""Tabelle: {table_name}
CREATE TABLE: {create_stmt}
Spalten: {column_info}
Beispiel: {sample}"""
            
            schema_chunks.append(chunk_text)
            metadata_list.append({"table": table_name, "type": "schema"})
        
        conn.close()
        
        # In Vector Store speichern
        if schema_chunks:
            self.schema_store.add_texts(texts=schema_chunks, metadatas=metadata_list)
            self.schema_store.persist()
    
    def index_kb(self, kb_text: str):
        """Indexiere Knowledge Base"""
        if not kb_text or kb_text.startswith("[FEHLER"):
            return
        
        # KB in einzelne Einträge aufteilen
        kb_entries = [e for e in kb_text.split("\n• ") if e.strip()]
        
        if kb_entries:
            metadata = [{"type": "kb"} for _ in kb_entries]
            self.kb_store.add_texts(texts=kb_entries, metadatas=metadata)
            self.kb_store.persist()
    
    def index_meanings(self, meanings_text: str):
        """Indexiere Column Meanings"""
        if not meanings_text or meanings_text.startswith("[FEHLER"):
            return
        
        meaning_lines = meanings_text.split("\n")
        chunks = []
        current_chunk = ""
        
        for line in meaning_lines:
            if line.strip() and not line.startswith("    ") and not line.startswith("       "):
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line
            elif line.strip():
                current_chunk += "\n" + line
        
        if current_chunk:
            chunks.append(current_chunk)
        
        if chunks:
            metadata = [{"type": "meaning"} for _ in chunks]
            self.meanings_store.add_texts(texts=chunks, metadatas=metadata)
            self.meanings_store.persist()
    
    def retrieve_relevant_schema(self, question: str, top_k: int = 5) -> Optional[str]:
        """Retrieve nur relevante Schema-Teile"""
        try:
            results = self.schema_store.similarity_search_with_score(question, k=top_k)
            relevant = [doc.page_content for doc, score in results if score < 0.7]
            return "\n\n".join(relevant) if relevant else None
        except Exception as e:
            print(f"⚠️  Schema Retrieval Fehler: {str(e)}")
            return None
    
    def retrieve_relevant_kb(self, question: str, top_k: int = 5) -> str:
        """Retrieve nur relevante KB-Einträge"""
        try:
            results = self.kb_store.similarity_search_with_score(question, k=top_k)
            relevant = [doc.page_content for doc, score in results if score < 0.7]
            return "\n".join(relevant) if relevant else ""
        except Exception as e:
            print(f"⚠️  KB Retrieval Fehler: {str(e)}")
            return ""
    
    def retrieve_relevant_meanings(self, question: str, top_k: int = 10) -> str:
        """Retrieve nur relevante Column Meanings"""
        try:
            results = self.meanings_store.similarity_search_with_score(question, k=top_k)
            relevant = [doc.page_content for doc, score in results if score < 0.7]
            return "\n".join(relevant) if relevant else ""
        except Exception as e:
            print(f"⚠️  Meanings Retrieval Fehler: {str(e)}")
            return ""

