import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pytesseract, os, re, fitz
import numpy as np
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = os.path.abspath(os.path.join('..', 'tesseract', 'tesseract.exe'))

pdfs = [f for f in os.listdir('..') if f.endswith('.pdf')]
if pdfs:
    target_pdf = os.path.join('..', pdfs[0])
    doc = fitz.open(target_pdf)
    page = doc[3] # Page 4
    
    for scale in [3, 4, 5]:
        print(f"\n--- TESTING SCALE {scale}x ---")
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img = Image.fromarray(np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n))
        if pix.n == 4: img = img.convert('RGB')
        
        for psm in [3, 6, 11]:
            text = pytesseract.image_to_string(img, lang='tam+eng', config=f'--psm {psm}')
            # Count EPIC-like strings
            epics = re.findall(r'[A-Z]{2,3}\d{6,}', text, re.IGNORECASE)
            print(f"PSM {psm}: Found {len(epics)} EPICs. Sample: {epics[:3]}")
    doc.close()
