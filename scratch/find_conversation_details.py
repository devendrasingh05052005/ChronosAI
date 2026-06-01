import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines in transcript: {len(lines)}")

for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        step = data.get("step_index", idx)
        if step >= 2570:
            print(f"\n========================================================")
            print(f"STEP: {step} | TYPE: {data.get('type')} | SOURCE: {data.get('source')}")
            print(f"========================================================")
            # print content
            content = data.get("content", "")
            if content:
                print(content[:800] + ("..." if len(content) > 800 else ""))
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                print("--- TOOL CALLS ---")
                print(json.dumps(tool_calls, indent=2))
    except Exception as e:
        pass
