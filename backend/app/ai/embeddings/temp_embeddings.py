from embeddings import EmbeddingGenerator

generator = EmbeddingGenerator()

sample_chunks = [
    {
        "chunk_id": 1,
        "text": "Artificial Intelligence is transforming the world.",
        "length": 47
    },
    {
        "chunk_id": 2,
        "text": "Machine Learning allows computers to learn from data.",
        "length": 56
    },
    {
        "chunk_id": 3,
        "text": "Deep Learning uses neural networks with multiple layers.",
        "length": 59
    }
]

result = generator.generate(sample_chunks)

print(f"\nTotal Chunks: {len(result)}\n")

for chunk in result:

    print("=" * 70)

    print(f"Chunk ID : {chunk['chunk_id']}")

    print(f"Length   : {chunk['length']}")

    print(f"Vector Dimension : {len(chunk['embedding'])}")

    print("\nFirst 10 Values:")

    print(chunk["embedding"][:10])

    print()