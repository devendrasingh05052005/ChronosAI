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

from scheduler_api.agent_tools import find_busy_faculties_tool

def main():
    print("=== Testing find_busy_faculties_tool ===")
    
    # 1. Thursday at 11:35
    print("\n--- Thursday at 11:35 ---")
    res1 = find_busy_faculties_tool.invoke({"day": "Thursday", "time": "11:35"})
    print(res1)
    
    # 2. Monday at 10:00 (or check what busy faculties exist on Thursday 09:35)
    print("\n--- Thursday at 09:35 ---")
    res2 = find_busy_faculties_tool.invoke({"day": "Thursday", "time": "09:35"})
    print(res2)

if __name__ == '__main__':
    main()
