from datetime import datetime

from langdetect import detect
import yake


class MetadataGenerator:
    """
    MetadataGenerator

    Responsible for:
    - Detecting document language
    - Calculating word count
    - Calculating character count
    - Estimating reading time
    - Extracting keywords
    - Returning structured metadata

    This module does NOT perform:
    - Chunking
    - Embedding generation
    - Summarization
    - Database storage
    """

    def __init__(self):

        self.keyword_extractor = yake.KeywordExtractor(
            lan="en",
            n=2,
            top=10
        )

    def generate(
        self,
        text: str,
        filename: str = None,
        title: str = None,
        chunk_count: int = None
    ) -> dict:
        """
        Generates metadata for a document.

        Args:
            text (str): Cleaned document text.
            filename (str): Optional filename.
            title (str): Optional document title.
            chunk_count (int): Number of generated chunks.

        Returns:
            dict: Document metadata.
        """

        try:

            if not isinstance(text, str):
                raise ValueError("Input must be a string.")

            if not text.strip():
                raise ValueError("Input text is empty.")

            words = text.split()

            word_count = len(words)

            character_count = len(text)

            reading_time = max(
                1,
                round(word_count / 200)
            )

            try:
                language = detect(text)
            except Exception:
                language = "unknown"

            keywords = self.keyword_extractor.extract_keywords(text)

            keywords = [
                keyword
                for keyword, score in keywords
            ]

            metadata = {
                "title": title,
                "filename": filename,
                "language": language,
                "word_count": word_count,
                "character_count": character_count,
                "reading_time_minutes": reading_time,
                "chunk_count": chunk_count,
                "keywords": keywords,
                "processed_at": datetime.utcnow().isoformat()
            }

            return metadata

        except Exception as e:
            raise RuntimeError(f"Metadata Generation Error: {e}")