import os
import sys
import django

# Add the workspace root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.models import Schedule

print("=== Monday Lectures in Database ===")
monday_schedules = Schedule.objects.filter(day_of_week__icontains="Monday").select_related('employee').order_by('academic_year', 'section', 'start_time')

for s in monday_schedules:
    print(
        f"ID: {s.pk} | {s.academic_year} Sec {s.section} | "
        f"{s.start_time} - {s.end_time} | {s.task_name} | "
        f"Teacher: {s.employee.name} | Room: {s.room_number}"
    )
