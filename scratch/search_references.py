import os
import re

print("--- Searching for _get_local_ references ---")
pattern = re.compile(r'_get_local_')

for root, dirs, files in os.walk("scheduler_api"):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f, 1):
                    if pattern.search(line):
                        print(f"{filepath}:{idx} - {line.strip()}")
