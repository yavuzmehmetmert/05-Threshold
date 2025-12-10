import sys
try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        print("No PDF library found. Installing pypdf...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
        from pypdf import PdfReader

def extract_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

if __name__ == "__main__":
    pdf_path = "pdf/21-Running Training Visuals and Dashboards.pdf"
    content = extract_text(pdf_path)
    print("--- PDF CONTENT START ---")
    print(content)
    print("--- PDF CONTENT END ---")
