import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pytesseract, os, re
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = os.path.abspath(os.path.join('..', 'tesseract', 'tesseract.exe'))

img = Image.open('../test_page.png')
text = pytesseract.image_to_string(img, lang='tam+eng')
text = text.replace('\u200c', '').replace('\u200b', '')
lines = text.split('\n')

target_epic = "RTW2687895"

for i, line in enumerate(lines):
    if target_epic.lower() in line.lower():
        print(f"\n{'='*60}")
        print(f"FOUND TARGET EPIC: {target_epic} at line {i}")
        print(f"LINE {i}: {repr(line)}")
        for k in range(-2, 7):
            if 0 <= i+k < len(lines):
                print(f"  [{i+k}]: {repr(lines[i+k])}")
