import traceback
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition, ToolNode

from scheduler_api.agent_tools import (
    get_faculty_schedule_tool,
    find_free_faculties_tool,
    find_busy_faculties_tool,
    assign_proxy_tool,
    get_day_schedule_tool,
    swap_faculty_lectures_tool,
    recommend_proxy_teachers_tool,
    search_subject_schedule_tool,
)

# -------------------------------------------------------------
# PRESENTATION MODE CONFIGURATION
# True = Use 'qwen/qwen3-32b' as PRIMARY (Super fast response times!)
# False = Use 'llama-3.3-70b-versatile' as PRIMARY (Higher reasoning/precision!)
# -------------------------------------------------------------
USE_QWEN_AS_PRIMARY = True


CHRONOS_SYSTEM_PROMPT = """
You are ChronosAI, an intelligent college timetable management assistant.

YOUR CAPABILITIES:
1. get_faculty_schedule_tool – View a teacher schedule
2. find_free_faculties_tool – Find free faculties
3. find_busy_faculties_tool – Find busy/teaching faculties
4. assign_proxy_tool – Assign proxy teachers
5. get_day_schedule_tool – Show full day timetable
6. swap_faculty_lectures_tool – Mutually swap slots between two faculty members on a given day.
7. recommend_proxy_teachers_tool – Find and rank free teachers to cover an absent teacher based on workload and subject alignment.
8. search_subject_schedule_tool – Search schedules for a specific course/subject name on a day or across the week.

RULES:
- ALWAYS use tools for timetable data
- NEVER fabricate schedule information
- Be concise and professional
- If tool output is enough, directly answer user
- Do not repeatedly call the same tool
- ROLE-BASED AUTHORIZATION RULE (CRITICAL):
  Only the HOD (User Role is "HOD") has the authority/rights to mutually swap timetable slots (swap_faculty_lectures_tool) or assign a proxy teacher (assign_proxy_tool).
  If the User Role in the query context is NOT "HOD" (e.g. if it is "Faculty" or "Unauthenticated"), and the user requests a swap or a proxy assignment, you MUST politely reject their request.
  Explain clearly that only the HOD has the rights to perform swaps or assign proxies, and standard faculty members cannot execute these actions directly via chat.
  For swaps, tell them that standard faculty can propose a swap using the "AI-Powered Swap Portal" on their dashboard sidebar, which will automatically route to the HOD's approvals inbox.
- If the HOD (User Role is "HOD") requests a mutual timetable slot swap (e.g. "I am Ms. Ruchi Jain. Can you swap my Thursday 11:35 lecture with Mr. Dheeraj Namdev's 14:10 class?"), extract: requesting_teacher, target_teacher, day_of_week, requestor_slot, target_slot, and call swap_faculty_lectures_tool.
- If the HOD (User Role is "HOD") asks to swap lectures by subject/course names (e.g., "swap Communication Skills with Deep Learning on Thursday"), you MUST first call search_subject_schedule_tool to lookup both subjects on that day. Find their scheduled start times and the actual teacher names teaching them. Then, execute the swap by calling swap_faculty_lectures_tool using the correct teacher names and start times (e.g. "11:35", "14:10"). NEVER pass subject names as teacher names or descriptive strings like "first lecture" as slots to swap_faculty_lectures_tool.
- If the HOD (User Role is "HOD") asks to assign a proxy teacher (e.g. "Assign Mr. Badal Hate to cover Ms. Meha Shrivastava's 09:35 lecture on Thursday"), extract: day, time, absent_teacher, proxy_teacher, and call assign_proxy_tool.
- If a user asks for a proxy teacher recommendation (e.g. "Who do you recommend to cover for Ms. Meha's 11:35 lecture on Tuesday?"), extract: day, time, absent_teacher, and call recommend_proxy_teachers_tool. (This tool is available to all users regardless of role).
- If a user asks about when a specific subject's class is scheduled (e.g., "When is Deep Learning?" or "Deep learning kab hai Thursday ko?"), extract: subject_name, day, and call search_subject_schedule_tool. (This tool is available to all users regardless of role).
- If a user asks who is busy, occupied, or teaching at a certain time/day (e.g., "which faculties are busy at 11:35 on Thursday" or "who is teaching on Monday at 10:00?"), extract: day, time, and call find_busy_faculties_tool. (This tool is available to all users regardless of role).
"""


# =========================
# STATE
# =========================

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# =========================
# TOOLS
# =========================

TOOLS = [
    get_faculty_schedule_tool,
    find_free_faculties_tool,
    find_busy_faculties_tool,
    assign_proxy_tool,
    get_day_schedule_tool,
    swap_faculty_lectures_tool,
    recommend_proxy_teachers_tool,
    search_subject_schedule_tool,
]


# =========================
# BUILD GRAPH
# =========================

def build_graph():

    # =========================
    # AGENT NODE
    # =========================

    def call_model_node(state: AgentState):
        from langchain_groq import ChatGroq
        from scheduler_api.utils import get_groq_api_keys

        messages = list(state["messages"])

        # Add system prompt once
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=CHRONOS_SYSTEM_PROMPT)] + messages

        # --- TOKEN OPTIMIZATION 1: Compress Old Tool Messages ---
        optimized_messages = []
        for i, msg in enumerate(messages):
            # If it's a ToolMessage and NOT one of the very last 2 messages (which represent the active turn)
            if isinstance(msg, ToolMessage) and i < len(messages) - 2:
                # Strip out the massive schedule table/details to save 95% of tokens
                msg_copy = ToolMessage(
                    content="[Timetable query results successfully retrieved and answered in the next message.]",
                    tool_call_id=msg.tool_call_id,
                    name=getattr(msg, 'name', None),
                    status=getattr(msg, 'status', 'success')
                )
                optimized_messages.append(msg_copy)
            else:
                optimized_messages.append(msg)
        messages = optimized_messages

        # --- TOKEN OPTIMIZATION 2: History Pruning (Keep System prompt + last 6 messages) ---
        system_msg = None
        other_msgs = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_msg = msg
            else:
                other_msgs.append(msg)

        if len(other_msgs) > 6:
            print(f"[ChronosAI] Pruning chatbot history from {len(other_msgs)} down to last 6 messages to stay within Groq limits.")
            other_msgs = other_msgs[-6:]

        messages = ([system_msg] if system_msg else []) + other_msgs

        try:

            last_message = messages[-1]

            # Detect if a swap or proxy action has already been successfully executed
            has_executed_action = False
            for msg in messages:
                if isinstance(msg, ToolMessage):
                    name = getattr(msg, 'name', '')
                    if name in ['swap_faculty_lectures_tool', 'assign_proxy_tool']:
                        has_executed_action = True
                        break

            # CRITICAL FIX
            # If tool already responded,
            # force final answer
            if isinstance(last_message, ToolMessage):

                messages.append(
                    SystemMessage(
                        content=(
                            "You have already received the tool result. "
                            "DO NOT call any more tools. "
                            "Answer the user directly using the tool output."
                        )
                    )
                )

            keys = get_groq_api_keys()
            response = None
            last_err = None

            # Establish dynamic model priority hierarchy based on user presentation preference flag
            if USE_QWEN_AS_PRIMARY:
                models_to_try = [
                    ("qwen/qwen3-32b", "Qwen Primary"),
                    ("llama-3.3-70b-versatile", "Llama-70B Secondary Fallback"),
                    ("llama-3.1-8b-instant", "Llama-8B Tertiary Fallback")
                ]
            else:
                models_to_try = [
                    ("llama-3.3-70b-versatile", "Llama-70B Primary"),
                    ("qwen/qwen3-32b", "Qwen Secondary Fallback"),
                    ("llama-3.1-8b-instant", "Llama-8B Tertiary Fallback")
                ]

            for model_name, label in models_to_try:
                if response is not None:
                    break
                    
                print(f"[ChronosAI] Attempting execution with model: {model_name} ({label})...")
                for idx, key in enumerate(keys):
                    try:
                        llm = ChatGroq(
                            model=model_name,
                            api_key=key,
                            temperature=0.1,
                            max_tokens=2048,
                            timeout=15,
                        )
                        if has_executed_action:
                            llm_with_tools = llm
                        else:
                            llm_with_tools = llm.bind_tools(TOOLS)
                            
                        response = llm_with_tools.invoke(messages)
                        print(f"[ChronosAI] Chatbot execution succeeded using model {model_name} with key index {idx}.")
                        break
                    except Exception as err:
                        print(f"[ChronosAI] Chatbot failed using model {model_name} on key index {idx}: {err}")
                        last_err = err

            if response is None:
                print("[ChronosAI] Chatbot all models failed on all keys. Returning friendly rate limit status message.")
                return {
                    "messages": [
                        AIMessage(
                            content="⚠️ ChronosAI is currently experiencing exceptionally high traffic or API rate limits. Please try your request again in a few moments."
                        )
                    ]
                }

            return {
                "messages": [response]
            }

        except Exception as e:

            traceback.print_exc()

            return {
                "messages": [
                    AIMessage(
                        content=f"Error while processing request: {str(e)}"
                    )
                ]
            }

    # =========================
    # GRAPH
    # =========================

    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("agent", call_model_node)
    graph.add_node("tools", ToolNode(TOOLS))

    # Entry
    graph.set_entry_point("agent")

    # Conditional routing
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        }
    )

    # After tool → back to agent
    graph.add_edge("tools", "agent")

    # Compile
    compiled_graph = graph.compile()

    print("[ChronosAI] LangGraph compiled successfully.")

    return compiled_graph


# =========================
# SINGLETON GRAPH
# =========================

_compiled_graph = None


def get_compiled_graph():

    global _compiled_graph

    if _compiled_graph is None:

        try:
            _compiled_graph = build_graph()

        except Exception as e:

            print(f"[ChronosAI] Graph build failed: {e}")

            traceback.print_exc()

            _compiled_graph = None

    return _compiled_graph