import re

filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

print("--- Searching for year/semester filter elements ---")
for m in re.finditer(r'(?:year|sem|batch|2nd|3rd|4th|Year|Sem|4|6|8)', content, re.IGNORECASE):
    start = max(0, m.start() - 40)
    end = min(len(content), m.end() + 40)
    snippet = content[start:end].replace('\n', ' ')
    print(f"Match '{m.group(0)}' at {m.start()}: ... {snippet} ...")
