"""
backend/app/api/routes/chat.py
--------------------------------
POST /chat — RAG question-answering.

Route responsibility
~~~~~~~~~~~~~~~~~~~~
* Accept and validate the ``ChatRequest`` JSON body (handled by Pydantic).
* Delegate to ``chat_service.create_chat_response``.
* Return the service result directly.

What does NOT live here
~~~~~~~~~~~~~~~~~~~~~~~
* No mock citations or answers — those live in chat_service.
* No embedding, ChromaDB, or LLM calls — ever.
* No retrieval scoping logic.

Pydantic validators in ``ChatRequest`` enforce:
  - ``question`` is non-empty and non-whitespace-only.
  - ``resource_ids``, if provided, is a non-empty list.
FastAPI returns a 422 automatically if these validators fail.
"""

from __future__ import annotations

from app.schemas import ChatRequest, ChatResponse
from app.services import chat_service
from fastapi import APIRouter, status

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question via RAG",
    description=(
        "Accepts a natural-language question and runs the RAG pipeline: "
        "embed the question → similarity search → top-k context → LLM → answer. "
        "Returns the answer with source citations. "
        "Optionally scope retrieval to specific resource IDs."
    ),
    tags=["chat"],
)
def ask_question(
    request: ChatRequest,
) -> ChatResponse:
    """
    Delegate to chat_service.create_chat_response and return the result.

    The route never calls embedding, retrieval, or LLM logic directly.
    An empty citations list is a valid 200 response — not an error.
    """
    return chat_service.create_chat_response(
        question=request.question,
        resource_ids=request.resource_ids,
    )
