import os
import sys
import django

# Add the workspace root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.models import Schedule

print("=== Raw Monday Schedules ===")
monday_schedules = Schedule.objects.filter(day_of_week__iexact="Monday").select_related('employee')
print(f"Total Monday records: {monday_schedules.count()}")
for s in monday_schedules:
    print(
        f"ID: {s.pk} | {s.academic_year} Sec {s.section} | "
        f"start_time: {repr(s.start_time)} | end_time: {repr(s.end_time)} | "
        f"task_name: {repr(s.task_name)} | Teacher: {repr(s.employee.name)}"
    )
