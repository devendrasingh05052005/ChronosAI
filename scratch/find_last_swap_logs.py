import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines in transcript: {len(lines)}")

# We look at the last 20 steps or search for "swap the both deep learning"
for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        content = data.get("content", "")
        # Search for queries of interest
        if "swap" in content.lower() and "saturday" in content.lower():
            print(f"\n--- STEP {data.get('step_index', idx)} (Source: {data.get('source')}) ---")
            print("Content:", content[:200])
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                print("Tool Calls:", json.dumps(tool_calls, indent=2))
    except Exception as e:
        pass
