import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

count = 0
for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        if data.get("source") == "MODEL":
            print(f"Step: {data.get('step_index')} | Type: {data.get('type')}")
            print(f"  Content: {data.get('content')[:150] if data.get('content') else 'None'}")
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                print(f"  Tool Calls: {[tc.get('name') for tc in tool_calls]}")
            count += 1
            if count >= 30:
                break
    except Exception as e:
        pass
