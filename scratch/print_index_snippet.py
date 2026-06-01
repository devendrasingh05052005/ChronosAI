filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

snippet = content[7500:8100]
print(snippet.encode('ascii', errors='replace').decode('ascii'))
