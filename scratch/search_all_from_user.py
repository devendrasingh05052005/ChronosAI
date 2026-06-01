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
        # If we see the user's request
        if "swap the both deep learning lectures" in content.lower():
            found_user_msg = True
        
        if found_user_msg:
            print(f"\n================ STEP {step} ================")
            print(f"Source: {data.get('source')} | Type: {data.get('type')}")
            if content:
                print("Content:")
                print(content[:600] + ("..." if len(content) > 600 else ""))
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                print("Tool Calls:")
                print(json.dumps(tool_calls, indent=2))
    except Exception as e:
        pass
