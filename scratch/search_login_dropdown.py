with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

lines = html_content.splitlines()
for idx, line in enumerate(lines):
    if "all_employees" in line:
        print(f"Line {idx + 1}: {line.strip()}")
        print("--- Context ---")
        for i in range(max(0, idx - 5), min(len(lines), idx + 8)):
            print(f"{i + 1}: {lines[i]}")
        print("=" * 60)
