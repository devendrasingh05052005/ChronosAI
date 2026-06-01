import os
import sys
import django

sys.path.append(r"c:\Users\jmsin\Desktop\chronosai")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from groq import Groq
from scheduler_api.utils import get_ocr_reader

FALLBACK_OCR_SYSTEM_PROMPT = """You are an academic timetable parsing AI.
Your job is to read raw OCR text and convert it into a strictly-formatted JSON object with exactly 36 daily class schedule entries.

DIRECTIONS:
1. Identify the Semester from raw text:
   - "4_B" or "4th" or "DBMS" ➔ academic_year="2nd Year", semester=4, section="B"
   - "6_A" or "6th" or "Internet of Things" ➔ academic_year="3rd Year", semester=6, section="A"
   - "8_A" or "8th" ➔ academic_year="4th Year", semester=8, section="A"
   All entries default to room_number="Room 302", department="CSE-AIDS".

2. Reconstruct the 6 days (Monday-Saturday) x 6 periods grid (36 entries total) dynamically:
   - Map the sequence of subjects and faculty following each day marker (Mo, Tu, We, Th, Fr, Sa) to these 6 periods in order:
     - Period 1: 09:35-10:35, Period 2: 10:35-11:35, Period 3: 11:35-12:35, Period 4: 12:35-13:35, Period 5: 14:10-15:10, Period 6: 15:10-16:10.
   - You MUST split any 2-period lab or lecture spans (spans of 2 hours, or containing "Lab") into TWO separate, identical 1-hour entries.
   - You MUST output EXACTLY 36 entries in the JSON (6 for each day). Fill empty slots with Subject "TG/Lib", Faculty "Mr. Sachin Malviya".

Clean up names to match standard forms (e.g. "Ms. Akshada Kulkarni", "Ms. Ruchi Jain", "Mr. Dheeraj Namdev", "Mr. Arihant Jain", "Mr. Badal Hate", "Ms. Meha Shrivastava", "Onaiza Ahmed", "Dr. Vasima Khan").

OUTPUT FORMAT:
Output ONLY a valid JSON object. No markdown fences.
{
  "schedule": [
     {"day": "Monday", "start_time": "09:35", "end_time": "10:35", "subject": "DBMS", "faculty": "Mr. Sachin Malviya", "academic_year": "2nd Year", "semester": 4, "section": "B", "room_number": "Room 302"}
  ]
}"""

image_path = r"c:\Users\jmsin\Desktop\chronosai\media\timetables\ChatGPT_Image_May_29_2026_10_43_01_AM.png"
reader = get_ocr_reader()
results = reader.readtext(image_path, detail=0, paragraph=True)
raw_text = "\n".join(results)

print("--- TESTING llama-3.1-8b-instant with COMPACT FALLBACK PROMPT ---")
groq_api_key = settings.GROQ_API_KEY
client = Groq(api_key=groq_api_key)

try:
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": FALLBACK_OCR_SYSTEM_PROMPT},
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
         print("[SUCCESS] llama-3.1-8b-instant successfully extracted all 36/36 entries using the compact fallback prompt!")
         # Print first few to verify
         import pprint
         pprint.pprint(schedule[:3])
    else:
         print(f"[WARNING] Extracted only {len(schedule)} entries.")
         import pprint
         pprint.pprint(schedule)
except Exception as e:
    print(f"FAILED: {e}")
