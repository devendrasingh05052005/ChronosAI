import os
import sys
import django

sys.path.append(r"c:\Users\jmsin\Desktop\chronosai")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import easyocr
from scheduler_api.utils import get_ocr_reader, process_timetable_image

image_path = r"c:\Users\jmsin\Desktop\chronosai\media\timetables\ChatGPT_Image_May_29_2026_10_43_01_AM.png"
reader = get_ocr_reader()
results = reader.readtext(image_path, detail=0, paragraph=True)
raw_text = "\n".join(results)

print("="*60)
print("RAW OCR TEXT FOR NEW UPLOAD:")
print("="*60)
print(raw_text)

print("\n" + "="*60)
print("RUNNING INGESTION:")
print("="*60)
result = process_timetable_image(image_path)
import pprint
pprint.pprint(result)
print(f"Number of rows extracted: {len(result.get('schedule', []))}")
