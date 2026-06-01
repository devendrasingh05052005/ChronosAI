filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

offset = 37345
start = max(0, offset - 100)
end = min(len(content), offset + 300)
print(content[start:end])
