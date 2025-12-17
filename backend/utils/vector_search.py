import logging
from typing import List, Dict, Any

import faiss
import numpy as np
import google.generativeai as genai


class SemanticIndex:
    """Kapselt einen HNSW Index für semantische Suche."""

    def __init__(self, embed_model: str = "models/embedding-001"):
        self.embed_model = embed_model
        self.index = None
        self.payloads: List[Dict[str, Any]] = []
        self.dim = None

    def _embed(self, texts: List[str]) -> np.ndarray:
        embeddings: List[List[float]] = []
        for text in texts:
            result = genai.embed_content(model=self.embed_model, content=text)
            embeddings.append(result["embedding"])

        matrix = np.array(embeddings, dtype="float32")
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        return matrix

    def build(self, documents: List[Dict[str, Any]]):
        """
        Baut den Index aus Dokumenten.
        Erwartet eine Liste mit {"text": str, ...} Einträgen. Alle Schlüssel außer "text" werden als Payload gespeichert.
        """
        if not documents:
            logging.warning("Kein Dokument für den Index bereitgestellt – Index wird übersprungen.")
            return

        texts = [doc["text"] for doc in documents]
        payloads = [{k: v for k, v in doc.items() if k != "text"} for doc in documents]

        matrix = self._embed(texts)
        self.dim = matrix.shape[1]

        index = faiss.IndexHNSWFlat(self.dim, 32)
        index.hnsw.efConstruction = 200
        index.add(matrix)

        self.index = index
        self.payloads = payloads

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None or self.dim is None:
            return []

        query_vec = self._embed([query])
        scores, indices = self.index.search(query_vec, top_k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self.payloads):
                continue
            payload = self.payloads[idx].copy()
            payload["score"] = float(score)
            results.append(payload)
        return results


class LookupEngine:
    """Zentrale Lookup-Tools für Schema- und KB-Suche."""

    def __init__(self, api_key: str, embed_model: str = "models/embedding-001"):
        genai.configure(api_key=api_key)
        self.schema_index = SemanticIndex(embed_model)
        self.kb_index = SemanticIndex(embed_model)

    def build_schema_index(
        self,
        schema_blocks: List[Dict[str, Any]],
        column_meanings: List[Dict[str, Any]] | None = None,
    ) -> None:
        documents: List[Dict[str, Any]] = []
        for block in schema_blocks:
            documents.append({
                "text": block["text"],
                "label": block.get("table", "schema"),
                "kind": "schema",
            })

        if column_meanings:
            for meaning in column_meanings:
                documents.append({
                    "text": meaning["text"],
                    "label": meaning.get("key", "column_meaning"),
                    "kind": "column_meaning",
                })

        self.schema_index.build(documents)

    def build_kb_index(self, kb_entries: List[Dict[str, Any]]) -> None:
        documents = [
            {"text": entry["text"], "label": entry.get("label", "kb"), "kind": "kb"}
            for entry in kb_entries
        ]
        self.kb_index.build(documents)

    def schema_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.schema_index.search(query, top_k)

    def kb_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.kb_index.search(query, top_k)
