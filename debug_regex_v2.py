import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import re

name_line = 'பெயர் : யுவராஜ் [J] வயர்: சர்மிளா [| [வயர் :புஷ்பதமயந்தி -'

# New Approach: Strip ALL possible delimiters first
clean_line = name_line.replace('[J]', ' ').replace('[|', ' ').replace('||', ' ')
clean_line = re.sub(r'[\[\]\(\)\|]', ' ', clean_line) # Strip all brackets and pipes
clean_line = re.sub(r'\s+', ' ', clean_line).strip() # Normalize whitespace
print(f"CLEAN LINE: {repr(clean_line)}")

name_line_split = re.sub(r'(பெயர்|வயர்|வயார்|வயகர்|Name)', r'|\1', clean_line, flags=re.IGNORECASE)
print(f"PIPED: {repr(name_line_split)}")

name_parts = [n.strip() for n in name_line_split.split('|') if n.strip()]
print(f"PARTS: {name_parts}")
