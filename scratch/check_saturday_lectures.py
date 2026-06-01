import os
import sys
import django

# Add the workspace root directory to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.models import Schedule

print("=== Saturday Lectures in Database ===")
saturday_schedules = Schedule.objects.filter(day_of_week__icontains="Saturday").select_related('employee').order_by('academic_year', 'section', 'start_time')

for s in saturday_schedules:
    print(
        f"ID: {s.pk} | {s.academic_year} Sec {s.section} | "
        f"{s.start_time} - {s.end_time} | {s.task_name} | "
        f"Teacher: {s.employee.name} | Room: {s.room_number}"
    )
