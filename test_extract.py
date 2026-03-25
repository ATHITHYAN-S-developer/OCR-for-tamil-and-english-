import fitz
import pytesseract
from PIL import Image
from app import extract_voters_from_text

img = Image.open('../2026-EROLLGEN-S22-99-SIR-FinalRoll-Revision1-TAM-100-WI.pdf')
text = pytesseract.image_to_string(img, lang='tam+eng')
voters, _ = extract_voters_from_text(text)
for v in voters:
    print(v)
