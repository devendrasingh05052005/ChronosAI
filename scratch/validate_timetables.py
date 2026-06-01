# Standard conflict-free timetables generator and checker.
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

from scheduler_api.scheduling_utils import point_in_slot
import re

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

# Let's import the local schedules directly from our code or define them:
from scheduler_api.utils import _get_local_4th_sem_schedule, _get_local_6th_sem_schedule

# We will generate:
# - 4th Sem B = original 4th sem schedule
# - 4th Sem A = 4th sem B but shifted days (Monday -> Wednesday, etc.) and rooms -> Room 301
# - 6th Sem A = original 6th sem schedule
# - 6th Sem B = 6th sem A but shifted days (Monday -> Thursday, etc.) and rooms -> Room 303

def make_shifted_schedule(original_list, section_name, room_name, day_shift_map):
    new_list = []
    for entry in original_list:
        day = entry["day"]
        new_day = day_shift_map.get(day, day)
        new_entry = {
            "day": new_day,
            "start_time": entry["start_time"],
            "end_time": entry["end_time"],
            "subject": entry["subject"],
            "faculty": entry["faculty"],
            "academic_year": entry["academic_year"],
            "semester": entry["semester"],
            "section": section_name,
            "room_number": room_name
        }
        new_list.append(new_entry)
    return new_list

def main():
    # Load raw standard lists
    s4b_raw = _get_local_4th_sem_schedule()["schedule"]
    s6a_raw = _get_local_6th_sem_schedule()["schedule"]

    # Day shifts
    # 4th Sem: A is B shifted by 2 days
    shift_4 = {
        "Monday": "Wednesday",
        "Tuesday": "Thursday",
        "Wednesday": "Friday",
        "Thursday": "Saturday",
        "Friday": "Monday",
        "Saturday": "Tuesday"
    }

    # 6th Sem: B is A shifted by 3 days
    shift_6 = {
        "Monday": "Thursday",
        "Tuesday": "Friday",
        "Wednesday": "Saturday",
        "Thursday": "Monday",
        "Friday": "Tuesday",
        "Saturday": "Wednesday"
    }

    s4b = s4b_raw  # Keep B
    s4a = make_shifted_schedule(s4b_raw, "A", "Room 301", shift_4)

    s6a = s6a_raw  # Keep A
    s6b = make_shifted_schedule(s6a_raw, "B", "Room 303", shift_6)

    # Let's check for any double booking conflict within each schedule or across them!
    all_slots = s4b + s4a + s6a + s6b
    print(f"Total slots to check: {len(all_slots)}")

    conflicts = []
    for i in range(len(all_slots)):
        for j in range(i + 1, len(all_slots)):
            s1 = all_slots[i]
            s2 = all_slots[j]
            if s1["day"] == s2["day"] and s1["start_time"] == s2["start_time"]:
                # Check teacher overlap
                t1s = clean_teachers(s1["faculty"])
                t2s = clean_teachers(s2["faculty"])
                common = set(t1s).intersection(set(t2s))
                if common:
                    conflicts.append((s1, s2, common))

    print(f"Total conflicts found: {len(conflicts)}")
    if conflicts:
        for c in conflicts[:5]:
            print(f"Conflict on {c[0]['day']} at {c[0]['start_time']}:")
            print(f"  Slot 1: {c[0]['subject']} ({c[0]['academic_year']} Sec {c[0]['section']}) - {c[0]['faculty']}")
            print(f"  Slot 2: {c[1]['subject']} ({c[1]['academic_year']} Sec {c[1]['section']}) - {c[1]['faculty']}")
            print(f"  Overlapping teacher: {c[2]}")
    else:
        print("🎉 SUCCESS! No conflicts between the 4 schedules!")

if __name__ == "__main__":
    main()
