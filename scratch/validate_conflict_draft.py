# Let's draft and test conflict-free standard timetables for:
# - 2nd Year (4th Semester) Section A (CSE-AIDS-4_A)
# - 2nd Year (4th Semester) Section B (CSE-AIDS-4_B)
# - 3rd Year (6th Semester) Section A (CSE-AIDS-6_A)
# - 3rd Year (6th Semester) Section B (CSE-AIDS-6_B)

# Let's import tools to validate double bookings
from scheduler_api.scheduling_utils import point_in_slot
import re

# Standard teachers list:
# "Ms. Madhuri Walia", "Mr. Arihant Jain", "Mr. Sachin Malviya", "Ms. Ruchi Jain", "Mr. Abhuday Tripathi", "Ms. Akshada Kulkarni", "Ashish Kr Tiwari", "Onaiza Ahmed", "Mr. Dheeraj Namdev", "Dr. Vasima Khan", "Ms. Meha Shrivastava", "Mr. Badal Hate"

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

# 4th Sem B (existing standard)
sem4_b = [
    # Monday
    {"day": "Monday", "start_time": "09:35", "end_time": "10:35", "subject": "Operating Systems Lab", "faculty": "Ms. Madhuri Walia / Mr. Arihant Jain"},
    {"day": "Monday", "start_time": "10:35", "end_time": "11:35", "subject": "Operating Systems Lab", "faculty": "Ms. Madhuri Walia / Mr. Arihant Jain"},
    {"day": "Monday", "start_time": "11:35", "end_time": "12:35", "subject": "DBMS", "faculty": "Mr. Sachin Malviya"},
    {"day": "Monday", "start_time": "12:35", "end_time": "13:35", "subject": "Operating Systems", "faculty": "Ms. Madhuri Walia"},
    {"day": "Monday", "start_time": "14:10", "end_time": "15:10", "subject": "Data Science", "faculty": "Ms. Ruchi Jain / Mr. Abhuday Tripathi"},
    {"day": "Monday", "start_time": "15:10", "end_time": "16:10", "subject": "Data Science", "faculty": "Ms. Ruchi Jain / Mr. Abhuday Tripathi"},
    # Tuesday
    {"day": "Tuesday", "start_time": "09:35", "end_time": "10:35", "subject": "DBMS", "faculty": "Mr. Sachin Malviya"},
    {"day": "Tuesday", "start_time": "10:35", "end_time": "11:35", "subject": "Mathematics III", "faculty": "Ms. Akshada Kulkarni"},
    {"day": "Tuesday", "start_time": "11:35", "end_time": "12:35", "subject": "Data Analytics using tools", "faculty": "Ms. Ruchi Jain / Mr. Arihant Jain"},
    {"day": "Tuesday", "start_time": "12:35", "end_time": "13:35", "subject": "Data Analytics using tools", "faculty": "Ms. Ruchi Jain / Mr. Arihant Jain"},
    {"day": "Tuesday", "start_time": "14:10", "end_time": "15:10", "subject": "Aptitude & Communication Skills", "faculty": "Ashish Kr Tiwari"},
    {"day": "Tuesday", "start_time": "15:10", "end_time": "16:10", "subject": "Communication Skills", "faculty": "Onaiza Ahmed"},
    # Wednesday
    {"day": "Wednesday", "start_time": "09:35", "end_time": "10:35", "subject": "Software Engineering with Agile Methodology", "faculty": "Mr. Abhuday Tripathi"},
    {"day": "Wednesday", "start_time": "10:35", "end_time": "11:35", "subject": "DBMS", "faculty": "Mr. Sachin Malviya"},
    {"day": "Wednesday", "start_time": "11:35", "end_time": "12:35", "subject": "Software Engineering with Agile Methodology Lab", "faculty": "Mr. Abhuday Tripathi / Mr. Dheeraj Namdev"},
    {"day": "Wednesday", "start_time": "12:35", "end_time": "13:35", "subject": "Software Engineering with Agile Methodology Lab", "faculty": "Mr. Abhuday Tripathi / Mr. Dheeraj Namdev"},
    {"day": "Wednesday", "start_time": "14:10", "end_time": "15:10", "subject": "Mathematics III", "faculty": "Ms. Akshada Kulkarni"},
    {"day": "Wednesday", "start_time": "15:10", "end_time": "16:10", "subject": "Data Science", "faculty": "Ms. Ruchi Jain"},
    # Thursday
    {"day": "Thursday", "start_time": "09:35", "end_time": "10:35", "subject": "Mathematics III", "faculty": "Ms. Akshada Kulkarni"},
    {"day": "Thursday", "start_time": "10:35", "end_time": "11:35", "subject": "Operating Systems", "faculty": "Ms. Madhuri Walia"},
    {"day": "Thursday", "start_time": "11:35", "end_time": "12:35", "subject": "Competitive Programming", "faculty": "Mr. Arihant Jain"},
    {"day": "Thursday", "start_time": "12:35", "end_time": "13:35", "subject": "Competitive Programming", "faculty": "Mr. Arihant Jain"},
    {"day": "Thursday", "start_time": "14:10", "end_time": "15:10", "subject": "Data Science", "faculty": "Ms. Ruchi Jain"},
    {"day": "Thursday", "start_time": "15:10", "end_time": "16:10", "subject": "TG/Lib", "faculty": "Mr. Dheeraj Namdev / Mr. Sachin Malviya"},
    # Friday
    {"day": "Friday", "start_time": "09:35", "end_time": "10:35", "subject": "Database Management Systems Lab", "faculty": "New Faculty / Mr. Sachin Malviya"},
    {"day": "Friday", "start_time": "10:35", "end_time": "11:35", "subject": "Database Management Systems Lab", "faculty": "New Faculty / Mr. Sachin Malviya"},
    {"day": "Friday", "start_time": "11:35", "end_time": "12:35", "subject": "Software Engineering with Agile Methodology", "faculty": "Mr. Abhuday Tripathi"},
    {"day": "Friday", "start_time": "12:35", "end_time": "13:35", "subject": "Operating Systems", "faculty": "Ms. Madhuri Walia"},
    {"day": "Friday", "start_time": "14:10", "end_time": "15:10", "subject": "Aptitude & Communication Skills", "faculty": "Ashish Kr Tiwari"},
    {"day": "Friday", "start_time": "15:10", "end_time": "16:10", "subject": "Communication Skills", "faculty": "Onaiza Ahmed"},
    # Saturday
    {"day": "Saturday", "start_time": "09:35", "end_time": "10:35", "subject": "Mathematics III", "faculty": "Ms. Akshada Kulkarni"},
    {"day": "Saturday", "start_time": "10:35", "end_time": "11:35", "subject": "Operating Systems", "faculty": "Ms. Madhuri Walia"},
    {"day": "Saturday", "start_time": "11:35", "end_time": "12:35", "subject": "Software Engineering with Agile Methodology", "faculty": "Mr. Abhuday Tripathi"},
    {"day": "Saturday", "start_time": "12:35", "end_time": "13:35", "subject": "DBMS", "faculty": "Mr. Sachin Malviya"},
    {"day": "Saturday", "start_time": "14:10", "end_time": "15:10", "subject": "Data Science", "faculty": "Ms. Ruchi Jain / Mr. Abhuday Tripathi"},
    {"day": "Saturday", "start_time": "15:10", "end_time": "16:10", "subject": "Data Science", "faculty": "Ms. Ruchi Jain / Mr. Abhuday Tripathi"},
]

# 4th Sem A (Let's design it by offsetting or swapping days/times to avoid conflicts with 4th Sem B!)
sem4_a = []
for entry in sem4_b:
    # Offset periods or swap days
    # Let's say:
    # Monday B: OS Lab(1-2), DBMS(3), OS(4), DS(5-6)
    # Monday A: DBMS(1), OS(2), OS Lab(3-4), Mathematics III(5), DS(6) (using Mr. Abhuday Tripathi)
    # Let's build Monday A:
    pass

# To make it absolutely robust, let's write a python checker and execute it.
print("Drafting in scratch/validate_conflict.py...")
