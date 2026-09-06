"""ChromaDB-backed index over AST-derived chunks."""
from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

from codewarden.indexing.chunker import chunk_parsed_file
from codewarden.parsing.model import ParsedFile


@dataclass
class RetrievedChunk:
    id: str
    text: str
    metadata: dict
    distance: float


class CodeIndex:
    def __init__(self, persist_path: str, collection_name: str = "codewarden"):
        self.client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(collection_name)

    def index_parsed_file(self, parsed: ParsedFile) -> int:
        chunks = chunk_parsed_file(parsed)
        if not chunks:
            return 0
        self.collection.upsert(
            ids=[c.id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )
        return len(chunks)

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[RetrievedChunk]:
        result = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )
        retrieved = []
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        for i in range(len(ids)):
            retrieved.append(
                RetrievedChunk(
                    id=ids[i],
                    text=documents[i],
                    metadata=metadatas[i],
                    distance=distances[i],
                )
            )
        return retrieved

    def count(self) -> int:
        return self.collection.count()
