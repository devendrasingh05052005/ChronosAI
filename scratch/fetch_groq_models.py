import os
import sys
import django

sys.path.append(r"c:\Users\jmsin\Desktop\chronosai")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from groq import Groq

groq_api_key = settings.GROQ_API_KEY
client = Groq(api_key=groq_api_key)

try:
    models = client.models.list()
    print("--- ACTIVE GROQ MODELS ---")
    for m in models.data:
        print(f"Model ID: '{m.id}' | Owned by: '{m.owned_by}'")
except Exception as e:
    print(f"Error fetching models: {e}")
