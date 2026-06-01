with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

import re
matches = [m.start() for m in re.finditer("swap", html_content, re.IGNORECASE)]
print(f"Found {len(matches)} occurrences of 'swap' in index.html")

lines = html_content.splitlines()
for idx, line in enumerate(lines):
    if "swap" in line.lower():
        print(f"Line {idx + 1}: {line.strip()}")
