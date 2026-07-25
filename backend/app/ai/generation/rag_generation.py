"""
===============================================================================
MaskaStorage Generation Engine
===============================================================================

Author:
    Yashneil Reddy
    (Retrieval, Augmentation & Generation Layer)

Purpose
-------
This module implements the Generation layer of the Retrieval-Augmented
Generation (RAG) pipeline.

The Retrieval layer retrieves the most relevant document chunks from
ChromaDB and assembles a grounded prompt.

This module is responsible for:

    • Receiving RetrievalResult from rag_retrieval.py
    • Sending the prompt to the configured LLM
    • Parsing the generated response
    • Building structured citations
    • Returning a GenerationResult object
    • Providing helper utilities for ChatService

Pipeline
--------

User Question
      │
      ▼
RetrievalEngine
      │
      ▼
RetrievalResult
      │
      ▼
GenerationEngine
      │
      ▼
OpenAI GPT
      │
      ▼
Grounded Answer
      │
      ▼
Chat Service
===============================================================================
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.ai.retrieval.rag_retrieval import (
    RetrievalResult,
    RetrievedChunk,
)

logger = logging.getLogger(__name__)

###############################################################################
# Configuration
###############################################################################

DEFAULT_MODEL = "gpt-5"

DEFAULT_TEMPERATURE = 0.2

DEFAULT_MAX_TOKENS = 700

SYSTEM_PROMPT = """
You are MaskaStorage AI.

You answer ONLY from the supplied document context.

Rules
-----

1. Never invent information.

2. Never use outside knowledge.

3. If the answer cannot be found in the supplied context,
reply:

'I couldn't find enough information in the uploaded resources
to answer that question.'

4. When multiple documents discuss the topic,
combine their information into one coherent answer.

5. Preserve technical terminology exactly.

6. Be concise.

7. Never mention ChromaDB,
embeddings,
vector search,
or retrieval internally.

Return only the answer.
"""

###############################################################################
# Exceptions
###############################################################################


class GenerationError(Exception):
    """
    Base exception raised by the Generation layer.
    """
    pass


class OpenAIConnectionError(GenerationError):
    """
    Raised when the OpenAI API cannot be reached.
    """
    pass


class InvalidGenerationResponse(GenerationError):
    """
    Raised when the model returns an invalid response.
    """
    pass


###############################################################################
# Response Models
###############################################################################


@dataclass(slots=True)
class Citation:
    """
    Represents one citation attached to the generated answer.
    """

    resource_id: str

    chunk_id: str

    title: str | None

    score: float

    snippet: str


@dataclass(slots=True)
class GenerationResult:
    """
    Final output of the Generation layer.
    """

    answer: str

    citations: list[Citation] = field(default_factory=list)

    model: str = DEFAULT_MODEL

    prompt_tokens: int = 0

    completion_tokens: int = 0

    total_tokens: int = 0

    generation_time: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)


###############################################################################
# OpenAI Wrapper
###############################################################################


class OpenAIClient:
    """
    Lightweight wrapper around the OpenAI SDK.

    Responsibilities
    ----------------
    • Hold one reusable SDK client
    • Hide SDK implementation details
    • Handle API failures
    • Return raw model responses
    """

    def __init__(self):

        settings = get_settings()

        api_key = settings.llm_api_key

        if not api_key:

            raise OpenAIConnectionError(
                "MASKA_LLM_API_KEY is not configured."
            )

        self.client = OpenAI(
            api_key=api_key
        )

        self.model = DEFAULT_MODEL

        logger.info(
            "OpenAI client initialized using model '%s'.",
            self.model,
        )

    ###########################################################################
    # Generate
    ###########################################################################

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Sends the prompt to OpenAI and returns the raw response.
        """

        start = time.perf_counter()

        try:

            response = self.client.chat.completions.create(

                model=self.model,

                temperature=temperature,

                max_tokens=max_tokens,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            elapsed = time.perf_counter() - start

            logger.info(
                "OpenAI generation completed in %.2f seconds.",
                elapsed,
            )

            return response, elapsed

        except Exception as exc:

            logger.exception(
                "Generation request failed."
            )

            raise OpenAIConnectionError(
                str(exc)
            )
###############################################################################
# Generation Engine
###############################################################################


class GenerationEngine:
    """
    Converts RetrievalResult into a grounded LLM response.

    Responsibilities
    ----------------
    • Validate retrieval output
    • Skip unnecessary LLM calls
    • Call OpenAI
    • Parse responses
    • Build citations
    • Return GenerationResult
    """

    def __init__(self):

        self.client = OpenAIClient()

        logger.info(
            "GenerationEngine initialized."
        )

    ###########################################################################
    # Public API
    ###########################################################################

    def generate(
        self,
        retrieval_result: RetrievalResult,
    ) -> GenerationResult:
        """
        Generates the final grounded response.

        Parameters
        ----------
        retrieval_result
            Output produced by rag_retrieval.py

        Returns
        -------
        GenerationResult
        """

        if retrieval_result is None:

            raise GenerationError(
                "RetrievalResult cannot be None."
            )

        if retrieval_result.prompt is None:

            raise GenerationError(
                "Prompt is missing."
            )

        if not retrieval_result.prompt.strip():

            raise GenerationError(
                "Prompt is empty."
            )

        ###################################################################
        # No retrieved chunks
        ###################################################################

        if len(retrieval_result.chunks) == 0:

            logger.info(
                "Retrieval returned zero chunks."
            )

            return GenerationResult(

                answer=(
                    "I couldn't find enough information "
                    "in the uploaded resources "
                    "to answer that question."
                ),

                citations=[],

                metadata={
                    "retrieved_chunks": 0,
                    "resource_count": 0,
                },
            )

        logger.info(
            "Retrieved %d chunks.",
            len(retrieval_result.chunks),
        )

        logger.info(
            "Prompt length: %d characters.",
            len(retrieval_result.prompt),
        )

        response, generation_time = self.client.generate(
            prompt=retrieval_result.prompt
        )

        return self._parse_response(
            response=response,
            retrieval_result=retrieval_result,
            generation_time=generation_time,
        )

    ###########################################################################
    # Internal Response Parser
    ###########################################################################

    def _parse_response(
        self,
        *,
        response,
        retrieval_result: RetrievalResult,
        generation_time: float,
    ) -> GenerationResult:
        """
        Converts the raw OpenAI response into a
        structured GenerationResult.
        """

        if response is None:

            raise InvalidGenerationResponse(
                "OpenAI returned None."
            )

        if not response.choices:

            raise InvalidGenerationResponse(
                "OpenAI returned zero choices."
            )

        message = response.choices[0].message

        if message is None:

            raise InvalidGenerationResponse(
                "Assistant message missing."
            )

        answer = message.content

        if answer is None:

            raise InvalidGenerationResponse(
                "Generated answer is empty."
            )

        usage = getattr(
            response,
            "usage",
            None,
        )

        prompt_tokens = (
            getattr(
                usage,
                "prompt_tokens",
                0,
            )
            if usage
            else 0
        )

        completion_tokens = (
            getattr(
                usage,
                "completion_tokens",
                0,
            )
            if usage
            else 0
        )

        total_tokens = (
            getattr(
                usage,
                "total_tokens",
                0,
            )
            if usage
            else 0
        )

        citations = self._build_citations(
            retrieval_result.chunks
        )

        logger.info(
            "Generated %d citations.",
            len(citations),
        )

        logger.info(
            "Prompt Tokens=%d Completion Tokens=%d Total=%d",
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )

        return GenerationResult(

            answer=answer.strip(),

            citations=citations,

            model=self.client.model,

            prompt_tokens=prompt_tokens,

            completion_tokens=completion_tokens,

            total_tokens=total_tokens,

            generation_time=generation_time,

            metadata={

                "retrieved_chunks": len(
                    retrieval_result.chunks
                ),

                "resource_count": len(
                    {
                        chunk.resource_id
                        for chunk in retrieval_result.chunks
                    }
                ),

                "generation_seconds": round(
                    generation_time,
                    3,
                ),
            },
        )
        ###########################################################################
    # Citation Builder
    ###########################################################################

    def _build_citations(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[Citation]:
        """
        Builds structured citations from retrieved chunks.

        Behaviour
        ---------
        • Removes duplicate chunks
        • Sorts by similarity score
        • Produces short snippets
        """

        if not chunks:
            return []

        #######################################################################
        # Highest similarity first
        #######################################################################

        sorted_chunks = sorted(
            chunks,
            key=lambda chunk: chunk.score,
            reverse=True,
        )

        citations: list[Citation] = []

        seen: set[tuple[str, str]] = set()

        for chunk in sorted_chunks:

            key = (
                chunk.resource_id,
                chunk.chunk_id,
            )

            if key in seen:
                continue

            seen.add(key)

            metadata = chunk.metadata or {}

            if len(chunk.text) > 250:
                snippet = chunk.text[:250].strip() + "..."
            else:
                snippet = chunk.text.strip()

            citations.append(

                Citation(

                    resource_id=chunk.resource_id,

                    chunk_id=chunk.chunk_id,

                    title=(
                        metadata.get("title")
                        or metadata.get("filename")
                        or metadata.get("document_title")
                    ),

                    score=chunk.score,

                    snippet=snippet,

                )

            )

        logger.info(
            "Prepared %d unique citations.",
            len(citations),
        )

        return citations


###############################################################################
# Singleton Engine
###############################################################################

_engine: GenerationEngine | None = None


def get_generation_engine() -> GenerationEngine:
    """
    Returns a singleton GenerationEngine.

    Prevents recreating the OpenAI client for every request.
    """

    global _engine

    if _engine is None:

        logger.info(
            "Creating GenerationEngine singleton."
        )

        _engine = GenerationEngine()

    return _engine


###############################################################################
# Public Helper API
###############################################################################

def generate_answer(
    retrieval_result: RetrievalResult,
) -> GenerationResult:
    """
    Main public API.

    Used by chat_service.py after retrieval has completed.

    Example
    -------

    retrieval = retrieve_context(...)

    result = generate_answer(retrieval)

    print(result.answer)
    """

    engine = get_generation_engine()

    return engine.generate(
        retrieval_result
    )


def generate_from_question(
    question: str,
    resource_ids: list[str] | None = None,
    top_k: int = 5,
) -> GenerationResult:
    """
    Complete RAG helper.

    Performs Retrieval followed by Generation.

    Mostly useful for testing or CLI utilities.
    """

    from app.ai.retrieval.rag_retrieval import retrieve_context

    retrieval_result = retrieve_context(

        question=question,

        resource_ids=resource_ids,

        top_k=top_k,

    )

    return generate_answer(
        retrieval_result
    )
###############################################################################
# Health Check
###############################################################################

def health_check() -> bool:
    """
    Verifies that the Generation subsystem is operational.

    Checks
    ------
    • OpenAI client initialization
    • API key configuration
    • Model availability

    Returns
    -------
    bool
        True if healthy.
    """

    try:

        engine = get_generation_engine()

        if engine.client is None:

            logger.error(
                "Generation health check failed: "
                "OpenAI client missing."
            )

            return False

        logger.info(
            "Generation subsystem healthy."
        )

        return True

    except Exception as exc:

        logger.exception(
            "Generation health check failed: %s",
            exc,
        )

        return False


###############################################################################
# Debug Helpers
###############################################################################

def print_generation_statistics(
    result: GenerationResult,
) -> None:
    """
    Prints useful debugging information.

    Intended only for development.
    """

    logger.info(
        "========== Generation Statistics =========="
    )

    logger.info(
        "Model: %s",
        result.model,
    )

    logger.info(
        "Prompt Tokens: %d",
        result.prompt_tokens,
    )

    logger.info(
        "Completion Tokens: %d",
        result.completion_tokens,
    )

    logger.info(
        "Total Tokens: %d",
        result.total_tokens,
    )

    logger.info(
        "Generation Time: %.3f sec",
        result.generation_time,
    )

    logger.info(
        "Returned Citations: %d",
        len(result.citations),
    )


###############################################################################
# Future Extension Hooks
###############################################################################

class BasePostProcessor:
    """
    Base class for future answer post-processing.

    Examples
    --------
    • Markdown formatting
    • Citation numbering
    • Streaming output
    • HTML rendering
    • Source highlighting
    """

    def process(
        self,
        result: GenerationResult,
    ) -> GenerationResult:

        return result


class IdentityPostProcessor(
    BasePostProcessor
):
    """
    Default post-processor.

    Returns the answer unchanged.
    """

    pass


###############################################################################
# Default Post Processor
###############################################################################

_post_processor = IdentityPostProcessor()


def set_post_processor(
    processor: BasePostProcessor,
) -> None:
    """
    Registers a custom post-processor.
    """

    global _post_processor

    _post_processor = processor

    logger.info(
        "Custom post processor registered."
    )


def process_generation_result(
    result: GenerationResult,
) -> GenerationResult:
    """
    Applies the configured post-processor.

    Future versions may use this for:

    • citation numbering
    • markdown conversion
    • answer formatting
    • streaming chunks
    """

    return _post_processor.process(
        result
    )


###############################################################################
# Convenience Wrapper
###############################################################################

def ask(
    question: str,
    resource_ids: list[str] | None = None,
) -> GenerationResult:
    """
    High-level helper.

    Equivalent to:

        retrieve_context(...)
        ↓
        generate_answer(...)
        ↓
        return GenerationResult

    Useful for quick testing scripts.
    """

    result = generate_from_question(
        question=question,
        resource_ids=resource_ids,
    )

    return process_generation_result(
        result
    )


###############################################################################
# End of File
###############################################################################
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("Testing Generation Layer")
    print("=" * 60)

    fake_retrieval = RetrievalResult(
        prompt="""
CONTEXT

Python is a programming language.

QUESTION

What is Python?
""",
        chunks=[
            RetrievedChunk(
                chunk_id="chunk_1",
                resource_id="resource_1",
                text="Python is a programming language.",
                score=0.99,
                metadata={
                    "title": "Python Notes"
                }
            )
        ]
    )

    try:

        engine = GenerationEngine()

        print("✓ GenerationEngine initialized successfully")

        print(f"Model: {engine.client.model}")

    except Exception as e:

        print("Initialization failed")

        print(e)