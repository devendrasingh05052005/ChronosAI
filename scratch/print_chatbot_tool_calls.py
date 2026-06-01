import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        step = data.get("step_index", idx)
        tool_calls = data.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("name", "")
                if "swap" in name or "search_subject" in name:
                    print(f"[{step}] Tool Call: {name}")
                    print(f"  Args: {tc.get('args')}")
                    # Also print the response in the next step
                    if idx + 1 < len(lines):
                        next_data = json.loads(lines[idx + 1])
                        print(f"  [{next_data.get('step_index')}] Response:")
                        print(next_data.get("content", "")[:300])
                    print("-" * 50)
    except Exception as e:
        pass
