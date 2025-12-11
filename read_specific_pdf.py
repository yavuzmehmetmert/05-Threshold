import os
from pypdf import PdfReader

target_pdf = "pdf/21-Running Training Visuals and Dashboards.pdf"

try:
    reader = PdfReader(target_pdf)
    text = ""

    # Print only first 2 pages
    for i, page in enumerate(reader.pages[:2]):
        print(f"--- PAGE {i+1} ---")
        print(page.extract_text())
except Exception as e:
    print(f"Error: {e}")
