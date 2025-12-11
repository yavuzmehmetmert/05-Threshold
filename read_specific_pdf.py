import os
from pypdf import PdfReader

target_pdf = "pdf/21-Running Training Visuals and Dashboards.pdf"

try:
    reader = PdfReader(target_pdf)
    text = ""



    # Print pages 3-10
    for i, page in enumerate(reader.pages[2:10]):
        print(f"--- PAGE {i+3} ---") # enumerate starts at 0, so page is index+2. 
        print(page.extract_text())
except Exception as e:
    print(f"Error: {e}")
