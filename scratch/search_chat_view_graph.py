with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\views.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- Printing lines 810 to 880 ---")
for i in range(809, min(879, len(lines))):
    print(f"{i + 1}: {lines[i]}", end="")
