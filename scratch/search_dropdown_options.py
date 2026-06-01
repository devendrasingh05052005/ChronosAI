with open(r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

lines = html_content.splitlines()
found_populate = False
for idx, line in enumerate(lines):
    if "choose your name" in line.lower() or "register-employee" in line.lower() or "login-employee" in line.lower() or "choose" in line.lower():
        print(f"Line {idx + 1}: {line.strip()}")
        # print 8 lines after
        print("--- Context ---")
        for i in range(idx, min(len(lines), idx + 10)):
            print(f"{i + 1}: {lines[i]}")
        print("=" * 60)
