import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    try:
        data = json.loads(line)
        # Search for any line that has tool calls in any form
        for key in data.keys():
            if "tool" in key.lower():
                print(f"Found key: {key} in step {data.get('step_index')}")
                print(json.dumps(data, indent=2)[:500])
                break
    except:
        pass
