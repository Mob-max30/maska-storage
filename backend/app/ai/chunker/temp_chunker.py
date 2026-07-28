from chunker import TextChunker

chunker = TextChunker()

sample_text = """
Artificial Intelligence (AI) is transforming the way people interact with technology.

Machine learning allows computers to learn from data without being explicitly programmed.

Deep learning is a subset of machine learning that uses neural networks.

Natural Language Processing enables computers to understand human language.

Large Language Models are capable of generating human-like text.

""" * 50


chunks = chunker.chunk(sample_text)

print(f"\nTotal Chunks: {len(chunks)}\n")

for chunk in chunks:

    print("=" * 60)

    print(f"Chunk ID : {chunk['chunk_id']}")

    print(f"Length   : {chunk['length']}")

    print(chunk["text"][:250])

    print()