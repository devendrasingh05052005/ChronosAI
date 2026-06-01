import os
import sys

# Ensure workspace root is in sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from scheduler_api.models import Schedule, Employee, TimetableFile, SyllabusLog, SwapRequest
from scheduler_api.utils import (
    _get_local_4th_sem_a_schedule,
    _get_local_4th_sem_b_schedule,
    _get_local_6th_sem_a_schedule,
    _get_local_6th_sem_b_schedule,
    _get_local_8th_sem_schedule
)
from scheduler_api.views import _ensure_default_users

def seed_data():
    print("=== Seeding ChronosAI with 4 Conflict-Free Timetables ===")
    
    with transaction.atomic():
        # Clear existing schedules, logs, and swaps to avoid any stale data
        SyllabusLog.objects.all().delete()
        SwapRequest.objects.all().delete()
        Schedule.objects.all().delete()
        print("[*] Cleared old Schedules, Logs, and Swap Requests.")
        
        # Load the schedules
        schedules_to_load = []
        schedules_to_load.extend(_get_local_4th_sem_a_schedule()["schedule"])
        schedules_to_load.extend(_get_local_4th_sem_b_schedule()["schedule"])
        schedules_to_load.extend(_get_local_6th_sem_a_schedule()["schedule"])
        schedules_to_load.extend(_get_local_6th_sem_b_schedule()["schedule"])
        schedules_to_load.extend(_get_local_8th_sem_schedule()["schedule"]) # Also keep 8th sem!
        
        # Get or create employees cache
        employee_cache = {}
        for emp in Employee.objects.all():
            employee_cache[emp.name.strip()] = emp
            
        schedule_objects = []
        for row in schedules_to_load:
            day = row["day"]
            start_time = row["start_time"]
            end_time = row["end_time"]
            subject = row["subject"]
            faculty = row["faculty"]
            academic_year = row["academic_year"]
            semester = row["semester"]
            section = row["section"]
            room_number = row["room_number"]
            dept = "CSE-AIDS"
            
            # Split joint/composite faculty names
            import re
            faculty_parts = re.split(r'/|&|\band\b', faculty)
            faculty_names = []
            for p in faculty_parts:
                name = p.strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if name and name.lower() not in ['new faculty', 'none', 'tg/lib']:
                    faculty_names.append(name)
            
            if not faculty_names:
                faculty_names = [faculty.strip()]
                
            for name in faculty_names:
                if name not in employee_cache:
                    employee, _ = Employee.objects.get_or_create(
                        name=name,
                        defaults={'department': dept}
                    )
                    employee_cache[name] = employee
                    
                employee = employee_cache[name]
                
                schedule_objects.append(
                    Schedule(
                        employee=employee,
                        day_of_week=day,
                        start_time=start_time,
                        end_time=end_time,
                        task_name=subject,
                        is_proxy=False,
                        academic_year=academic_year,
                        semester=semester,
                        section=section,
                        room_number=room_number,
                        department=dept
                    )
                )
                
        Schedule.objects.bulk_create(schedule_objects)
        print(f"[*] Successfully seeded {len(schedule_objects)} active schedule slots across 2nd, 3rd, and 4th Years.")
        
        # Ensure default HOD and Faculty user accounts are seeded
        print("[*] Seeding default HOD and Faculty logins...")
        _ensure_default_users()
        
    print("=== Seeding completed successfully! ===")

if __name__ == "__main__":
    seed_data()
