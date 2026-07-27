from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """
    EmbeddingGenerator

    Responsible for:
    - Loading the embedding model
    - Generating embeddings for text chunks
    - Generating embeddings for user queries

    This module does NOT perform:
    - Chunking
    - Summarization
    - Metadata generation
    - Database storage
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """
        Initializes the embedding model.

        Args:
            model_name (str): HuggingFace embedding model.
        """

        self.model = SentenceTransformer(model_name)

    def generate(self, chunks: list) -> list:
        """
        Generates embeddings for document text chunks.

        Args:
            chunks (list): List of chunk dictionaries.

        Returns:
            list: Chunks with embeddings added.
        """

        try:

            if not isinstance(chunks, list):
                raise ValueError("Input must be a list of chunks.")

            if len(chunks) == 0:
                raise ValueError("Chunk list is empty.")

            result = []

            for chunk in chunks:

                if "text" not in chunk:
                    raise ValueError("Chunk missing 'text' field.")

                embedding = self.model.encode(
                    chunk["text"],
                    normalize_embeddings=True
                )

                result.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "length": chunk["length"],
                        "embedding": embedding.tolist()
                    }
                )

            return result

        except Exception as e:
            raise RuntimeError(f"Embedding Generation Error: {e}")

    def generate_query_embedding(self, question: str) -> list[float]:
        """
        Generates an embedding for a user query.

        This is used by the Retrieval Engine to perform similarity
        search against stored document embeddings.

        Args:
            question (str): User's question.

        Returns:
            list[float]: Query embedding vector.
        """

        try:

            if not isinstance(question, str):
                raise ValueError("Question must be a string.")

            if not question.strip():
                raise ValueError("Question cannot be empty.")

            embedding = self.model.encode(
                question,
                normalize_embeddings=True
            )

            return embedding.tolist()

        except Exception as e:
            raise RuntimeError(f"Query Embedding Error: {e}")