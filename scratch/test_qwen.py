import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from langchain_groq import ChatGroq
from scheduler_api.utils import get_groq_api_keys
from scheduler_api.agent_graph import TOOLS

keys = get_groq_api_keys()
key = keys[0]

print(f"Testing Qwen3-32b with key: {key[:15]}...")
try:
    llm = ChatGroq(
        model="qwen/qwen3-32b",
        api_key=key,
        temperature=0.1,
        max_tokens=2048,
    )
    llm_with_tools = llm.bind_tools(TOOLS)
    res = llm_with_tools.invoke("Hello, show me the Thursday schedule for Mr. Arihant Jain.")
    print("SUCCESS!")
    print(res)
except Exception as e:
    print("FAILED:", e)
