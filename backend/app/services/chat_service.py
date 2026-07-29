"""
backend/app/services/chat_service.py
-----------------------------------

Service layer for the RAG chat endpoint.

Responsibilities
----------------
• Validate and orchestrate the Retrieval + Generation pipeline.
• Call RetrievalEngine.
• Call GenerationEngine.
• Convert GenerationResult into ChatResponse.
• Handle graceful failures.

Routes must NEVER call Retrieval or Generation directly.
"""

from __future__ import annotations

import logging

from app.schemas import (
    ChatResponse,
    CitationSnippet,
)

from app.ai.retrieval.rag_retrieval import (
    retrieve_context,
    extract_resource_ids,
)

from app.ai.generation.rag_generation import (
    generate_answer,
    GenerationError,
)

logger = logging.getLogger(__name__)

###############################################################################
# Configuration
###############################################################################

DEFAULT_TOP_K = 5

NO_CONTEXT_MESSAGE = (
    "I couldn't find enough information in the uploaded resources "
    "to answer that question."
)

INTERNAL_ERROR_MESSAGE = (
    "An unexpected error occurred while processing your request. "
    "Please try again."
)

###############################################################################
# Public API
###############################################################################


def create_chat_response(
    question: str,
    resource_ids: list[str] | None,
) -> ChatResponse:
    """
    Execute the complete Retrieval-Augmented Generation pipeline.

    Pipeline

        User Question
              │
              ▼
        Retrieval Engine
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
        Generation Engine
              │
              ▼
        ChatResponse
    """

    logger.info(
        "Received chat request (question_length=%d, scoped=%s, resources=%s)",
        len(question),
        resource_ids is not None,
        len(resource_ids) if resource_ids else "ALL",
    )

    try:

        #######################################################################
        # Retrieval
        #######################################################################

        retrieval_result = retrieve_context(
            question=question,
            resource_ids=resource_ids,
            top_k=DEFAULT_TOP_K,
        )

        #######################################################################
        # No Context
        #######################################################################

        if not retrieval_result.chunks:

            logger.info(
                "No relevant chunks retrieved."
            )

            return ChatResponse(
                answer=NO_CONTEXT_MESSAGE,
                citations=[],
                resource_ids_used=[],
            )

        logger.info(
            "Retrieved %d chunks.",
            len(retrieval_result.chunks),
        )

        #######################################################################
        # Generation
        #######################################################################

        generation_result = generate_answer(
            retrieval_result
        )

        #######################################################################
        # Convert Citations
        #######################################################################

        citations = [

            CitationSnippet(

                resource_id=citation.resource_id,

                title=citation.title,

                snippet=citation.snippet,

            )

            for citation in generation_result.citations

        ]

        #######################################################################
        # Resource IDs Used
        #######################################################################

        resource_ids_used = extract_resource_ids(
            retrieval_result.chunks
        )

        #######################################################################
        # Build Response
        #######################################################################

        logger.info(
            "Returning grounded response with %d citations.",
            len(citations),
        )

        return ChatResponse(

            answer=generation_result.answer,

            citations=citations,

            resource_ids_used=resource_ids_used,

        )

    ###########################################################################
    # Expected Generation / Retrieval Errors
    ###########################################################################

    except GenerationError as exc:

        logger.exception(
            "Generation failed."
        )

        return ChatResponse(

            answer=str(exc)
            if str(exc)
            else INTERNAL_ERROR_MESSAGE,

            citations=[],

            resource_ids_used=[],

        )

    ###########################################################################
    # Unexpected Errors
    ###########################################################################

    except Exception:

        logger.exception(
            "Unexpected error during chat pipeline."
        )

        return ChatResponse(

            answer=INTERNAL_ERROR_MESSAGE,

            citations=[],

            resource_ids_used=[],

        )


###############################################################################
# Convenience Wrapper
###############################################################################

def ask(
    question: str,
    resource_ids: list[str] | None = None,
) -> ChatResponse:
    """
    Convenience wrapper for testing.

    Equivalent to:

        create_chat_response(...)
    """

    return create_chat_response(
        question=question,
        resource_ids=resource_ids,
    )


###############################################################################
# Health Check
###############################################################################

def health_check() -> bool:
    """
    Verifies that both Retrieval and Generation
    subsystems are operational.
    """

    try:

        from app.ai.retrieval.rag_retrieval import (
            health_check as retrieval_health,
        )

        from app.ai.generation.rag_generation import (
            health_check as generation_health,
        )

        return (
            retrieval_health()
            and generation_health()
        )

    except Exception:

        logger.exception(
            "Chat service health check failed."
        )

        return False


###############################################################################
# End of File
###############################################################################