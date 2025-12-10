import os
from pypdf import PdfReader

target_pdf = "pdf/21-Running Training Visuals and Dashboards.pdf"

try:
    reader = PdfReader(target_pdf)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    print(text)
except Exception as e:
    print(f"Error: {e}")
