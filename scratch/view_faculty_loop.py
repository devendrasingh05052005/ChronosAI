with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- Printing lines 565 to 620 ---")
for i in range(564, min(620, len(lines))):
    line = lines[i]
    print(f"{i + 1}: {line.strip()}")
