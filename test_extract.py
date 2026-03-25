import fitz
import pytesseract
from PIL import Image
from app import extract_voters_from_text

img = Image.open('../test_page.png')
text = pytesseract.image_to_string(img, lang='tam+eng')
voters, _ = extract_voters_from_text(text)
for v in voters:
    print(v)
