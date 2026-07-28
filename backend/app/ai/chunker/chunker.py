from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextChunker:
    """
    TextChunker

    Responsible for:
    - Splitting cleaned text into semantic chunks
    - Preserving context using chunk overlap
    - Returning structured chunk data

    This module does NOT perform:
    - Embedding generation
    - Summarization
    - Metadata generation
    - Database storage
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initializes the Recursive Character Text Splitter.

        Args:
            chunk_size (int): Maximum size of each chunk.
            chunk_overlap (int): Number of overlapping characters
                                 between consecutive chunks.
        """

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                ""
            ]
        )

    def chunk(self, text: str) -> list:
        """
        Splits cleaned text into semantic chunks.

        Args:
            text (str): Cleaned document text.

        Returns:
            list: List of structured chunks.
        """

        try:

            if not isinstance(text, str):
                raise ValueError("Input must be a string.")

            if not text.strip():
                raise ValueError("Input text is empty.")

            chunks = self.splitter.split_text(text)

            result = []

            for index, chunk in enumerate(chunks):

                result.append(
                    {
                        "chunk_id": index + 1,
                        "text": chunk,
                        "length": len(chunk)
                    }
                )

            return result

        except Exception as e:
            raise RuntimeError(f"Chunking Error: {e}")