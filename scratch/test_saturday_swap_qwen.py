import os
import sys
import django

# Add the workspace root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from scheduler_api.utils import get_groq_api_keys
from scheduler_api.agent_graph import build_graph, TOOLS
from scheduler_api.models import Schedule

print("=== Checking Saturday Lectures BEFORE Swap ===")
schedules_before = Schedule.objects.filter(day_of_week__icontains="Saturday").select_related('employee').order_by('academic_year', 'section', 'start_time')
for s in schedules_before:
    print(f"  {s.academic_year} Sec {s.section} | {s.start_time} - {s.end_time} | {s.task_name} | {s.employee.name} | Room: {s.room_number}")

# Build a temporary graph that uses qwen/qwen3-32b directly to test the agent tool orchestration
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition, ToolNode
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage
from scheduler_api.agent_graph import CHRONOS_SYSTEM_PROMPT

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def call_model_node(state: AgentState):
    messages = list(state["messages"])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=CHRONOS_SYSTEM_PROMPT)] + messages

    # compact or prune if needed, but not needed for single turn
    keys = get_groq_api_keys()
    key = keys[0]
    
    llm = ChatGroq(
        model="qwen/qwen3-32b",
        api_key=key,
        temperature=0.1,
        max_tokens=2048,
    )
    llm_with_tools = llm.bind_tools(TOOLS)
    
    # If tool already responded, add system message to answer directly
    if isinstance(messages[-1], ToolMessage):
        messages.append(
            SystemMessage(
                content="You have already received the tool result. DO NOT call any more tools. Answer the user directly using the tool output."
            )
        )
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

graph = StateGraph(AgentState)
graph.add_node("agent", call_model_node)
graph.add_node("tools", ToolNode(TOOLS))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")
compiled_graph = graph.compile()

print("\n=== Invoking Qwen-powered Graph with Saturday Swap Query ===")
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
