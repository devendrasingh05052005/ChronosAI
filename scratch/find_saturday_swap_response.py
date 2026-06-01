import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

found_user_msg = False
for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        content = data.get("content", "")
        if "swap the both deep learning lectures with internet of things" in content.lower() and data.get("type") == "USER_INPUT":
            found_user_msg = True
            print(f"=== User Request at Step {data.get('step_index')} ===")
            print(content)
            print("-" * 50)
            
        if found_user_msg and data.get("step_index") > idx:
            # Print subsequent steps until the next USER_INPUT
            step = data.get("step_index")
            print(f"[{step}] Source={data.get('source')} Type={data.get('type')}")
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    print(f"  Tool: {tc.get('name')}")
                    print(f"  Args: {tc.get('args')}")
            if content:
                print("  Content preview:")
                print("\n".join(content.split("\n")[:10]))
            print("-" * 50)
            if data.get("type") == "USER_INPUT":
                break
    except Exception as e:
        pass
