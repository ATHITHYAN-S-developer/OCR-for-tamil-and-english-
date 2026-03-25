import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pytesseract, os, re
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = os.path.abspath(os.path.join('..', 'tesseract', 'tesseract.exe'))

# Use the cached text if possible to save time, but I'll re-run once more to be sure of layout
img = Image.open('../test_page.png')
text = pytesseract.image_to_string(img, lang='tam+eng')
text = text.replace('\u200c', '').replace('\u200b', '')
lines = text.split('\n')

for i, line in enumerate(lines):
    if "RTW2687895" in line:
        print(f"\nFOUND EPIC RTW2687895 at line {i}")
        for k in range(-1, 8):
            if 0 <= i+k < len(lines):
                print(f"  [{i+k}]: {repr(lines[i+k])}")
