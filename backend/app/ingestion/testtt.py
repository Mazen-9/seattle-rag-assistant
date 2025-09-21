import glob
from pypdf import PdfReader

pdfs = glob.glob("docs/raw/*.pdf")

if not pdfs:
    print("No PDFs found in docs/raw/")
else:
    for path in pdfs:
        try:
            reader = PdfReader(path)
            print(f"{path}: Encrypted? {reader.is_encrypted}")
        except Exception as e:
            print(f"{path}: ERROR -> {e}")
