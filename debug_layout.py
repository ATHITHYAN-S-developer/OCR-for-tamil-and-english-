import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pytesseract, os, re
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = os.path.abspath(os.path.join('..', 'tesseract', 'tesseract.exe'))

img = Image.open('../test_page.png')
text = pytesseract.image_to_string(img, lang='tam+eng')
text = text.replace('\u200c', '').replace('\u200b', '')
lines = text.split('\n')

EPIC_RE = re.compile(r'[A-Z]{2,3}\d{6,}', re.IGNORECASE)

for i, line in enumerate(lines):
    if EPIC_RE.search(line):
        print(f"\n{'='*60}")
        print(f"[LINE {i}] EPIC LINE: {repr(line)}")
        for k in range(1, 7):
            if i+k < len(lines):
                print(f"  [+{k}]: {repr(lines[i+k])}")
        break  # Show only first EPIC for now - remove 'break' to see all
