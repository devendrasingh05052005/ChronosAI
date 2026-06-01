with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\views.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- Printing lines 860 to 950 ---")
for i in range(859, min(950, len(lines))):
    line = lines[i]
    clean_line = line.encode('ascii', 'ignore').decode('ascii').strip()
    print(f"{i + 1}: {clean_line}")
