import os
import sys

# Ensure workspace root is in sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scheduler_api.models import Schedule
from django.db.models import Count

def main():
    print("=== Verification of Timetables Seeding ===")
    
    counts = Schedule.objects.values('academic_year', 'section').annotate(count=Count('id')).order_by('academic_year', 'section')
    
    total = 0
    for c in counts:
        print(f"  • {c['academic_year']} (Sec {c['section']}): {c['count']} active slots in DB")
        total += c['count']
        
    print(f"Total active schedule entries in DB: {total}")
    assert total > 0, "No schedules seeded!"
    print("Verification PASSED successfully!")

if __name__ == "__main__":
    main()
