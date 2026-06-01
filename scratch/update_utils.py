import os
import sys

# Ensure workspace root is in sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scratch.resolved_schedules import S4A, S6B
from scheduler_api.utils import _get_local_4th_sem_schedule, _get_local_6th_sem_schedule, _get_local_8th_sem_schedule
import pprint

def main():
    utils_path = "scheduler_api/utils.py"
    with open(utils_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Let's locate _build_smart_local_schedule in content
    # It starts at: def _build_smart_local_schedule
    # We want to replace everything from def _build_smart_local_schedule to the end of the file!
    idx = content.find("def _build_smart_local_schedule")
    if idx == -1:
        print("Error: Could not find _build_smart_local_schedule in utils.py")
        return

    # Keep everything before _build_smart_local_schedule
    header = content[:idx]

    # Generate our new code
    new_code_parts = []
    
    new_code_parts.append("""def _build_smart_local_schedule(raw_text: str) -> dict:
    raw_lower = raw_text.lower()
    
    # Detect 4th Semester Section A vs B
    if any(kw in raw_lower for kw in ["4_a", "4th a"]):
        print("[ChronosAI] Local Fallback matched: 4th Semester (CSE-AIDS-4_A)")
        return _get_local_4th_sem_a_schedule()
    if any(kw in raw_lower for kw in ["4_b", "4th b"]):
        print("[ChronosAI] Local Fallback matched: 4th Semester (CSE-AIDS-4_B)")
        return _get_local_4th_sem_b_schedule()
        
    # Detect 6th Semester Section A vs B
    if any(kw in raw_lower for kw in ["6_b", "6th b"]):
        print("[ChronosAI] Local Fallback matched: 6th Semester (CSE-AIDS-6_B)")
        return _get_local_6th_sem_b_schedule()
    if any(kw in raw_lower for kw in ["6_a", "6th a"]):
        print("[ChronosAI] Local Fallback matched: 6th Semester (CSE-AIDS-6_A)")
        return _get_local_6th_sem_a_schedule()

    # Detect 8th Semester
    if any(kw in raw_lower for kw in ["8_a", "8_b", "8th", "major project", "information security"]):
        print("[ChronosAI] Local Fallback matched: 8th Semester (CSE-AIDS-8_A)")
        return _get_local_8th_sem_schedule()

    # Default fallback: return 3rd Year Sec A
    print("[ChronosAI] Local Fallback matched default: 6th Semester (CSE-AIDS-6_A)")
    return _get_local_6th_sem_a_schedule()
""")

    # 4th Sem A
    new_code_parts.append("\ndef _get_local_4th_sem_a_schedule() -> dict:\n    return {\"schedule\": " + pprint.pformat(S4A, indent=8) + "}\n")

    # 4th Sem B (original)
    original_4th_b = _get_local_4th_sem_schedule()["schedule"]
    new_code_parts.append("\ndef _get_local_4th_sem_b_schedule() -> dict:\n    return {\"schedule\": " + pprint.pformat(original_4th_b, indent=8) + "}\n")

    # 6th Sem A (original)
    original_6th_a = _get_local_6th_sem_schedule()["schedule"]
    new_code_parts.append("\ndef _get_local_6th_sem_a_schedule() -> dict:\n    return {\"schedule\": " + pprint.pformat(original_6th_a, indent=8) + "}\n")

    # 6th Sem B
    new_code_parts.append("\ndef _get_local_6th_sem_b_schedule() -> dict:\n    return {\"schedule\": " + pprint.pformat(S6B, indent=8) + "}\n")

    # 8th Sem (original)
    original_8th = _get_local_8th_sem_schedule()["schedule"]
    new_code_parts.append("\ndef _get_local_8th_sem_schedule() -> dict:\n    return {\"schedule\": " + pprint.pformat(original_8th, indent=8) + "}\n")

    full_new_code = "".join(new_code_parts)
    
    # Save back to utils.py
    with open(utils_path, "w", encoding="utf-8") as f:
        f.write(header + full_new_code)
    
    print("SUCCESS: Successfully wrote new conflict-free timetables to scheduler_api/utils.py!")

if __name__ == "__main__":
    main()
