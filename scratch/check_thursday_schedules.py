import os
import sys

# Ensure workspace root is in sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import django

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.models import Schedule, Employee
from scheduler_api.scheduling_utils import point_in_slot

def main():
    print("=== Thursday Schedules check ===")
    schedules = Schedule.objects.filter(day_of_week__iexact='Thursday').select_related('employee')
    print(f"Total Thursday schedules in DB: {schedules.count()}")
    
    busy_at_1135 = []
    for s in schedules:
        if point_in_slot('11:35', s.start_time, s.end_time):
            busy_at_1135.append(s)
            print(f"  [{s.start_time} - {s.end_time}] {s.task_name} ({s.academic_year} Sec {s.section}) - Teacher: {s.employee.name}")
            
    print(f"\nTotal busy at 11:35: {len(busy_at_1135)}")
    
    all_employees = list(Employee.objects.all().order_by('name'))
    busy_ids = [b.employee_id for b in busy_at_1135]
    busy_names = [b.employee.name for b in busy_at_1135]
    
    free_employees = [e for e in all_employees if e.id not in busy_ids and e.name not in busy_names]
    print(f"\nTotal all employees in DB: {len(all_employees)}")
    print(f"Total free at 11:35: {len(free_employees)}")
    for f in free_employees:
        print(f"  - {f.name}")

if __name__ == '__main__':
    main()
