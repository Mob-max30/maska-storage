"""
===============================================================================
MaskaStorage Retrieval Engine
===============================================================================

Author:

Purpose
-------
This module implements the complete Retrieval layer of the
Retrieval-Augmented Generation (RAG) pipeline.

Responsibilities
----------------
• Initialize ChromaDB
• Store AI pipeline embeddings
• Retrieve relevant chunks
• Filter retrieval by resource IDs
• Delete vectors
• Build prompts
• Return retrieval results for the generation layer

This module DOES NOT call the LLM.

Pipeline

Upload
   │
   ▼
AIPipeline.process_url()/process_pdf()
   │
   ▼
Store Embeddings
   │
   ▼
ChromaDB
   │
   ▼
Similarity Search
   │
   ▼
Retrieved Chunks
   │
   ▼
Prompt Builder
   │
   ▼
rag_generation.py
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.config import Settings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

###############################################################################
# Configuration
###############################################################################

COLLECTION_NAME = "maska_documents"

DEFAULT_TOP_K = 5

MAX_CONTEXT_CHUNKS = 10

###############################################################################
# Exceptions
###############################################################################


class RetrievalError(Exception):
    """
    Base Retrieval Exception
    """
    pass


###############################################################################
# Data Models
###############################################################################


@dataclass
class RetrievedChunk:
    """
    Represents one retrieved chunk.
    """

    chunk_id: str

    resource_id: str

    text: str

    score: float

    metadata: dict[str, Any]


@dataclass
class RetrievalResult:
    """
    Returned to rag_generation.py
    """

    prompt: str

    chunks: list[RetrievedChunk]


###############################################################################
# ChromaDB Wrapper
###############################################################################


class ChromaDBManager:
    """
    Handles every interaction with ChromaDB.

    Responsibilities

        • Create/Open Collection

        • Store Embeddings

        • Similarity Search

        • Delete Vectors

        • Collection Statistics
    """

    def __init__(self):

        settings = get_settings()

        self.client = chromadb.PersistentClient(

            path=settings.chroma_path,

            settings=Settings(

                anonymized_telemetry=False

            )

        )

        self.collection = self.client.get_or_create_collection(

            COLLECTION_NAME,

            metadata={

                "hnsw:space": "cosine"

            }

        )

        logger.info(

            "Connected to ChromaDB collection '%s'.",

            COLLECTION_NAME,

        )

###############################################################################
# Store Embeddings
###############################################################################
    
    def add_document(
        self,
        pipeline_result: dict,
    ) -> None:
        """
        Stores output returned by

            AIPipeline.process_url()

        or

            AIPipeline.process_pdf()
        """

        metadata = pipeline_result["metadata"]

        document = pipeline_result["document"]

        chunks = pipeline_result["chunks"]

        embeddings = pipeline_result["embeddings"]

        resource_id = metadata["resource_id"]

        ids = []

        vectors = []

        documents = []

        metadatas = []

        for chunk, embedding in zip(chunks, embeddings):

            ids.append(

                chunk["chunk_id"]

            )

            vectors.append(

                embedding["embedding"]

            )

            documents.append(

                chunk["text"]

            )

            metadatas.append(

                {

                    "resource_id": resource_id,

                    "title": document.get("title"),

                    "filename": document.get("filename"),

                    "source_type": pipeline_result["source_type"],

                    "summary": pipeline_result["summary"]

                }

            )

        self.collection.add(

            ids=ids,

            embeddings=vectors,

            documents=documents,

            metadatas=metadatas,

        )

        logger.info(

            "Stored %d chunks for resource %s",

            len(ids),

            resource_id,

        )

###############################################################################
# Delete Resource
###############################################################################

    def delete_resource(
        self,
        resource_id: str,
    ) -> None:

        self.collection.delete(

            where={

                "resource_id": resource_id

            }

        )

        logger.info(

            "Deleted vectors for %s",

            resource_id

        )

###############################################################################
# Collection Statistics
###############################################################################

    def count(self) -> int:

        return self.collection.count()

    ###########################################################################

    def reset(self):

        self.client.delete_collection(

            COLLECTION_NAME

        )

        self.collection = self.client.get_or_create_collection(

            COLLECTION_NAME,

            metadata={

                "hnsw:space": "cosine"

            }

        )

        logger.warning(

            "Collection reset successfully."

        )
        ###############################################################################
# Similarity Search
###############################################################################

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = DEFAULT_TOP_K,
        resource_ids: list[str] | None = None,
    ):
        """
        Perform cosine similarity search.

        Parameters
        ----------
        query_embedding
            Embedding generated from the user's question.

        top_k
            Number of chunks to retrieve.

        resource_ids
            Optional list of resource ids to restrict search.
        """

        where_clause = None

        if resource_ids:

            where_clause = {

                "resource_id": {

                    "$in": resource_ids

                }

            }

        logger.info(

            "Running similarity search (top_k=%d)",

            top_k,

        )

        results = self.collection.query(

            query_embeddings=[query_embedding],

            n_results=top_k,

            where=where_clause,

            include=[

                "documents",

                "embeddings",

                "metadatas",

                "distances",

            ],

        )

        return results

###############################################################################
# Result Parser
###############################################################################

class ResultParser:
    """
    Converts raw ChromaDB output into RetrievedChunk objects.
    """

    @staticmethod
    def parse(
        chroma_result: dict,
    ) -> list[RetrievedChunk]:

        chunks: list[RetrievedChunk] = []

        ids = chroma_result["ids"][0]

        docs = chroma_result["documents"][0]

        metas = chroma_result["metadatas"][0]

        distances = chroma_result["distances"][0]

        for chunk_id, text, meta, distance in zip(

            ids,

            docs,

            metas,

            distances,

        ):

            chunks.append(

                RetrievedChunk(

                    chunk_id=chunk_id,

                    resource_id=meta["resource_id"],

                    text=text,

                    score=1.0 - float(distance),

                    metadata=meta,

                )

            )

        chunks.sort(

            key=lambda x: x.score,

            reverse=True,

        )

        return chunks

###############################################################################
# Prompt Builder
###############################################################################

class PromptBuilder:
    """
    Builds the prompt sent to the LLM.

    The LLM is instructed to answer ONLY using the supplied context.
    """

    SYSTEM_PROMPT = """
You are MaskaStorage AI.

Rules

1. Use ONLY the supplied context.

2. Never fabricate information.

3. If the answer does not exist in the context,
   clearly say so.

4. Do not use outside knowledge.

5. Keep answers factual.
"""

    ###########################################################################

    def build(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:

        prompt = self.SYSTEM_PROMPT

        prompt += "\n\n"

        prompt += "CONTEXT\n"

        prompt += "=======\n\n"

        for index, chunk in enumerate(chunks, start=1):

            title = (

                chunk.metadata.get("title")

                or

                chunk.metadata.get("filename")

                or

                "Untitled Resource"

            )

            prompt += (

                f"[Chunk {index}]\n"

                f"Resource ID : {chunk.resource_id}\n"

                f"Title       : {title}\n"

                f"Score       : {chunk.score:.3f}\n\n"

                f"{chunk.text}\n\n"

            )

        prompt += "QUESTION\n"

        prompt += "========\n\n"

        prompt += question

        prompt += "\n"

        return prompt

###############################################################################
# Utility Functions
###############################################################################

def extract_resource_ids(
    chunks: list[RetrievedChunk],
) -> list[str]:
    """
    Returns unique resource ids while preserving order.
    """

    seen = set()

    ordered = []

    for chunk in chunks:

        if chunk.resource_id not in seen:

            seen.add(

                chunk.resource_id

            )

            ordered.append(

                chunk.resource_id

            )

    return ordered


def build_citation_map(
    chunks: list[RetrievedChunk],
) -> dict[str, list[RetrievedChunk]]:
    """
    Groups retrieved chunks by resource_id.
    """

    grouped: dict[str, list[RetrievedChunk]] = {}

    for chunk in chunks:

        grouped.setdefault(

            chunk.resource_id,

            []

        ).append(

            chunk

        )

    return grouped
###############################################################################
# Retrieval Engine
###############################################################################

from app.ai.embeddings.embeddings import EmbeddingGenerator


class RetrievalEngine:
    """
    Main Retrieval Orchestrator.

    Responsibilities
    ----------------
    1. Generate embedding for user question.
    2. Search ChromaDB.
    3. Parse retrieved chunks.
    4. Build the prompt.
    5. Return RetrievalResult.

    This class does NOT call the LLM. It prepares everything needed for the
    generation layer.
    """

    def __init__(self):

        self.vector_store = ChromaDBManager()

        self.prompt_builder = PromptBuilder()

        self.embedder = EmbeddingGenerator()

    ###########################################################################

    def retrieve(
        self,
        question: str,
        resource_ids: list[str] | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> RetrievalResult:

        logger.info("Generating embedding for user query...")

        query_embedding = self.embedder.generate_query_embedding(question)

        logger.info("Embedding generated successfully.")

        raw_results = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            resource_ids=resource_ids,
        )

        retrieved_chunks = ResultParser.parse(raw_results)

        if not retrieved_chunks:

            logger.warning("No relevant chunks retrieved.")

            return RetrievalResult(
                prompt="No relevant context found.",
                chunks=[],
            )

        prompt = self.prompt_builder.build(
            question=question,
            chunks=retrieved_chunks,
        )

        logger.info(
            "Retrieved %d chunks.",
            len(retrieved_chunks),
        )

        return RetrievalResult(
            prompt=prompt,
            chunks=retrieved_chunks,
        )

###############################################################################
# Convenience APIs
###############################################################################

_engine: RetrievalEngine | None = None


def get_retrieval_engine() -> RetrievalEngine:
    """
    Singleton RetrievalEngine.

    Prevents repeatedly loading the embedding model and reconnecting to
    ChromaDB for every request.
    """

    global _engine

    if _engine is None:

        _engine = RetrievalEngine()

    return _engine


###############################################################################
# Public Helper Functions
###############################################################################

def retrieve_context(
    question: str,
    resource_ids: list[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> RetrievalResult:
    """
    Primary public function used by chat_service.py.

    Example
    -------
    result = retrieve_context(
        question="Explain residual connections."
    )

    print(result.prompt)
    """

    engine = get_retrieval_engine()

    return engine.retrieve(
        question=question,
        resource_ids=resource_ids,
        top_k=top_k,
    )


def store_pipeline_result(
    pipeline_result: dict,
) -> None:
    """
    Store the output of Sriganesh's AI pipeline in ChromaDB.

    Parameters
    ----------
    pipeline_result
        Dictionary returned by:

            AIPipeline.process_url()

        or

            AIPipeline.process_pdf()
    """

    engine = get_retrieval_engine()

    engine.vector_store.add_document(
        pipeline_result
    )


def delete_resource_vectors(
    resource_id: str,
) -> None:
    """
    Delete every vector belonging to a resource.
    """

    engine = get_retrieval_engine()

    engine.vector_store.delete_resource(
        resource_id
    )


def retrieval_statistics() -> dict:
    """
    Returns collection statistics.

    Useful for diagnostics and future admin endpoints.
    """

    engine = get_retrieval_engine()

    return {
        "collection_name": COLLECTION_NAME,
        "stored_chunks": engine.vector_store.count(),
    }


###############################################################################
# Health Check
###############################################################################

def health_check() -> bool:
    """
    Verify that the retrieval subsystem is operational.

    Returns
    -------
    bool
        True if ChromaDB is reachable and the collection exists.
    """

    try:

        engine = get_retrieval_engine()

        engine.vector_store.count()

        logger.info("Retrieval subsystem healthy.")

        return True

    except Exception as exc:

        logger.exception(
            "Retrieval health check failed: %s",
            exc,
        )

        return False


###############################################################################
# End of File
###############################################################################
if __name__ == "__main__":
    engine = RetrievalEngine()
    print("Connected to ChromaDB")
    print("Stored chunks:", engine.vector_store.count())