import re


class TextCleaner:
    """
    TextCleaner

    Responsible for:
    - Removing excessive whitespace
    - Removing tabs
    - Removing non-printable characters
    - Normalizing line breaks
    - Returning cleaned text

    This module does NOT perform:
    - Chunking
    - Embedding generation
    - Summarization
    - Metadata generation
    """

    def clean(self, text: str) -> str:
        """
        Cleans extracted text from a URL or PDF.

        Args:
            text (str): Raw extracted text.

        Returns:
            str: Cleaned and normalized text.
        """

        try:
            if not isinstance(text, str):
                raise ValueError("Input must be a string.")

            # Remove tabs
            text = text.replace("\t", " ")

            # Remove carriage returns
            text = text.replace("\r", "\n")

            # Remove non-printable characters
            text = re.sub(r"[^\x20-\x7E\n]", "", text)

            # Remove multiple spaces
            text = re.sub(r"[ ]{2,}", " ", text)

            # Normalize multiple blank lines
            text = re.sub(r"\n{3,}", "\n\n", text)

            # Trim whitespace
            text = text.strip()

            return text

        except Exception as e:
            raise RuntimeError(f"Cleaning Error: {e}")