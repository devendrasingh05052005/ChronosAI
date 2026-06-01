import os
import sys
import django

# Add the workspace root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from langchain_core.messages import HumanMessage
from scheduler_api.agent_graph import get_compiled_graph
from scheduler_api.models import Schedule

print("=== Checking Saturday Lectures BEFORE Swap ===")
schedules_before = Schedule.objects.filter(day_of_week__icontains="Saturday").select_related('employee').order_by('academic_year', 'section', 'start_time')
for s in schedules_before:
    print(f"  {s.academic_year} Sec {s.section} | {s.start_time} - {s.end_time} | {s.task_name} | {s.employee.name} | Room: {s.room_number}")

print("\n=== Invoking LangGraph Chatbot with Saturday Swap Query ===")
compiled_graph = get_compiled_graph()
query = "swap the both deep learning lectures with internet of things lectures of the saturday."
enriched_query = f"[Context: Today is Thursday, Current Time is 11:35, User Department is CSE-AIDS]\nQuery: {query}"

messages = [HumanMessage(content=enriched_query)]
result = compiled_graph.invoke(
    {"messages": messages},
    config={"recursion_limit": 10}
)

print("\n=== Chatbot Final Response ===")
final_response = "No response generated."
for msg in reversed(result.get("messages", [])):
    if hasattr(msg, 'content') and msg.content:
        if isinstance(msg.content, str) and msg.content.strip():
            final_response = msg.content
            break
print(final_response)

print("\n=== Checking Saturday Lectures AFTER Swap ===")
schedules_after = Schedule.objects.filter(day_of_week__icontains="Saturday").select_related('employee').order_by('academic_year', 'section', 'start_time')
for s in schedules_after:
    print(f"  {s.academic_year} Sec {s.section} | {s.start_time} - {s.end_time} | {s.task_name} | {s.employee.name} | Room: {s.room_number}")
