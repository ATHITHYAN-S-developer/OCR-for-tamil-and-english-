import os
import re
import fitz
import pytesseract
from PIL import Image
import numpy as np
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Increase upload limit to 100MB for large PDFs
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Configure Tesseract Path based on user's directory structure
TESSERACT_PATH = os.path.abspath(os.path.join(os.getcwd(), '..', 'tesseract', 'tesseract.exe'))
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Database Setup
def init_db():
    conn = sqlite3.connect('voters.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_no INTEGER,
            epic_number TEXT,
            name TEXT,
            father_name TEXT,
            house_no TEXT,
            age TEXT,
            gender TEXT,
            source_file TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_to_db(voters, filename):
    conn = sqlite3.connect('voters.db')
    try:
        cursor = conn.cursor()
        for v in voters:
            cursor.execute('''
                INSERT INTO voters (serial_no, epic_number, name, father_name, house_no, age, gender, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (v.get('Serial No'), v.get('EPIC Number'), v.get('Name'), v.get('Father Name'), v.get('House No'), v.get('Age'), v.get('Gender'), filename))
        conn.commit()
    finally:
        conn.close()

def extract_voters_from_text(text, start_serial=1):
    text = text.replace('\u200c', '').replace('\u200b', '') # Clear hidden formatting
    voters = []
    lines = text.split('\n')
    serial_no = start_serial
    
    for i, line in enumerate(lines):
        clean_line = line.strip()
        if not clean_line: continue
            
        # 1. Look for EPIC IDs in line
        epics = re.findall(r'([A-Z0-9]{2,3}\d{4,})', clean_line, re.IGNORECASE)
        
        # 2. Look for Serial Numbers at start of line (1-3 digits)
        # We look for numbers that aren't followed by "Page", "Date", or "Year"
        # e.g. "^ 123 " or "123 RTW" or "123 பெயர்"
        serial_matches = re.findall(r'(?:\n|^)\s*(\d{1,4})(?=\s+(?:[A-Z0-9]{3}|பெயர்|Name|வயது|Age))', '\n' + clean_line, re.MULTILINE)
        
        # Determine effective "voter count" for this trigger line
        voter_count = max(len(epics), len(serial_matches))
        
        # Trigger if we found AT LEAST one EPIC or clear Serial Number
        if voter_count == 0:
            # Special fallback for very garbled lines: check if it's just an EPIC alone
            if re.search(r'[A-Z]{1,2}[0-9/]{3,}', clean_line):
                epics = re.findall(r'([A-Z0-9]{2,3}\d{3,})', clean_line, re.IGNORECASE)
                if not epics: continue
                voter_count = len(epics)
            else:
                continue

        # Use epics if found, otherwise use placeholder for serial-only detection
        trigger_epics = epics if epics else ["MISSING_EPIC"] * voter_count

        # Vertical search for Name and Father lines (within next few lines)
        name_parts = []
        father_parts = []
        
        # 1. Search for Name Line
        name_kw = r'(பெயர்|பெயா|பெய|பபயர்|வயர்|வயார்|வயா|வயகர்|Name)'
        found_name_idx = -1
        # Look ahead up to 6 lines to find the names
        for offset in range(1, 7): 
            idx = i + offset
            if idx < len(lines):
                test_line = lines[idx]
                if re.search(name_kw, test_line, re.IGNORECASE):
                    found_name_idx = idx
                    cl = test_line.replace('[J]', ' ').replace('[|', ' ').replace('||', ' ')
                    cl = re.sub(r'[\[\]\(\)\|]', ' ', cl)
                    cl = re.sub(r'\s+', ' ', cl).strip()
                    piped = re.sub(name_kw, r'|\1', cl, flags=re.IGNORECASE)
                    name_parts = [n.strip() for n in piped.split('|') if n.strip()]
                    break
        
        # 2. Search for Father Line
        father_kw = r'(தந்தையின்|தந்கையின்|தந்த்தையின்|தந்கை|தந்ததையின்|கணவர்|Father|Husband)'
        search_start = found_name_idx + 1 if found_name_idx != -1 else i + 1
        for idx in range(search_start, search_start + 7): 
            if idx < len(lines):
                test_line = lines[idx]
                if re.search(father_kw, test_line, re.IGNORECASE):
                    cl = test_line.replace('[J]', ' ').replace('[|', ' ').replace('||', ' ')
                    cl = re.sub(r'[\[\]\(\)\|]', ' ', cl)
                    cl = re.sub(r'\s+', ' ', cl).strip()
                    piped = re.sub(father_kw, r'|\1', cl, flags=re.IGNORECASE)
                    father_parts = [f.strip() for f in piped.split('|') if f.strip()]
                    break

        # Context for house/age/gender - slightly wider window for multi-voter rows
        context = '\n'.join(lines[max(0, i):min(len(lines), i+15)])
        houses = re.findall(r'(?:வீட்டு\s*எண்|House\s*No|எண்|எஎண|எண)\s*[:\s]*([0-9/\-A-Z]+)', context, re.IGNORECASE)
        ages = re.findall(r'(?:வயது|Age|வயத)\s*[:\s]*(\d{1,3})', context, re.IGNORECASE)
        genders = re.findall(r'(?:பாலினம்|பாலின|Gender|பாலீனம்)\s*[:\s]*([^\s]+)', context, re.IGNORECASE)
        
        for j in range(voter_count):
            epic = trigger_epics[j] if j < len(trigger_epics) else "MISSING"
            
            voter = {
                'Serial No': serial_no,
                'EPIC Number': epic.upper() if epic != "MISSING_EPIC" else "MISSING",
                'Name': '',
                'Father Name': '',
                'House No': '',
                'Age': '',
                'Gender': ''
            }
            
            # Name assignment
            if j < len(name_parts):
                val = name_parts[j]
                val = re.sub(f'^{name_kw}\s*[:\s]*', '', val, flags=re.IGNORECASE)
                val = re.sub(r'[\s\-\[\]\|J0-9]*$', '', val).strip()
                val = val.split('Photo')[0].split('available')[0].split('வீட்டு')[0].strip()
                if len(val) > 1: voter['Name'] = val
                    
            # Father assignment
            if j < len(father_parts):
                val = father_parts[j]
                val = re.sub(f'^{father_kw}\s*(?:பெயர்)?\s*[:\s]*', '', val, flags=re.IGNORECASE)
                val = re.sub(r'[\s\-\[\]\|J0-9]*$', '', val).strip()
                val = val.split('Photo')[0].split('வீட்')[0].split('வயது')[0].strip()
                if len(val) > 1: voter['Father Name'] = val
            
            # Match metadata from context by relative count
            if j < len(houses): voter['House No'] = houses[j]
            if j < len(ages): voter['Age'] = ages[j]
            if j < len(genders):
                v_gen = genders[j]
                clean_gen = re.sub(r'[^a-zA-Z]', '', v_gen)
                if 'ஆண்' in v_gen or 'Male' in clean_gen: voter['Gender'] = 'Male'
                elif 'பெண்' in v_gen or 'Female' in clean_gen: voter['Gender'] = 'Female'
                else: voter['Gender'] = v_gen
            
            # Validation: Don't add completely empty records
            if voter['Name'] or voter['EPIC Number'] != "MISSING":
                voters.append(voter)
                serial_no += 1
                
    return voters, serial_no


@app.route('/ocr', methods=['POST'])
def process_ocr():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    filename = file.filename
    temp_path = f"temp_{os.urandom(4).hex()}.pdf"
    file.save(temp_path)
    
    # Read page range from request (1-indexed, user-facing)
    try:
        start_page = max(1, int(request.form.get('start_page', 1))) - 1  # convert to 0-indexed
    except:
        start_page = 0
    try:
        end_page_raw = request.form.get('end_page', '').strip()
        end_page = int(end_page_raw) if end_page_raw else None  # None = all pages
    except:
        end_page = None
    
    try:
        final_voters = []
        final_text = ""
        
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(temp_path)
            # Upscale images to improve OCR clarity
            img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            # Use PSM 3 (Automatic) which is more robust for finding EPICs
            text = pytesseract.image_to_string(img, lang='tam+eng', config='--psm 3')
            voters, _ = extract_voters_from_text(text)
            final_voters = voters
            final_text = text
        else:
            doc = fitz.open(temp_path)
            total_pages = len(doc)
            
            # Clamp end_page to actual total pages
            if end_page is None or end_page > total_pages:
                end_page = total_pages
            if start_page >= total_pages:
                start_page = 0
            
            current_serial = 1
            for page_num in range(start_page, end_page):
                page = doc[page_num]
                # High resolution 4x matrix
                pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4: img_np = img_np[:, :, :3]
                pil_image = Image.fromarray(img_np)
                # Add contrast and sharpening to improve legibility
                from PIL import ImageEnhance, ImageFilter
                # Original image for Tamil
                # Enhanced copy for EPIC/Numbers
                enhancer = ImageEnhance.Contrast(pil_image)
                pil_image = enhancer.enhance(2.0)
                pil_image = pil_image.filter(ImageFilter.SHARPEN)
                
                # Use PSM 3 (Automatic) - Experiment showed PSM 6 misses EPICs
                text = pytesseract.image_to_string(pil_image, lang='tam+eng', config='--psm 3')
                voters, next_serial = extract_voters_from_text(text, start_serial=current_serial)
                current_serial = next_serial
                
                final_voters.extend(voters)
                final_text += f"--- Page {page_num + 1} ---\n{text}\n\n"
            doc.close()
        
        # Save to SQLite Database
        if final_voters:
            save_to_db(final_voters, filename)
            
        return jsonify({'voters': final_voters, 'raw_text': final_text})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == '__main__':
    app.run(port=5000, debug=True)
