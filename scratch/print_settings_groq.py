import os
import sys

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with open(r"c:\Users\jmsin\Desktop\chronosai\core\settings.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "GROQ_API_KEY" in line or "GROQ" in line:
        print(f"{idx + 1}: {line.strip()}")
