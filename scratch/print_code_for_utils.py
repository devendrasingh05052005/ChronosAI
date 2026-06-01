import os
import sys
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from scratch.resolved_schedules import S4A, S6B
import pprint

# Let's format them nicely
print("--- S4A Python Code ---")
pp = pprint.PrettyPrinter(indent=8, width=120)
s4a_str = pp.pformat(S4A)
print(s4a_str)

print("\n--- S6B Python Code ---")
s6b_str = pp.pformat(S6B)
print(s6b_str)
