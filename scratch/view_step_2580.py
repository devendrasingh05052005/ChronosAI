import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    try:
        data = json.loads(line)
        step = data.get("step_index", 0)
        if step == 2580:
            print(json.dumps(data, indent=2))
    except Exception as e:
        pass
