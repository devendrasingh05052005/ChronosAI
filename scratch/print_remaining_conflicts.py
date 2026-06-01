import os
import sys

# Ensure workspace root is in sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import re
from scheduler_api.utils import _get_local_4th_sem_schedule, _get_local_6th_sem_schedule
from scratch.resolved_schedules import S4A, S6B

def clean_teachers(faculty_str):
    parts = re.split(r'/|&|\band\b', faculty_str)
    names = []
    for p in parts:
        name = p.strip()
        name = re.sub(r'\s*\([^)]*\)', '', name).strip()
        if name and name.lower() not in ['new faculty', 'none', 'tg/lib']:
            names.append(name)
    if not names:
        names = [faculty_str.strip()]
    return names

def main():
    s4b = _get_local_4th_sem_schedule()["schedule"]
    s6a = _get_local_6th_sem_schedule()["schedule"]
    s4a = S4A
    s6b = S6B

    all_slots = s4b + s4a + s6a + s6b
    final_conflicts = []
    for i in range(len(all_slots)):
        for j in range(i + 1, len(all_slots)):
            s1 = all_slots[i]
            s2 = all_slots[j]
            if s1["day"] == s2["day"] and s1["start_time"] == s2["start_time"]:
                t1s = clean_teachers(s1["faculty"])
                t2s = clean_teachers(s2["faculty"])
                common = set(t1s).intersection(set(t2s))
                if common:
                    final_conflicts.append((s1, s2, common))
    
    print(f"Total remaining conflicts: {len(final_conflicts)}")
    for idx, (s1, s2, common) in enumerate(final_conflicts, 1):
        print(f"Conflict #{idx} on {s1['day']} at {s1['start_time']}:")
        print(f"  Slot A: {s1['subject']} ({s1['academic_year']} Sec {s1['section']}) - {s1['faculty']}")
        print(f"  Slot B: {s2['subject']} ({s2['academic_year']} Sec {s2['section']}) - {s2['faculty']}")
        print(f"  Teacher: {common}")

if __name__ == "__main__":
    main()
