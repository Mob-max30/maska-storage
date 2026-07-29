from parser import PDFParser

parser = PDFParser()

pdf_path = input("Enter PDF path: ")

result = parser.parse(pdf_path)

print("\nFilename:")
print(result["filename"])

print("\nPages:")
print(result["page_count"])

print("\nCharacters:")
print(len(result["text"]))

print("\nPreview:")
print(result["text"][:1000])