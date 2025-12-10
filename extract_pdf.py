import os
from pypdf import PdfReader

pdf_dir = "pdf"
output_file = "/Users/mertyavuz/.gemini/antigravity/brain/cfe09391-764e-4a85-a883-222537d8ce91/research_knowledge.md"

knowledge_base = "# Research Knowledge Base\n\n"

for filename in os.listdir(pdf_dir):
    if filename.endswith(".pdf"):
        print(f"Processing {filename}...")
        try:
            reader = PdfReader(os.path.join(pdf_dir, filename))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            knowledge_base += f"## {filename}\n\n{text[:5000]}...\n\n---\n\n" # Truncating for now to avoid huge context
        except Exception as e:
            print(f"Failed to read {filename}: {e}")

with open(output_file, "w") as f:
    f.write(knowledge_base)

print("Done.")
