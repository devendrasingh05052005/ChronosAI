filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
print("--- Searching for year-tab-btn ---")
for m in re.finditer(r'year-tab-btn', content):
    start = max(0, m.start() - 200)
    end = min(len(content), m.end() + 200)
    print(f"Offset {m.start()}:\n{content[start:end]}\n{'-'*60}")
