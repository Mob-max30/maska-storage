import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


class DocumentSummarizer:
    """
    DocumentSummarizer

    Responsible for:
    - Loading the Gemini model
    - Generating document summaries
    - Returning the generated summary

    This module does NOT perform:
    - Chunking
    - Embedding generation
    - Metadata generation
    - Database storage
    """

    def __init__(
    self,
    model_name: str = "gemini-3.6-flash"
):
        """
        Initializes the Gemini client.

        Args:
            model_name (str): Gemini model name.
        """

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment variables."
            )

        self.client = genai.Client(api_key=api_key)

        self.model = model_name

    def summarize(self, text: str) -> dict:
        """
        Generates a concise summary.

        Args:
            text (str): Cleaned document text.

        Returns:
            dict: Generated summary.
        """

        try:

            if not isinstance(text, str):
                raise ValueError("Input must be a string.")

            if not text.strip():
                raise ValueError("Input text is empty.")

            prompt = f"""
You are an expert document summarization assistant for the MaskaStorage Retrieval-Augmented Generation (RAG) system.

Your task is to produce a concise, accurate, and objective summary of the provided document. The summary will be stored as document metadata and used to help users quickly understand the document before asking questions about it.

Instructions:
- Read the entire document before summarizing.
- Capture the document's primary purpose, main ideas, key topics, and important conclusions.
- Preserve all essential factual information while removing repetition, navigation text, advertisements, and other irrelevant content.
- If the document contains multiple sections, combine them into one coherent summary.
- Maintain the original meaning and intent.
- Do not infer, assume, exaggerate, or fabricate information.
- Do not include personal opinions, interpretations, or external knowledge.
- Preserve technical terms, names, and important entities exactly as they appear in the document.

Output Requirements:
- Maximum 150 words.
- Write as a single well-structured paragraph.
- Use clear, concise, professional English.
- Return only the summary.

Document:

{text}
"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            return {
                "summary": response.text.strip()
            }

        except Exception as e:
            raise RuntimeError(
                f"Summarization Error: {e}"
            )