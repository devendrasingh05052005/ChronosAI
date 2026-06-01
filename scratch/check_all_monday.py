import os
import sys
import django

# Add the workspace root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.models import Schedule

print("=== Checking Monday 15:10 - 16:10 Slots ===")
monday_last = Schedule.objects.filter(day_of_week__icontains="Monday", start_time="15:10").select_related('employee').order_by('academic_year', 'section')
for s in monday_last:
    print(f"  {s.academic_year} Sec {s.section} | {s.start_time} - {s.end_time} | {s.task_name} | {s.employee.name} | Room: {s.room_number}")
