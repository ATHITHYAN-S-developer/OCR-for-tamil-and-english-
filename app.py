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
        # We look for ANY epic code in the line (RTW, FSW, ITW, SWO, etc.)
        if re.search(r'[A-Z]{2,3}\d{6,}', line, re.IGNORECASE):
            epics = re.findall(r'([A-Z]{2,3}\d{6,})', line, re.IGNORECASE)
            if not epics:
                continue
                
            context = '\n'.join(lines[max(0, i):min(len(lines), i+8)])
            
            # Bilingual house, age, gender with fuzzy spacing
            houses = re.findall(r'(?:வீட்டு\s*எண்|House\s*No|எண்|எஎண|எண)\s*[:\s]*([0-9/\-A-Z]+)', context, re.IGNORECASE)
            ages = re.findall(r'(?:வயது|Age|வயத)\s*[:\s]*(\d{1,3})', context, re.IGNORECASE)
            genders = re.findall(r'(?:பாலினம்|பாலின|Gender|பாலீனம்)\s*[:\s]*([^\s]+)', context, re.IGNORECASE)
            
            # Vertical search for Name and Father lines (within next few lines)
            name_parts = []
            father_parts = []
            
            # 1. Search for Name Line
            name_kw = r'(பெயர்|பெயா|பெய|பபயர்|வயர்|வயார்|வயா|வயகர்|Name)'
            found_name_idx = -1
            for offset in range(1, 4): # Look up to 3 lines ahead
                idx = i + offset
                if idx < len(lines):
                    test_line = lines[idx]
                    if re.search(name_kw, test_line, re.IGNORECASE):
                        found_name_idx = idx
                        # Clean and Split
                        clean_l = test_line.replace('[J]', ' ').replace('[|', ' ').replace('||', ' ')
                        clean_l = re.sub(r'[\[\]\(\)\|]', ' ', clean_l)
                        clean_l = re.sub(r'\s+', ' ', clean_l).strip()
                        piped = re.sub(name_kw, r'|\1', clean_l, flags=re.IGNORECASE)
                        name_parts = [n.strip() for n in piped.split('|') if n.strip()]
                        break
            
            # 2. Search for Father Line (from after name_line or current line)
            father_kw = r'(தந்தையின்|தந்கையின்|தந்த்தையின்|தந்கை|தந்ததையின்|கணவர்|Father|Husband)'
            search_start = found_name_idx + 1 if found_name_idx != -1 else i + 1
            for idx in range(search_start, search_start + 4): # Look up to 4 lines ahead from last point
                if idx < len(lines):
                    test_line = lines[idx]
                    if re.search(father_kw, test_line, re.IGNORECASE):
                        clean_l = test_line.replace('[J]', ' ').replace('[|', ' ').replace('||', ' ')
                        clean_l = re.sub(r'[\[\]\(\)\|]', ' ', clean_l)
                        clean_l = re.sub(r'\s+', ' ', clean_l).strip()
                        piped = re.sub(father_kw, r'|\1', clean_l, flags=re.IGNORECASE)
                        father_parts = [f.strip() for f in piped.split('|') if f.strip()]
                        break
            
            for j, epic in enumerate(epics):
                voter = {
                    'Serial No': serial_no,
                    'EPIC Number': epic.upper(),
                    'Name': '',
                    'Father Name': '',
                    'House No': '',
                    'Age': '',
                    'Gender': ''
                }
                
                # Get Name
                if j < len(name_parts):
                    name = name_parts[j]
                    # Strip the keyword prefix
                    name = re.sub(r'^(?:பெயர்|பெயயா|பெயா|பபயர்|வயர்|வயார்|வயா|வயகர்|Name)\s*[:\s]*', '', name, flags=re.IGNORECASE)
                    # Strip trailing garbage: dashes, brackets, pipes, underscors, Photo markers
                    name = re.sub(r'[\s\-\[\]\|J0-9]*$', '', name).strip()
                    name = name.split('Photo')[0].split('available')[0].strip()
                    if len(name) > 1:
                        voter['Name'] = name
                        
                # Get Father Name
                if j < len(father_parts):
                    father = father_parts[j]
                    father = re.sub(r'^(?:தந்தையின்|தந்கையின்|தந்த்தையின்|தந்கை|தந்ததையின்|கணவர்|Father|Husband)\s*(?:பெயர்)?\s*[:\s]*', '', father, flags=re.IGNORECASE)
                    father = re.sub(r'[\s\-\[\]\|J0-9]*$', '', father).strip()
                    father = father.split('Photo')[0].split('வீட்')[0].strip()
                    if len(father) > 1:
                        voter['Father Name'] = father

                        
                # Assigment by index bounds (column-wise)
                if j < len(houses):
                    voter['House No'] = houses[j]
                
                if j < len(ages):
                    voter['Age'] = ages[j]
                    
                if j < len(genders):
                    v_gen = genders[j]
                    clean_gen = re.sub(r'[^a-zA-Z]', '', v_gen) # Strip Tamil letters
                    if 'ஆண்' in v_gen or 'Male' in clean_gen:
                        voter['Gender'] = 'Male'
                    elif 'பெண்' in v_gen or 'Female' in clean_gen:
                        voter['Gender'] = 'Female'
                    else:
                        voter['Gender'] = v_gen
                
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
            # Preprocessing: Convert to grayscale and improve contrast
            img = img.convert('L')
            from PIL import ImageOps
            img = ImageOps.invert(img) # Invert if necessary (usually black on white is better for Tesseract)
            img = ImageOps.invert(img) 
            # Upscale images to improve OCR clarity
            img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            text = pytesseract.image_to_string(img, lang='tam+eng', config='--psm 6')
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
                # High resolution 4x matrix for better Tesseract detection
                pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4: img_np = img_np[:, :, :3]
                pil_image = Image.fromarray(img_np)
                # Grayscale for OCR
                pil_image = pil_image.convert('L')
                
                text = pytesseract.image_to_string(pil_image, lang='tam+eng', config='--psm 6')
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
