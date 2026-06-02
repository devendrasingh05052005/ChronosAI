import os
import sys
import traceback

# Setup Django env
sys.path.append(r"c:\Users\jmsin\Desktop\chronosai")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from scheduler_api.utils import get_groq_api_keys
from langchain_groq import ChatGroq

print("--- DIAGNOSTIC: Testing Groq Connection ---")
keys = get_groq_api_keys()
print(f"Total keys retrieved: {len(keys)}")

for idx, key in enumerate(keys):
    masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "invalid"
    print(f"\nTesting Key Index {idx} ({masked_key}):")
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=key,
            timeout=10
        )
        response = llm.invoke("Hello, quick test.")
        print(f"  [SUCCESS] Connection succeeded! Response: {response.content}")
    except Exception as e:
        print(f"  [FAILED] Connection failed with exception class: {type(e).__name__}")
        print("  Error message:")
        print(f"    {str(e)}")
        print("\n  Full Traceback:")
        traceback.print_exc()

print("\n--- Testing direct API Endpoint via HTTPS ---")
try:
    import urllib.request
    import json
    
    url = "https://api.groq.com/openai/v1/models"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {keys[0]}" if keys else "")
    
    with urllib.request.urlopen(req, timeout=5) as response:
        html = response.read().decode('utf-8')
        print("  [SUCCESS] Direct HTTPS request to api.groq.com succeeded!")
        print("  Available models parsed successfully.")
except Exception as e:
    print(f"  [FAILED] Direct HTTPS request failed: {type(e).__name__}: {str(e)}")
