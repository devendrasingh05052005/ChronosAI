with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- Printing lines 2000 to 2020 ---")
for i in range(1999, min(2020, len(lines))):
    line = lines[i]
    print(f"{i + 1}: {line.strip()}")
