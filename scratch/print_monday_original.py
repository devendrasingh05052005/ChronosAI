import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scheduler_api.utils import _get_local_6th_sem_a_schedule

sched = _get_local_6th_sem_a_schedule()
print("=== Original Monday Timetable for 3rd Year Sec A ===")
for item in sched["schedule"]:
    if item["day"].lower() == "monday":
        print(f"  {item['start_time']} - {item['end_time']} | {item['subject']} | {item['faculty']} | Room: {item['room_number']}")
