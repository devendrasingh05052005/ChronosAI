import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

found_user_msg = False
for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        step = data.get("step_index", idx)
        content = data.get("content", "")
        if "swap the both deep learning lectures with internet of things" in content.lower():
            found_user_msg = True
        
        if found_user_msg and step <= 2600:
            print(f"[{step}] {data.get('source')} | {data.get('type')}")
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    print(f"  Tool: {tc.get('name')}")
                    print(f"  Args: {tc.get('args')}")
            if content:
                clean_lines = [l.strip() for l in content.split("\n") if l.strip()]
                print(f"  Text: {clean_lines[:3] if clean_lines else ''}")
            print("-" * 40)
    except Exception as e:
        pass
