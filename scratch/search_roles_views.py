import os
import sys

with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\views.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=== Checking Auth/Roles in views.py ===")
for idx, line in enumerate(lines):
    if "request.user" in line or "role" in line.lower() or "def dashboard" in line:
        print(f"Line {idx + 1}: {line.strip()}")
