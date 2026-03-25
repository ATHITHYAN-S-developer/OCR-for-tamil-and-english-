import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pytesseract, os, re, fitz
import numpy as np
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = os.path.abspath(os.path.join('..', 'tesseract', 'tesseract.exe'))

doc = fitz.open('../test_page.png' if os.path.exists('../test_page.png') else 'test_page.png')
# Since it might be an image, I'll just use PIL
if doc.is_pdf:
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
    img = Image.fromarray(np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n))
else:
    img = Image.open('../test_page.png')
    img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)

text = pytesseract.image_to_string(img, lang='tam+eng')
text = text.replace('\u200c', '').replace('\u200b', '')
lines = text.split('\n')

for i, line in enumerate(lines):
    if "RTW2687895" in line:
        print(f"\nFOUND EPIC RTW2687895 at line {i}")
        for k in range(-1, 5):
            if 0 <= i+k < len(lines):
                print(f"  [{i+k}]: {repr(lines[i+k])}")
