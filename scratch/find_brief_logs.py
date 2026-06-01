import json

transcript_path = r"C:\Users\jmsin\.gemini\antigravity\brain\979ec97f-aafd-4c12-bc0b-abca6a8bf04f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    try:
        data = json.loads(line)
        step = data.get("step_index", 0)
        if step >= 2580 and step < 2643:
            print(f"[{step}] Source={data.get('source')} Type={data.get('type')}")
            # If tool calls are present
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    print(f"  -> Calling Tool: {tc.get('name')} with args: {tc.get('args')}")
            # If it has a short summary of content
            content = data.get("content", "")
            if content:
                # print first few lines of content
                lines_content = [l.strip() for l in content.split("\n") if l.strip()][:5]
                print("  Content preview:")
                for lc in lines_content:
                    print(f"    {lc[:150]}")
            print("-" * 50)
    except Exception as e:
        pass
