import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import re

name_line = 'பெயர் : யுவராஜ் [J] வயர்: சர்மிளா [| [வயர் :புஷ்பதமயந்தி -'
name_line = name_line.replace('[J]', '|').replace('[|', '|').replace('||', '|')
print(f"NORMALIZED: {repr(name_line)}")

name_line_split = re.sub(r'(பெயர்|வயர்|வயார்|Name)', r'|\1', name_line, flags=re.IGNORECASE)
print(f"PIPED: {repr(name_line_split)}")

name_parts = name_line_split.split('|')
name_parts = [n.strip() for n in name_parts if n.strip()]
print(f"PARTS: {name_parts}")

for j, name in enumerate(name_parts):
    orig = name
    name = re.sub(r'^[\[\s]*(?:பெயர்|பெயயா|வயர்|வயார்|வயகர்|Name)\s*[:\s]*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'[\s\-\[\|]*$', '', name)
    name = name.split('Photo')[0].split('available')[0].strip()
    print(f"  PART {j} -> {repr(orig)} -> CLEAN: {repr(name)}")
