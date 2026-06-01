filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
print("--- Searching for Year Tab Switches or Selectors ---")
for m in re.finditer(r'(?:switchYear|2nd|3rd|4th|Year|YearTab)', content, re.IGNORECASE):
    start = max(0, m.start() - 60)
    end = min(len(content), m.end() + 60)
    snippet = content[start:end].replace('\n', ' ')
    clean_snippet = snippet.encode('ascii', errors='replace').decode('ascii')
    print(f"Offset {m.start()}: ... {clean_snippet} ...")
