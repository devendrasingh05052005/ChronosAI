import os
import sys
import django

# Add the workspace root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.models import Schedule

print("=== Checking TG / TG/Lib Lectures on Monday ===")
tg_schedules = Schedule.objects.filter(day_of_week__icontains="Monday", task_name__icontains="TG").select_related('employee')
for s in tg_schedules:
    print(f"  ID: {s.pk} | {s.academic_year} Sec {s.section} | {s.start_time} - {s.end_time} | {s.task_name} | {s.employee.name} | Room: {s.room_number}")
