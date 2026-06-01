import os
import sys
import django

sys.path.append(r"c:\Users\jmsin\Desktop\chronosai")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from groq import Groq
from scheduler_api.utils import get_ocr_reader, OCR_SYSTEM_PROMPT

image_path = r"c:\Users\jmsin\Desktop\chronosai\media\timetables\ChatGPT_Image_May_29_2026_10_43_01_AM.png"
reader = get_ocr_reader()
results = reader.readtext(image_path, detail=0, paragraph=True)
raw_text = "\n".join(results)

print("--- TESTING openai/gpt-oss-120b with max_tokens=1500 ---")
groq_api_key = settings.GROQ_API_KEY
client = Groq(api_key=groq_api_key)

try:
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": OCR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this timetable OCR text into JSON:\n\n{raw_text}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1500,
    )
    raw_response = completion.choices[0].message.content
    import json
    parsed = json.loads(raw_response)
    schedule = parsed.get('schedule', [])
    print(f"SUCCESS! Number of rows extracted: {len(schedule)}")
    if len(schedule) == 36:
        print("[SUCCESS] openai/gpt-oss-120b successfully extracted all 36/36 entries!")
    else:
        print(f"[WARNING] Extracted only {len(schedule)} entries.")
except Exception as e:
    print(f"FAILED: {e}")
