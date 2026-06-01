filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
print("--- Searching for data-year ---")
for m in re.finditer(r'data-year', content):
    start = max(0, m.start() - 150)
    end = min(len(content), m.end() + 250)
    print(f"Offset {m.start()}:\n{content[start:end]}\n{'-'*60}")
