with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

import re
matches = [m.start() for m in re.finditer("my_sent_requests", html_content)]
print(f"Found {len(matches)} occurrences of 'my_sent_requests' in index.html")

lines = html_content.splitlines()
for idx, line in enumerate(lines):
    if "my_sent_requests" in line:
        print(f"Line {idx + 1}: {line.strip()}")
        # print context
        print("--- Context ---")
        for i in range(max(0, idx - 5), min(len(lines), idx + 8)):
            print(f"{i + 1}: {lines[i]}")
        print("=" * 60)
