import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        step = data.get("step_index", idx)
        if data.get("type") == "USER_INPUT":
            content = data.get("content", "")
            if any(w in content.lower() for w in ["swap", "learning", "saturday"]):
                print(f"[{step}] USER_INPUT: {content.strip()}")
    except Exception as e:
        pass
