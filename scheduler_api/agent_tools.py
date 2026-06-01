import logging
import traceback

from langchain_core.tools import tool

from scheduler_api.scheduling_utils import (
    check_teacher_double_booking,
    normalize_time_to_hhmm,
    point_in_slot,
    resolve_schedule_slot,
)

logger = logging.getLogger('chronosai.agent_tools')


@tool
def get_faculty_schedule_tool(teacher_name: str, day: str) -> str:
    """
    Fetches the complete schedule for a specific faculty member on a given day.

    Use this tool when the user asks about what a specific teacher is teaching on a day,
    or wants to see all lectures of a particular faculty member. For example:
    "What does Dr. Sharma teach on Monday?" or "Show me Prof. Kumar's Thursday schedule."

    Args:
        teacher_name: The name (or partial name) of the faculty member. Case-insensitive.
        day: The day of the week (e.g., "Monday", "Tuesday"). Case-insensitive.

    Returns:
        A formatted string listing all schedule entries for the given faculty on that day,
        or an informative message if no entries are found.
    """
    try:
        from scheduler_api.models import Schedule

        entries = Schedule.objects.filter(
            employee__name__icontains=teacher_name,
            day_of_week__icontains=day
        ).select_related('employee').order_by('academic_year', 'start_time')

        if not entries.exists():
            return (
                f"No schedule found for faculty matching '{teacher_name}' on '{day}'. "
                f"Please check the name spelling or try a different day."
            )

        lines = [f"Schedule for '{teacher_name}' on {day.capitalize()}:"]
        for entry in entries:
            proxy_note = ""
            if entry.is_proxy:
                proxy_note = f" [PROXY covering for: {entry.proxy_teacher_name}]"
            lines.append(
                f"  • {entry.start_time} – {entry.end_time} | {entry.task_name} | "
                f"[{entry.academic_year} Sec {entry.section}] ({entry.room_number}) | "
                f"Faculty: {entry.employee.name}{proxy_note}"
            )

        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        return f"Error fetching faculty schedule: {str(e)}"


@tool
def find_free_faculties_tool(day: str, time: str) -> str:
    """
    Finds all faculty members who are FREE (not scheduled) at a specific day and time slot.

    Use this tool when the user wants to assign a proxy teacher and needs to know who is
    available. For example: "Who is free on Monday at 10:00?" or "Which teachers are
    available Thursday at 2 PM to cover a class?"

    Args:
        day: The day of the week (e.g., "Monday", "Thursday"). Case-insensitive.
        time: The time slot to check (e.g., "10:00", "14:00", "09:30"). Should be in HH:MM format.

    Returns:
        A formatted string listing all faculty who have no scheduled class at that day/time,
        or a message if all faculty are busy.
    """
    try:
        from scheduler_api.models import Employee, Schedule

        normalized_time = normalize_time_to_hhmm(time)
        busy_employee_ids = set()
        busy_names = set()

        for entry in Schedule.objects.filter(day_of_week__icontains=day).select_related('employee'):
            if point_in_slot(normalized_time, entry.start_time, entry.end_time):
                busy_employee_ids.add(entry.employee_id)
                if entry.is_proxy and entry.proxy_teacher_name:
                    busy_names.add(entry.proxy_teacher_name.strip().lower())

        free_employees = Employee.objects.exclude(id__in=busy_employee_ids).order_by('name')
        free_employees = [
            emp for emp in free_employees
            if emp.name.strip().lower() not in busy_names
        ]

        if not free_employees:
            return (
                f"All faculty members appear to be busy on {day.capitalize()} at {time}. "
                f"Consider checking adjacent time slots."
            )

        lines = [f"Free faculty on {day.capitalize()} at {time}:"]
        for emp in free_employees:
            lines.append(f"  ✓ {emp.name}")

        lines.append(f"\nTotal: {len(free_employees)} faculty member(s) available.")
        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        return f"Error finding free faculties: {str(e)}"


@tool
def find_busy_faculties_tool(day: str, time: str) -> str:
    """
    Finds all faculty members who are BUSY (scheduled/teaching) at a specific day and time slot.

    Use this tool when the user wants to know who is teaching or busy in a particular slot.
    For example: "Who is busy on Thursday at 11:35?" or "Which faculties are busy at 10:00 on Monday?"

    Args:
        day: The day of the week (e.g., "Monday", "Thursday"). Case-insensitive.
        time: The time slot to check (e.g., "11:35", "10:30"). Should be in HH:MM format.

    Returns:
        A formatted string listing all busy faculty members and their active teaching slots/subjects,
        or a message indicating that no faculty members are busy.
    """
    try:
        from scheduler_api.models import Schedule, Employee

        normalized_time = normalize_time_to_hhmm(time)
        day_norm = day.strip().capitalize()

        busy_records = []

        for entry in Schedule.objects.filter(day_of_week__icontains=day_norm).select_related('employee'):
            if point_in_slot(normalized_time, entry.start_time, entry.end_time):
                # If this entry is covered by a proxy, the proxy teacher is busy.
                if entry.is_proxy and entry.proxy_teacher_name:
                    teacher_name = entry.proxy_teacher_name.strip()
                    subject = f"{entry.task_name} (Proxy for {entry.employee.name})"
                else:
                    teacher_name = entry.employee.name
                    subject = entry.task_name

                busy_records.append({
                    'teacher': teacher_name,
                    'subject': subject,
                    'slot': f"{entry.start_time} – {entry.end_time}",
                    'batch': f"{entry.academic_year} Sec {entry.section}",
                    'room': entry.room_number or "N/A"
                })

        if not busy_records:
            return f"No faculty members are busy on {day_norm} at {time}."

        busy_records.sort(key=lambda x: x['teacher'])

        lines = [f"Busy faculty on {day_norm} at {time}:"]
        for rec in busy_records:
            lines.append(
                f"  • {rec['teacher']} | {rec['subject']} | {rec['slot']} | {rec['batch']} ({rec['room']})"
            )

        lines.append(f"\nTotal: {len(busy_records)} faculty member(s) busy.")
        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        return f"Error finding busy faculties: {str(e)}"


@tool
def assign_proxy_tool(day: str, time: str, absent_teacher: str, proxy_teacher: str) -> str:
    """
    Assigns a proxy teacher to cover a class slot when the original teacher is absent.

    This tool updates the database to mark the schedule entry as a proxy assignment.
    It includes a multi-booking prevention check to ensure the proxy teacher is not
    already scheduled at the same time. Use when: "Assign Dr. Gupta as proxy for
    Dr. Sharma on Monday at 10:00" or "Dr. Kumar is absent Thursday 9 AM, who can cover?"

    Args:
        day: The day of the week (e.g., "Monday"). Case-insensitive.
        time: The time slot in HH:MM format (e.g., "10:00", "09:00").
        absent_teacher: The name of the absent faculty member. Case-insensitive partial match.
        proxy_teacher: The name of the faculty who will cover the class. Case-insensitive partial match.

    Returns:
        A confirmation string with full proxy assignment details, or an error message
        explaining why the assignment could not be completed.
    """
    try:
        from scheduler_api.models import Employee
        from scheduler_api.tasks import send_proxy_alert_email

        normalized_time = normalize_time_to_hhmm(time)
        schedule_entry = resolve_schedule_slot(day, normalized_time, absent_teacher)

        if not schedule_entry:
            return (
                f"No schedule entry found for '{absent_teacher}' on {day.capitalize()} at {time}. "
                f"Please verify the teacher name and time slot."
            )

        proxy_employee = Employee.objects.filter(
            name__icontains=proxy_teacher
        ).first()

        if not proxy_employee:
            return (
                f"Proxy teacher '{proxy_teacher}' not found in the system. "
                f"Please ensure they are registered in the employee database."
            )

        has_conflict, conflict_message = check_teacher_double_booking(
            day=day,
            slot_start=schedule_entry.start_time,
            slot_end=schedule_entry.end_time,
            teacher_name=proxy_employee.name,
            exclude_schedule_id=schedule_entry.pk,
        )

        if has_conflict:
            return conflict_message

        # Apply proxy assignment
        original_teacher_name = schedule_entry.employee.name
        original_subject = schedule_entry.task_name

        schedule_entry.is_proxy = True
        schedule_entry.proxy_teacher_name = proxy_employee.name
        schedule_entry.save()

        slot_description = (
            f"{day.capitalize()} {schedule_entry.start_time}–{schedule_entry.end_time}"
        )
        logger.info(
            'Proxy assigned: %s covers %s on %s',
            proxy_employee.name,
            original_teacher_name,
            slot_description,
        )

        try:
            send_proxy_alert_email.delay(
                teacher_name=proxy_employee.name,
                slot=slot_description,
                subject=original_subject,
            )
        except Exception as celery_err:
            logger.warning('Could not dispatch Celery proxy alert: %s', celery_err)

        return (
            f"✅ PROXY ASSIGNED SUCCESSFULLY\n"
            f"  Subject: {original_subject}\n"
            f"  Absent Teacher: {original_teacher_name}\n"
            f"  Proxy Teacher: {proxy_employee.name}\n"
            f"  Slot: {slot_description}\n"
            f"  📧 Alert notification dispatched to background queue."
        )

    except Exception as e:
        traceback.print_exc()
        return f"Error assigning proxy: {str(e)}"


@tool
def get_day_schedule_tool(day: str, academic_year: str = None) -> str:
    """
    Retrieves the complete timetable matrix for an entire day, showing all faculty
    and their respective class slots. Optionally filters by academic year (e.g., '2nd Year', '3rd Year', '4th Year').

    Use this when the user asks for a full day overview or a specific year's overview. For example:
    "Show me the entire Monday schedule", "What's happening on Friday for 3rd year?",
    "Give me all lectures for Thursday."

    Args:
        day: The day of the week (e.g., "Monday", "Friday", "Thursday"). Case-insensitive.
        academic_year: Optional academic year filter (e.g., '2nd Year', '3rd Year', '4th Year'). Case-insensitive.

    Returns:
        A formatted timetable string showing all schedule entries for the day,
        organized by time slot, or a message if no entries exist for that day.
    """
    try:
        from scheduler_api.models import Schedule

        filters = {'day_of_week__icontains': day}
        if academic_year:
            # Clean / match standard academic year values
            year_norm = academic_year.strip().lower()
            if any(kw in year_norm for kw in [
                '2nd', 'second', '4th sem', '4 sem', 'fourth sem', '4th semester', 'sem 4', 'semester 4',
                '3rd sem', '3 sem', 'third sem', 'third semester', 'sem 3', 'semester 3'
            ]):
                filters['academic_year'] = '2nd Year'
            elif any(kw in year_norm for kw in [
                '3rd', 'third', '6th sem', '6 sem', 'sixth sem', '6th semester', 'sem 6', 'semester 6',
                '5th sem', '5 sem', 'fifth sem', 'fifth semester', 'sem 5', 'semester 5'
            ]):
                filters['academic_year'] = '3rd Year'
            elif any(kw in year_norm for kw in [
                '4th', 'fourth', '8th sem', '8 sem', 'eighth sem', '8th semester', 'sem 8', 'semester 8',
                '7th sem', '7 sem', 'seventh sem', 'seventh semester', 'sem 7', 'semester 7'
            ]):
                filters['academic_year'] = '4th Year'
            else:
                filters['academic_year'] = academic_year

        entries = Schedule.objects.filter(**filters).select_related('employee').order_by('start_time', 'employee__name')

        title_str = f"📅 Complete Schedule for {day.capitalize()}"
        if academic_year:
            title_str += f" ({filters['academic_year']})"

        if not entries.exists():
            return (
                f"No schedule entries found for {day.capitalize()}" + 
                (f" ({filters['academic_year']})" if academic_year else "") + ". "
                f"The timetable may not have been uploaded yet."
            )

        lines = [title_str, "=" * 55]

        current_time = None
        for entry in entries:
            if entry.start_time != current_time:
                current_time = entry.start_time
                lines.append(f"\n⏰ {entry.start_time} – {entry.end_time}")

            proxy_badge = " 🔄[PROXY]" if entry.is_proxy else ""
            proxy_name = f" → covered by {entry.proxy_teacher_name}" if entry.is_proxy else ""
            batch_info = f" [{entry.academic_year} Sec {entry.section}]"
            lines.append(
                f"    • {entry.task_name} | {entry.employee.name}{batch_info}{proxy_badge}{proxy_name}"
            )

        lines.append(f"\n{'=' * 55}")
        lines.append(f"Total entries: {entries.count()}")
        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        return f"Error fetching day schedule: {str(e)}"


@tool
def swap_faculty_lectures_tool(
    requesting_teacher: str,
    target_teacher: str,
    day_of_week: str,
    requestor_slot: str,
    target_slot: str,
) -> str:
    """
    Mutually swaps scheduled lecture slots between two faculty members on a given day.
    
    Use this tool when a professor requests to swap their lecture slot with another faculty's slot
    on the same day. For example: "I am Ms. Ruchi Jain. Can you swap my Thursday 11:35 lecture with
    Mr. Dheeraj Namdev's 14:10 class?" or "Swap Prof. A's 9:35 class on Monday with Prof. B's 11:35 class."
    
    Args:
        requesting_teacher: The name (or partial name) of the initiating teacher. Case-insensitive.
        target_teacher: The name (or partial name) of the second teacher to swap with. Case-insensitive.
        day_of_week: The day of the week (e.g., "Monday", "Thursday"). Case-insensitive.
        requestor_slot: The start time of the requesting teacher's slot (e.g., "11:35", "09:35").
        target_slot: The start time of the target teacher's slot (e.g., "14:10", "15:10").
        
    Returns:
        A markdown-formatted string summarizing the success parameter, the newly swapped slots,
        and Celery alert dispatch status, or a fail-safe verification abort message detailing conflicts.
    """
    try:
        from django.db import transaction
        from scheduler_api.models import Schedule
        from scheduler_api.tasks import send_swap_confirmation_email

        req_time = normalize_time_to_hhmm(requestor_slot)
        tgt_time = normalize_time_to_hhmm(target_slot)
        day_norm = day_of_week.strip().capitalize()

        # 1. Resolve and validate both schedule slots exist in the database
        req_schedule = Schedule.objects.filter(
            day_of_week__icontains=day_norm,
            start_time=req_time,
            employee__name__icontains=requesting_teacher
        ).select_related('employee').first()

        if not req_schedule:
            return (
                f"❌ **SWAP ABORTED**\n\n"
                f"Could not locate a scheduled class for **{requesting_teacher}** starting at "
                f"**{requestor_slot}** on **{day_norm}**."
            )

        tgt_schedule = Schedule.objects.filter(
            day_of_week__icontains=day_norm,
            start_time=tgt_time,
            employee__name__icontains=target_teacher
        ).select_related('employee').first()

        if not tgt_schedule:
            return (
                f"❌ **SWAP ABORTED**\n\n"
                f"Could not locate a scheduled class for **{target_teacher}** starting at "
                f"**{target_slot}** on **{day_norm}**."
            )

        req_teacher_full = req_schedule.employee.name
        tgt_teacher_full = tgt_schedule.employee.name

        # 2. Two-way Fail-Safe Verification Checks
        # A: Check if target_teacher has conflicts during req_schedule's slot (excluding tgt_schedule)
        has_conflict_tgt, conflict_msg_tgt = check_teacher_double_booking(
            day=day_norm,
            slot_start=req_schedule.start_time,
            slot_end=req_schedule.end_time,
            teacher_name=tgt_teacher_full,
            exclude_schedule_id=tgt_schedule.pk
        )
        if has_conflict_tgt:
            return (
                f"❌ **SWAP VERIFICATION FAILED — ABORTING TRANSACTION**\n\n"
                f"Target teacher **{tgt_teacher_full}** has a scheduling conflict during the requestor slot "
                f"({req_schedule.start_time} - {req_schedule.end_time}):\n"
                f"> {conflict_msg_tgt}"
            )

        # B: Check if requesting_teacher has conflicts during tgt_schedule's slot (excluding req_schedule)
        has_conflict_req, conflict_msg_req = check_teacher_double_booking(
            day=day_norm,
            slot_start=tgt_schedule.start_time,
            slot_end=tgt_schedule.end_time,
            teacher_name=req_teacher_full,
            exclude_schedule_id=req_schedule.pk
        )
        if has_conflict_req:
            return (
                f"❌ **SWAP VERIFICATION FAILED — ABORTING TRANSACTION**\n\n"
                f"Requesting teacher **{req_teacher_full}** has a scheduling conflict during the target slot "
                f"({tgt_schedule.start_time} - {tgt_schedule.end_time}):\n"
                f"> {conflict_msg_req}"
            )

        # 3. Execute Atomic Database Swap Transaction
        with transaction.atomic():
            req_start_orig = req_schedule.start_time
            req_end_orig = req_schedule.end_time
            req_room_orig = req_schedule.room_number

            tgt_start_orig = tgt_schedule.start_time
            tgt_end_orig = tgt_schedule.end_time
            tgt_room_orig = tgt_schedule.room_number

            # Resolve all joint entries sharing these slots
            req_joint = Schedule.objects.filter(
                day_of_week=req_schedule.day_of_week,
                start_time=req_start_orig,
                end_time=req_end_orig,
                academic_year=req_schedule.academic_year,
                section=req_schedule.section,
                task_name=req_schedule.task_name,
                department=req_schedule.department
            )
            tgt_joint = Schedule.objects.filter(
                day_of_week=tgt_schedule.day_of_week,
                start_time=tgt_start_orig,
                end_time=tgt_end_orig,
                academic_year=tgt_schedule.academic_year,
                section=tgt_schedule.section,
                task_name=tgt_schedule.task_name,
                department=tgt_schedule.department
            )

            # Swap timeslots and rooms
            req_joint.update(start_time=tgt_start_orig, end_time=tgt_end_orig, room_number=tgt_room_orig)
            tgt_joint.update(start_time=req_start_orig, end_time=req_end_orig, room_number=req_room_orig)

            # Clean proxy assignments if any existed on these slots to restore them to standard status
            req_joint.update(is_proxy=False, proxy_teacher_name="")
            tgt_joint.update(is_proxy=False, proxy_teacher_name="")

        # 4. Trigger Background SMTP Dispatch Log simulation via Celery Beat pipeline
        slot_desc_a = f"{day_norm} {req_start_orig}–{req_end_orig}"
        slot_desc_b = f"{day_norm} {tgt_start_orig}–{tgt_end_orig}"

        try:
            send_swap_confirmation_email.delay(
                teacher_a=req_teacher_full,
                teacher_b=tgt_teacher_full,
                slot_a=slot_desc_a,
                slot_b=slot_desc_b,
                subject_a=req_schedule.task_name,
                subject_b=tgt_schedule.task_name
            )
            celery_status = "✨ Dispatched Dual confirmation receipts to background queue."
        except Exception as celery_err:
            logger.warning("Celery beat confirmation dispatch failed: %s", celery_err)
            celery_status = "⚠️ Celery confirmation queue unavailable. Database transaction remains successfully persistent."

        return (
            f"🎯 **LECTURE SLOT SWAP TRANSACTION COMPLETED SUCCESSFULLY**\n\n"
            f"| Parameter | Requestor Subject | Target Subject |\n"
            f"|---|---|---|\n"
            f"| **Day** | {day_norm} | {day_norm} |\n"
            f"| **Batch/Section** | **[{req_schedule.academic_year} Sec {req_schedule.section}]** | **[{tgt_schedule.academic_year} Sec {tgt_schedule.section}]** |\n"
            f"| **Faculty Member(s)** | {req_teacher_full} | {tgt_teacher_full} |\n"
            f"| **Subject Name** | {req_schedule.task_name} | {tgt_schedule.task_name} |\n"
            f"| **Original Slot** | {req_start_orig} – {req_end_orig} ({req_room_orig}) | {tgt_start_orig} – {tgt_end_orig} ({tgt_room_orig}) |\n"
            f"| **New Swapped Slot** | **{tgt_start_orig} – {tgt_end_orig} ({tgt_room_orig})** | **{req_start_orig} – {req_end_orig} ({req_room_orig})** |\n\n"
            f"📧 **Celery Dispatch Status:** {celery_status}"
        )

    except Exception as e:
        traceback.print_exc()
        return f"Error executing mutual faculty lecture swap: {str(e)}"


@tool
def recommend_proxy_teachers_tool(day: str, time: str, absent_teacher: str) -> str:
    """
    Finds and ranks all available faculty members who can cover an absent teacher's lecture.
    
    This tool recommends proxy teachers based on:
    1. Subject Alignment (+15 points): Boosts free teachers who teach the same or similar subject on other days.
    2. Workload Balance (+3 points per free slot): Prioritizes free teachers who have a lower total teaching load today.
    
    Use this tool when a user asks for a proxy suggestion, e.g.: "Who do you recommend to cover for Ms. Meha's 11:35 lecture on Tuesday?"
    
    Args:
        day: The day of the week (e.g., "Monday", "Tuesday"). Case-insensitive.
        time: The start time of the slot to cover (e.g., "11:35", "10:35").
        absent_teacher: The name (or partial name) of the absent teacher. Case-insensitive.
        
    Returns:
        A markdown-formatted ranked table of recommended proxy teachers, their workload,
        subject alignment details, and recommendation reasons.
    """
    try:
        import re
        from scheduler_api.models import Employee, Schedule
        from django.db.models import Q

        normalized_time = normalize_time_to_hhmm(time)
        day_norm = day.strip().capitalize()

        # 1. Locate the absent teacher's lecture to get the subject
        absent_lecture = resolve_schedule_slot(day_norm, normalized_time, absent_teacher)
        if not absent_lecture:
            return (
                f"❌ **RECOMMENDATION ABORTED**\n\n"
                f"Could not locate a scheduled class for absent teacher **{absent_teacher}** "
                f"starting at **{time}** on **{day_norm}**."
            )

        target_subject = absent_lecture.task_name
        absent_teacher_full = absent_lecture.employee.name

        # 2. Find all free teachers at this slot (regular or proxy)
        busy_employee_ids = set()
        busy_names = set()

        for entry in Schedule.objects.filter(day_of_week__icontains=day_norm).select_related('employee'):
            if point_in_slot(normalized_time, entry.start_time, entry.end_time):
                busy_employee_ids.add(entry.employee_id)
                if entry.is_proxy and entry.proxy_teacher_name:
                    busy_names.add(entry.proxy_teacher_name.strip().lower())

        free_employees = Employee.objects.exclude(
            Q(id__in=busy_employee_ids) | Q(name__icontains=absent_teacher_full)
        ).order_by('name')
        
        free_employees = [
            emp for emp in free_employees
            if emp.name.strip().lower() not in busy_names
        ]

        if not free_employees:
            return (
                f"❌ **RECOMMENDATION WARNING**\n\n"
                f"All registered faculty members are busy on **{day_norm}** at **{time}**. "
                f"No available proxy candidates found."
            )

        # 3. Calculate scores and rank each free employee
        scored_recommendations = []
        subject_keywords = [w.lower() for w in re.split(r'[\s&/_\-]+', target_subject) if len(w) > 2]

        for emp in free_employees:
            score = 0
            reasons = []

            # A. Workload Count (classes taught on this day)
            regular_classes_count = Schedule.objects.filter(
                day_of_week__icontains=day_norm,
                employee=emp
            ).count()
            
            proxy_classes_count = Schedule.objects.filter(
                day_of_week__icontains=day_norm,
                is_proxy=True,
                proxy_teacher_name__icontains=emp.name
            ).count()
            
            total_load = regular_classes_count + proxy_classes_count
            load_score = max(0, (6 - total_load) * 3)
            score += load_score
            reasons.append(f"Workload: {total_load} classes today (+{load_score} pts)")

            # B. Subject Similarity
            emp_subjects = Schedule.objects.filter(
                employee=emp
            ).values_list('task_name', flat=True).distinct()

            match_found = False
            for subj in emp_subjects:
                subj_lower = subj.lower()
                if any(kw in subj_lower for kw in subject_keywords):
                    match_found = True
                    break

            if match_found:
                score += 15
                reasons.append(f"Subject Alignment: Teaches related courses (+15 pts)")
            else:
                reasons.append("General Coverage")

            scored_recommendations.append({
                'employee': emp,
                'name': emp.name,
                'total_load': total_load,
                'score': score,
                'reason_text': ", ".join(reasons)
            })

        # Sort by score descending, then by name
        scored_recommendations.sort(key=lambda x: (-x['score'], x['name']))

        # 4. Generate beautiful Markdown Table response
        lines = [
            f"🤖 **ChronosAI Intelligent Proxy Matchmaker**",
            f"Recommending proxy coverage for **{absent_teacher_full}** teaching **{target_subject}**",
            f"Batch: **[{absent_lecture.academic_year} Sec {absent_lecture.section}]** | Room: **{absent_lecture.room_number}**",
            f"Slot: **{day_norm} {absent_lecture.start_time} – {absent_lecture.end_time}**",
            f"\n| Rank | Faculty Member | Today's Load | Match Score | Recommendation Rationale |",
            f"|---|---|---|---|---|"
        ]

        for rank, rec in enumerate(scored_recommendations, 1):
            star = "⭐ " if rank == 1 else ""
            lines.append(
                f"| {rank} | {star}**{rec['name']}** | {rec['total_load']} lecture(s) | **{rec['score']}** | {rec['reason_text']} |"
            )

        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        return f"Error computing intelligent proxy recommendations: {str(e)}"


@tool
def search_subject_schedule_tool(subject_name: str, day: str = None) -> str:
    """
    Searches the timetable for a specific subject/course name (e.g. "Deep Learning", "IoT") on a given day or across the whole week.

    Use this tool when the user asks about when a specific subject's class is scheduled,
    or wants to find what time a course lecture is held. For example:
    "When is the Deep Learning class scheduled?" or "Deep learning ka lecture kitni baje hai Thursday ko?"

    Args:
        subject_name: The name (or partial name) of the subject/course. Case-insensitive.
        day: Optional. The day of the week (e.g., "Monday", "Thursday"). Case-insensitive.

    Returns:
        A formatted string listing all matching schedule slots for the subject/course,
        including start/end times, faculty teaching it, and room number/section.
    """
    try:
        from scheduler_api.models import Schedule

        query_filter = {
            'task_name__icontains': subject_name
        }
        if day:
            query_filter['day_of_week__icontains'] = day.strip()

        entries = Schedule.objects.filter(**query_filter).select_related('employee').order_by('day_of_week', 'start_time')

        if not entries.exists():
            day_msg = f" on '{day}'" if day else ""
            return (
                f"No scheduled lectures found for subject '{subject_name}'{day_msg}. "
                f"Please verify the subject name or try searching across the whole week."
            )

        lines = [f"Found {entries.count()} scheduled slot(s) for '{subject_name}':"]
        for entry in entries:
            proxy_note = ""
            if entry.is_proxy:
                proxy_note = f" (covered by proxy: {entry.proxy_teacher_name})"
            lines.append(
                f"  • {entry.day_of_week} | {entry.start_time} – {entry.end_time} | "
                f"[{entry.academic_year} Sec {entry.section}] ({entry.room_number}) | "
                f"Faculty: {entry.employee.name}{proxy_note}"
            )

        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        return f"Error searching subject schedule: {str(e)}"
