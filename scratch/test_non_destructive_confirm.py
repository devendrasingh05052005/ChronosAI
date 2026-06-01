import os
import sys
import django

sys.path.append(r"c:\Users\jmsin\Desktop\chronosai")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from scheduler_api.models import Employee, Schedule, UserProfile
from django.test import RequestFactory
from scheduler_api.views import TimetableConfirmView
import json

# Setup
print("--- STARTING NON-DESTRUCTIVE CONFIRMATION TESTS ---")
Schedule.objects.all().delete()

# Create dummy employee
emp, _ = Employee.objects.get_or_create(name="Ms. Meha Shrivastava", defaults={'department': 'CSE-AIDS'})

# Create a dummy 3rd Year class schedule
s3 = Schedule.objects.create(
    employee=emp,
    day_of_week="Monday",
    start_time="09:35",
    end_time="10:35",
    task_name="Internet of Things",
    academic_year="3rd Year",
    semester=6,
    section="A",
    room_number="Room 302",
    department="CSE-AIDS"
)
print("[OK] Created baseline 3rd Year class.")

# Prepare a request to confirm a 2nd Year timetable upload
rows = [
    {
        "day": "Monday",
        "start_time": "11:35",
        "end_time": "12:35",
        "subject": "DBMS",
        "faculty": "Mr. Sachin Malviya",
        "academic_year": "2nd Year",
        "semester": 4,
        "section": "B",
        "room_number": "Room 302"
    }
]

# Create Request
factory = RequestFactory()
request = factory.post(
    '/api/timetable/confirm/',
    data=json.dumps({'rows': rows}),
    content_type='application/json'
)

# Mock authenticated user
user, _ = User.objects.get_or_create(username='hod_test', email='hod_test@sistec.ac.in')
profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'HOD', 'department': 'CSE-AIDS'})
request.user = user

# Run View
view = TimetableConfirmView.as_view()
response = view(request)

print(f"Response Status Code: {response.status_code}")
res_data = json.loads(response.content)
print(f"Response Body: {res_data}")

# Assertions
count_2nd = Schedule.objects.filter(academic_year="2nd Year").count()
count_3rd = Schedule.objects.filter(academic_year="3rd Year").count()

print(f"2nd Year Schedules in database: {count_2nd}")
print(f"3rd Year Schedules in database: {count_3rd}")

if count_2nd == 1 and count_3rd == 1:
    print("[SUCCESS] Scoped non-destructive deletion works perfectly! 3rd Year schedule was preserved while 2nd Year was confirmed!")
else:
    print("[FAIL] Scoped deletion failed! Schedules were wiped or not created.")
    sys.exit(1)
