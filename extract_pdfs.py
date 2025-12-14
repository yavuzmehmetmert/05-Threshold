#!/usr/bin/env python3
"""Extract text from all PDF files in the pdf folder."""

from PyPDF2 import PdfReader
import os

pdf_dir = 'pdf'
output_dir = 'pdf_extracted'

os.makedirs(output_dir, exist_ok=True)

pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.endswith('.pdf')])

for pdf_file in pdf_files:
    pdf_path = os.path.join(pdf_dir, pdf_file)
    output_path = os.path.join(output_dir, pdf_file.replace('.pdf', '.txt'))
    
    try:
        reader = PdfReader(pdf_path)
        text = ''
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n\n---PAGE---\n\n'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f'✓ {pdf_file} -> {len(text)} chars')
    except Exception as e:
        print(f'✗ {pdf_file}: {e}')

print(f'\nExtracted {len(pdf_files)} PDFs to {output_dir}/')
