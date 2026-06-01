import os
import sys

with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\views.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=== Views in views.py ===")
for idx, line in enumerate(lines):
    if "def " in line and line.strip().startswith("def ") and not line.strip().startswith("def _"):
        print(f"Line {idx + 1}: {line.strip()}")
    elif "class " in line and line.strip().startswith("class "):
        print(f"Line {idx + 1}: {line.strip()}")
