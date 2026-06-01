import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    try:
        data = json.loads(line)
        step = data.get("step_index", idx)
        tool_calls = data.get("tool_calls", [])
        for tc in tool_calls:
            if tc.get("name") == "swap_faculty_lectures_tool":
                print(f"[{step}] Executed swap_faculty_lectures_tool!")
                print(f"  Args: {json.dumps(tc.get('args'), indent=2)}")
                # Check response
                if idx + 1 < len(lines):
                    resp_data = json.loads(lines[idx + 1])
                    print(f"  Response (Step {resp_data.get('step_index')}):")
                    print(resp_data.get("content", "")[:600])
                print("=" * 60)
    except:
        pass
