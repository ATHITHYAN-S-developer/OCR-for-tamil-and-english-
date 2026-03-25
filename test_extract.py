import fitz
import pytesseract
import io
import os
from PIL import Image
from app import extract_voters_from_text

pdf_path = '../2026-EROLLGEN-S22-99-SIR-FinalRoll-Revision1-TAM-100-WI.pdf'
doc = fitz.open(pdf_path)
page = doc.load_page(3) # Page 4 (Voter Page)
pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72)) # 300 DPI
img_data = pix.tobytes("png")
img = Image.open(io.BytesIO(img_data))

# Extract
text = pytesseract.image_to_string(img, lang='tam+eng')
voters, _ = extract_voters_from_text(text)

print(f"Total Voters on Page 4: {len(voters)}")
for v in voters:
    print(v)
