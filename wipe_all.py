import os
import sys

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.contrib.auth.models import User
from scheduler_api.models import UserProfile, Schedule, TimetableFile, SyllabusLog, SwapRequest, Employee

def wipe_all_data():
    print("\n==========================================")
    print("      CHRONOSAI DATABASE SYSTEM CLEANUP   ")
    print("==========================================\n")
    
    # 1. Clear all user registrations
    user_count = User.objects.count()
    profile_count = UserProfile.objects.count()
    UserProfile.objects.all().delete()
    User.objects.all().delete()
    print(f"[*] Cleared {user_count} registered User Accounts & {profile_count} Profiles.")
    
    # 2. Clear all timetables and active schedules
    schedule_count = Schedule.objects.count()
    file_count = TimetableFile.objects.count()
    Schedule.objects.all().delete()
    TimetableFile.objects.all().delete()
    print(f"[*] Cleared {schedule_count} Active Class Schedules & {file_count} Uploaded timetables.")
    
    # 3. Clear syllabus logs and swap requests
    syllabus_count = SyllabusLog.objects.count()
    swap_count = SwapRequest.objects.count()
    SyllabusLog.objects.all().delete()
    SwapRequest.objects.all().delete()
    print(f"[*] Cleared {syllabus_count} Syllabus Progress logs & {swap_count} Faculty Swap Requests.")
    
    # 4. Clean and preserve only individual faculty profiles in Employee directory
    print("\n------------------------------------------")
    print(f"ACTIVE FACULTY DIRECTORY PRESERVED ({Employee.objects.count()} Teachers)")
    print("------------------------------------------")
    for emp in Employee.objects.all().order_by('name'):
        print(f" - {emp.name:<35} | Department: {emp.department}")
        
    print("\n==========================================")
    print(" DATABASE 100% PREPARED FOR LIVE DEMO!")
    print("==========================================\n")

if __name__ == "__main__":
    wipe_all_data()
