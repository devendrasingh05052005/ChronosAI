import os
import sys

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\utils.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

found = False
for idx, line in enumerate(lines):
    if "def get_groq_api_keys" in line:
        found = True
        print(f"Found get_groq_api_keys on line {idx + 1}")
        for i in range(idx, idx + 40):
            print(lines[i].strip())
        break
