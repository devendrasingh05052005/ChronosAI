filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("btn-year-all_years")
start = max(0, idx - 150)
end = min(len(content), idx + 800)
print(content[start:end])
