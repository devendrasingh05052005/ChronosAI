filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
print("--- Searching for year tab buttons ---")
for m in re.finditer(r'btn-year-\w+', content):
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 100)
    snippet = content[start:end].replace('\n', ' ')
    clean_snippet = snippet.encode('ascii', errors='replace').decode('ascii')
    print(f"Offset {m.start()}: ... {clean_snippet} ...")
