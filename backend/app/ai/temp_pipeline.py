from app.ai.pipeline import AIPipeline


pipeline = AIPipeline()

print("\nChoose Input Type")
print("1. URL")
print("2. PDF")

choice = input("\nEnter choice: ")


if choice == "1":

    url = input("\nEnter URL: ")

    result = pipeline.process_url(url)


elif choice == "2":

    pdf_path = input("\nEnter PDF Path: ")

    result = pipeline.process_pdf(pdf_path)


else:

    print("Invalid Choice")

    exit()


print("\n==============================")
print("AI PIPELINE RESULT")
print("==============================\n")

print("SOURCE TYPE:")
print(result["source_type"])

print("\nDOCUMENT:")
print(result["document"])

print("\nSUMMARY:")
print(result["summary"]["summary"])

print("\nMETADATA:")
print(result["metadata"])

print("\nTOTAL CHUNKS:")
print(len(result["chunks"]))

print("\nFIRST CHUNK:")
print(result["chunks"][0])

print("\nTOTAL EMBEDDINGS:")
print(len(result["embeddings"]))

print("\nFIRST EMBEDDING DIMENSION:")
print(len(result["embeddings"][0]["embedding"]))