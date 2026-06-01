import os
import sys
import django
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.utils import get_groq_api_keys

keys = get_groq_api_keys()
key = keys[0]

url = "https://api.groq.com/openai/v1/models"
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json().get("data", [])
        print("=== Available Groq Models ===")
        for m in sorted(models, key=lambda x: x.get("id")):
            print(f"ID: {m.get('id')} | Owned By: {m.get('owned_by')}")
    else:
        print(f"Failed to list models: {response.status_code} - {response.text}")
except Exception as e:
    print("Error:", e)
