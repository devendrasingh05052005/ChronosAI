with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

lines = html_content.splitlines()
for idx, line in enumerate(lines):
    if "appendMessage" in line or "sendMessage" in line or "typing" in line.lower() or "chat-messages" in line.lower():
        print(f"Line {idx + 1}: {line.strip()}")
