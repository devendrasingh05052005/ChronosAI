import sys
import os

with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\views.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

found_chat = False
start_line = -1
for idx, line in enumerate(lines):
    if "def chat_api" in line or "class Chat" in line or "api/chat" in line or "chat(" in line:
        print(f"Found match on line {idx + 1}: {line.strip()}")
        start_line = idx
        break

if start_line != -1:
    print(f"--- Printing lines {start_line + 1} to {start_line + 60} ---")
    for i in range(start_line, min(start_line + 60, len(lines))):
        print(f"{i + 1}: {lines[i]}", end="")
