"""
chat.py
-------
Schemas for POST /chat.

Design notes
~~~~~~~~~~~~
* ``ChatRequest`` is the JSON body sent by the frontend. The only required
  field is ``question``; ``resource_ids`` is optional and scopes retrieval
  to specific resources.

* ``CitationSnippet`` represents a single chunk of retrieved text that the
  LLM used to construct its answer. Each snippet carries its source
  ``resource_id`` and optionally the resource ``title`` so the frontend
  can render linked citations.

* ``ChatResponse`` wraps the LLM answer, the ordered list of citations, and
  the definitive list of resource IDs that actually contributed context.
  The frontend should render citations from ``citations``, not infer them
  from ``resource_ids_used``.

* There is no streaming contract in this version. The entire response is
  returned as a single JSON object. Streaming (Server-Sent Events or
  chunked JSON) is deferred to a future phase.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """
    Request body for POST /chat.

    The frontend sends a natural-language question and optionally scopes
    the RAG retrieval to a subset of stored resources.

    Validation:
        - ``question`` must be a non-empty, non-whitespace-only string.
        - ``resource_ids``, when provided, must be a **non-empty** list.
          Pass ``null`` (or omit the field entirely) to search all resources.
        - Resources in ``resource_ids`` that are not in ``"ready"`` status
          are silently skipped by the service layer.

    Shape::

        {
          "question": "What are the key takeaways about neural networks?",
          "resource_ids": ["res_01j9k3m7xp0000000000000000"]
        }

    Or to search across all ready resources::

        {
          "question": "Summarise everything I have saved."
        }
    """

    question: Annotated[
        str,
        Field(
            ...,
            description=(
                "The user's natural-language question. "
                "Must be non-empty (whitespace-only strings are rejected)."
            ),
            examples=["What are the key takeaways about neural networks?"],
            min_length=1,
        ),
    ]
    resource_ids: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of resource IDs to scope the retrieval search. "
            "When null or omitted, the RAG pipeline searches across all 'ready' resources. "
            "When provided, must be a non-empty list — an empty list is rejected."
        ),
        examples=[
            ["res_01j9k3m7xp0000000000000000", "res_01j9k3m7xp0000000000000001"],
            None,
        ],
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("'question' must not be empty or whitespace-only.")
        return v.strip()

    @field_validator("resource_ids")
    @classmethod
    def resource_ids_must_not_be_empty_list(
        cls, v: list[str] | None
    ) -> list[str] | None:
        if v is not None and len(v) == 0:
            raise ValueError(
                "resource_ids must be a non-empty list when provided. "
                "Pass null or omit the field to search all resources."
            )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What are the key takeaways about neural networks?",
                    "resource_ids": [
                        "res_01j9k3m7xp0000000000000000",
                        "res_01j9k3m7xp0000000000000001",
                    ],
                },
                {
                    "question": "Summarise everything I have saved.",
                },
            ]
        }
    }


# ---------------------------------------------------------------------------
# Citation snippet (nested inside ChatResponse)
# ---------------------------------------------------------------------------


class CitationSnippet(BaseModel):
    """
    A single chunk of text retrieved from a resource and used by the LLM.

    Returned inside ``ChatResponse.citations`` so the frontend can render
    source attributions linked to the originating resource.

    Shape::

        {
          "resource_id": "res_01j9k3m7xp0000000000000000",
          "title": "Example Article Title",
          "snippet": "Residual connections allow gradients to flow..."
        }
    """

    resource_id: str = Field(
        ...,
        description="ID of the resource this snippet was retrieved from.",
        examples=["res_01j9k3m7xp0000000000000000"],
    )
    title: str | None = Field(
        default=None,
        description=(
            "Title of the source resource. "
            "Null if no title was extracted during ingestion."
        ),
        examples=["Example Article Title", None],
    )
    snippet: str = Field(
        ...,
        description=(
            "The exact chunk of text that was retrieved from ChromaDB "
            "and injected into the LLM prompt as context."
        ),
        examples=[
            (
                "Residual connections, introduced by He et al. (2016), allow gradients "
                "to flow directly through skip connections, effectively solving the "
                "vanishing gradient problem in very deep networks."
            )
        ],
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class ChatResponse(BaseModel):
    """
    Response body for POST /chat.

    Returned with HTTP 200 even when no relevant context was found.
    In that case, ``citations`` and ``resource_ids_used`` will be empty
    lists, and ``answer`` will explain that no relevant content was found.
    The frontend should handle this gracefully — it is NOT an error.

    Frontend rendering guidance:
        - Render the LLM answer from ``answer``.
        - Render source attributions from ``citations`` (ordered by relevance).
        - Use ``resource_ids_used`` to highlight which archive cards
          contributed to the answer — do NOT use the originally requested
          ``resource_ids`` for this purpose.
        - An empty ``citations`` list should be shown as "No sources found",
          not as an error state.

    Shape::

        {
          "answer": "The articles highlight three takeaways: ...",
          "citations": [
            {
              "resource_id": "res_01j9k3m7xp0000000000000000",
              "title": "Example Article Title",
              "snippet": "Residual connections..."
            }
          ],
          "resource_ids_used": ["res_01j9k3m7xp0000000000000000"]
        }
    """

    answer: str = Field(
        ...,
        description=(
            "The LLM-generated answer grounded in retrieved context. "
            "Always present — may state 'no relevant content found' if "
            "retrieval returned no results."
        ),
        examples=[
            (
                "The uploaded articles highlight three key takeaways about neural "
                "networks: (1) depth improves representational power, "
                "(2) residual connections mitigate vanishing gradients, and "
                "(3) attention mechanisms enable long-range dependency modelling."
            )
        ],
    )
    citations: list[CitationSnippet] = Field(
        default_factory=list,
        description=(
            "Ordered list of context snippets used to produce the answer. "
            "Empty when retrieval found no relevant chunks — this is NOT an error."
        ),
    )
    resource_ids_used: list[str] = Field(
        default_factory=list,
        description=(
            "IDs of all resources that contributed at least one chunk to the answer. "
            "May be a subset of the requested resource_ids. "
            "Use this — not the original request's resource_ids — to highlight sources."
        ),
        examples=[
            [
                "res_01j9k3m7xp0000000000000000",
                "res_01j9k3m7xp0000000000000001",
            ]
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": (
                        "The uploaded articles highlight three key takeaways about neural "
                        "networks: (1) depth improves representational power, "
                        "(2) residual connections mitigate vanishing gradients, and "
                        "(3) attention mechanisms enable long-range dependency modelling."
                    ),
                    "citations": [
                        {
                            "resource_id": "res_01j9k3m7xp0000000000000000",
                            "title": "Example Article Title",
                            "snippet": (
                                "Residual connections, introduced by He et al. (2016), "
                                "allow gradients to flow directly through skip connections."
                            ),
                        },
                        {
                            "resource_id": "res_01j9k3m7xp0000000000000001",
                            "title": "Research Paper.pdf",
                            "snippet": (
                                "Attention mechanisms compute a weighted sum over all "
                                "positions in a sequence, enabling long-range dependencies."
                            ),
                        },
                    ],
                    "resource_ids_used": [
                        "res_01j9k3m7xp0000000000000000",
                        "res_01j9k3m7xp0000000000000001",
                    ],
                }
            ]
        }
    }
