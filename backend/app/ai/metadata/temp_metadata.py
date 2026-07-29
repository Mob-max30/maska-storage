from metadata import MetadataGenerator

generator = MetadataGenerator()

sample_text = """
Artificial Intelligence (AI) is transforming healthcare by assisting
doctors in disease diagnosis, predictive analytics, personalized
medicine, and medical imaging.

Machine Learning algorithms analyze large datasets to identify
patterns that would be impossible for humans to detect manually.

AI systems are also improving hospital management, patient care,
drug discovery, and robotic surgery.
"""

metadata = generator.generate(
    text=sample_text,
    filename="ai_healthcare.pdf",
    title="Artificial Intelligence in Healthcare",
    chunk_count=5
)

print("\n========== METADATA ==========\n")

for key, value in metadata.items():
    print(f"{key}: {value}")