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

# Standard teachers pool:
TEACHERS_POOL = [
    "Ashish Kr Tiwari",
    "Badal Bose",
    "Dr. Vasima Khan",
    "Mr. Abhuday Tripathi",
    "Mr. Abhudy Tripathi",
    "Mr. Badal Hate",
    "Mr. Dheeraj Namdev",
    "Mr. Sachin Malviya",
    "Ms. Akshada Kulkarni",
    "Ms. Madhuri Walia",
    "Ms. Meha Shrivastava",
    "Ms. Ruchi Jain",
    "Mr. Arihant Jain",
    "Onaiza Ahmed"
]

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
    s4b_raw = _get_local_4th_sem_schedule()["schedule"]
    s6a_raw = _get_local_6th_sem_schedule()["schedule"]

    shift_4 = {
        "Monday": "Wednesday",
        "Tuesday": "Thursday",
        "Wednesday": "Friday",
        "Thursday": "Saturday",
        "Friday": "Monday",
        "Saturday": "Tuesday"
    }

    shift_6 = {
        "Monday": "Thursday",
        "Tuesday": "Friday",
        "Wednesday": "Saturday",
        "Thursday": "Monday",
        "Friday": "Tuesday",
        "Saturday": "Wednesday"
    }

    s4b = [dict(x) for x in s4b_raw]
    s4a = make_shifted_schedule(s4b_raw, "A", "Room 301", shift_4)

    s6a = [dict(x) for x in s6a_raw]
    s6b = make_shifted_schedule(s6a_raw, "B", "Room 303", shift_6)

    # We will resolve conflicts in s4a and s6b iteratively!
    # A teacher conflict occurs when at the same (day, start_time) a teacher is assigned in multiple places.
    # To fix it, we look for all busy teachers in that slot across all 4 schedules.
    # Then we pick a teacher from TEACHERS_POOL who is not busy in that slot.
    # We replace the teacher in s4a or s6b with this free teacher.
    # If the slot had multiple teachers (e.g. Lab), we replace all conflicting ones.

    all_schedules = [s4b, s4a, s6a, s6b]

    max_iterations = 100
    for iteration in range(max_iterations):
        conflicts_resolved = 0
        
        for s_idx, current_sch in enumerate(all_schedules):
            # We only modify s4a (s_idx=1) or s6b (s_idx=3) to preserve the original B and A schedules!
            if s_idx not in [1, 3]:
                continue
                
            for entry_idx, entry in enumerate(current_sch):
                day = entry["day"]
                time = entry["start_time"]
                
                # Find all busy teachers in this slot across ALL schedules
                busy_teachers = set()
                other_busy_entries = []
                for other_s_idx, other_sch in enumerate(all_schedules):
                    for other_entry in other_sch:
                        if other_entry["day"] == day and other_entry["start_time"] == time:
                            # Skip ourselves
                            if other_s_idx == s_idx and other_entry is entry:
                                continue
                            names = clean_teachers(other_entry["faculty"])
                            for n in names:
                                busy_teachers.add(n.lower())
                            other_busy_entries.append((other_s_idx, other_entry))
                
                # Check if our current entry's teachers overlap with other busy teachers
                our_teachers = clean_teachers(entry["faculty"])
                has_conflict = False
                conflicting_names = []
                for t in our_teachers:
                    if t.lower() in busy_teachers:
                        has_conflict = True
                        conflicting_names.append(t)
                        
                if has_conflict:
                    # Find free teachers from pool
                    free_pool = [t for t in TEACHERS_POOL if t.lower() not in busy_teachers and t not in our_teachers]
                    if len(free_pool) >= len(our_teachers):
                        # Replace the conflicting teachers in our entry!
                        new_fac_parts = []
                        orig_fac_parts = re.split(r'/|&|\band\b', entry["faculty"])
                        
                        pool_idx = 0
                        for part in orig_fac_parts:
                            part_clean = re.sub(r'\s*\([^)]*\)', '', part).strip()
                            if part_clean in conflicting_names:
                                # Replace with a free teacher from pool
                                replacement = free_pool[pool_idx]
                                pool_idx += 1
                                # Keep proxy notations or formatting if any
                                part_replaced = part.replace(part_clean, replacement)
                                new_fac_parts.append(part_replaced)
                            else:
                                new_fac_parts.append(part)
                                
                        new_faculty = " / ".join([p.strip() for p in new_fac_parts])
                        print(f"[RESOLVE] Slot {day} {time}: Swapped '{entry['faculty']}' -> '{new_faculty}' in {'4th Sem A' if s_idx==1 else '6th Sem B'} to resolve conflict with other years/sections")
                        entry["faculty"] = new_faculty
                        conflicts_resolved += 1
                        
        if conflicts_resolved == 0:
            print(f"SUCCESS: All conflicts resolved successfully in iteration {iteration}!")
            break
    else:
        print("Warning: Reached max iterations, some conflicts might remain.")

    # Re-verify
    print("\n--- Final Verification ---")
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
    print(f"Remaining conflicts: {len(final_conflicts)}")
    
    # Save the conflict-free lists to a python module format so we can print them or copy them!
    with open("scratch/resolved_schedules.py", "w", encoding="utf-8") as f:
        f.write("# Conflict-free schedules\n\n")
        f.write("S4A = " + repr(s4a) + "\n\n")
        f.write("S6B = " + repr(s6b) + "\n")
    print("Saved conflict-free schedules to scratch/resolved_schedules.py")

if __name__ == "__main__":
    main()
