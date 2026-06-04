import json
import logging
import os
import traceback

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction

from langchain_core.messages import HumanMessage

from scheduler_api.scheduling_utils import (
    check_teacher_double_booking,
    normalize_time_to_hhmm,
    point_in_slot,
    resolve_schedule_slot,
)

logger = logging.getLogger('chronosai.views')


# ─────────────────────────────────────────────────────────────
# KEYWORD MAPS
# ─────────────────────────────────────────────────────────────

DAY_KEYWORDS = {
    'monday': 'Monday',
    'tuesday': 'Tuesday',
    'wednesday': 'Wednesday',
    'thursday': 'Thursday',
    'friday': 'Friday',
    'saturday': 'Saturday',
    'sunday': 'Sunday',
    'mon': 'Monday',
    'tue': 'Tuesday',
    'wed': 'Wednesday',
    'thu': 'Thursday',
    'thur': 'Thursday',
    'fri': 'Friday',
    'sat': 'Saturday',
    'sun': 'Sunday',
}

BOT_DESCRIPTION_KEYWORDS = [
    'what can you do',
    'what do you do',
    'help me',
    'how can you help',
    'capabilities',
    'features',
    'who are you',
]

FREE_FACULTY_KEYWORDS = [
    'free',
    'available',
    'vacant',
]

PROXY_KEYWORDS = [
    'proxy',
    'assign',
    'cover',
    'substitute',
    'absent',
]


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _detect_day_in_query(query_lower: str):

    for keyword, day in DAY_KEYWORDS.items():
        if keyword in query_lower:
            return day

    return None


def _is_bot_description_query(query_lower: str):

    return any(
        kw in query_lower
        for kw in BOT_DESCRIPTION_KEYWORDS
    )


def _bot_description_response():

    return (
        "👋 I'm ChronosAI.\n\n"
        "I can:\n"
        "• View faculty schedules\n"
        "• Find free faculties\n"
        "• Assign proxy teachers\n"
        "• Show complete day schedules\n"
    )


def _detect_academic_year_in_query(query_lower: str):
    # 2nd Year: 3rd Semester (Odd) or 4th Semester (Even)
    if any(kw in query_lower for kw in [
        '2nd year', '2nd yr', 'second year', '2 year', 'sec year',
        '4th sem', '4 sem', 'fourth sem', '4th semester', 'sem 4', 'semester 4',
        '3rd sem', '3 sem', 'third sem', 'third semester', 'sem 3', 'semester 3'
    ]):
        return '2nd Year'
    # 3rd Year: 5th Semester (Odd) or 6th Semester (Even)
    if any(kw in query_lower for kw in [
        '3rd year', '3rd yr', 'third year', '3 year', 'third yr',
        '6th sem', '6 sem', 'sixth sem', '6th semester', 'sem 6', 'semester 6',
        '5th sem', '5 sem', 'fifth sem', 'fifth semester', 'sem 5', 'semester 5'
    ]):
        return '3rd Year'
    # 4th Year: 7th Semester (Odd) or 8th Semester (Even)
    if any(kw in query_lower for kw in [
        '4th year', '4th yr', 'fourth year', '4 year', 'fourth yr',
        '8th sem', '8 sem', 'eighth sem', '8th semester', 'sem 8', 'semester 8',
        '7th sem', '7 sem', 'seventh sem', 'seventh semester', 'sem 7', 'semester 7'
    ]):
        return '4th Year'
    return None


def _fast_day_schedule_response(day: str, academic_year: str = None, department: str = 'CSE-AIDS'):

    from scheduler_api.models import Schedule

    filters = {'day_of_week__icontains': day, 'department': department}
    if academic_year:
        filters['academic_year'] = academic_year

    entries = (
        Schedule.objects
        .filter(**filters)
        .select_related('employee')
        .order_by('start_time')
    )

    title = f"📅 Schedule for {day}"
    if academic_year:
        title += f" ({academic_year})"

    if not entries.exists():
        return f"No schedule found for {day}" + (f" ({academic_year})" if academic_year else "")

    lines = [title, "-" * 40]

    current_time = None

    # Merge entries for a premium chatbot response
    merged_entries = _group_and_merge_schedules(entries)

    for entry in merged_entries:

        if current_time != entry.start_time:
            current_time = entry.start_time

            lines.append(
                f"\n⏰ {entry.start_time} - {entry.end_time}"
            )

        proxy_note = ""

        if entry.is_proxy:
            proxy_note = f" 🔄 Proxy: {entry.proxy_teacher_name}"

        # Display year and section if multiple exist, or just section if year is filtered
        year_sec = f" [{entry.academic_year} Sec {entry.section}]" if not academic_year else f" [Sec {entry.section}]"
        lines.append(
            f"• {entry.task_name} — {entry.employee.name}{year_sec}{proxy_note}"
        )

    return "\n".join(lines)


class MergedEmployee:
    def __init__(self, name, department=None):
        self.name = name
        self.department = department


class MergedSchedule:
    def __init__(self, id, employee, day_of_week, start_time, end_time, task_name, is_proxy, proxy_teacher_name, academic_year, semester, section, room_number, department):
        self.id = id
        self.pk = id
        self.employee = employee
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
        self.task_name = task_name
        self.is_proxy = is_proxy
        self.proxy_teacher_name = proxy_teacher_name
        self.academic_year = academic_year
        self.semester = semester
        self.section = section
        self.room_number = room_number
        self.department = department


def _group_and_merge_schedules(queryset):
    """
    Groups schedule objects by day_of_week, start_time, end_time, academic_year,
    semester, section, task_name, and room_number, merging joint teacher names.
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for s in queryset:
        key = (
            s.day_of_week.strip().lower(),
            s.start_time.strip(),
            s.end_time.strip(),
            s.academic_year.strip().lower() if s.academic_year else '',
            s.semester or 0,
            s.section.strip().lower() if s.section else '',
            s.task_name.strip().lower(),
            s.room_number.strip().lower() if s.room_number else '',
        )
        groups[key].append(s)

    merged_list = []
    for key, group_entries in groups.items():
        primary = group_entries[0]

        # Merge primary employees cleanly
        seen_primary = []
        for s in group_entries:
            if s.employee and s.employee.name:
                name = s.employee.name.strip()
                if name not in seen_primary:
                    seen_primary.append(name)
        employee_name = " / ".join(seen_primary) if seen_primary else "No Teacher Assigned"

        # Merge proxy teachers if present
        seen_proxy = []
        is_proxy = False
        for s in group_entries:
            if s.is_proxy:
                is_proxy = True
                if s.proxy_teacher_name:
                    p_name = s.proxy_teacher_name.strip()
                    if p_name not in seen_proxy:
                        seen_proxy.append(p_name)
        proxy_teacher_name = " / ".join(seen_proxy) if seen_proxy else None

        merged_emp = MergedEmployee(name=employee_name, department=primary.department)
        merged_s = MergedSchedule(
            id=primary.id,
            employee=merged_emp,
            day_of_week=primary.day_of_week,
            start_time=primary.start_time,
            end_time=primary.end_time,
            task_name=primary.task_name,
            is_proxy=is_proxy,
            proxy_teacher_name=proxy_teacher_name,
            academic_year=primary.academic_year,
            semester=primary.semester,
            section=primary.section,
            room_number=primary.room_number,
            department=primary.department
        )
        merged_list.append(merged_s)

    # Sort merged list by start_time
    merged_list.sort(key=lambda x: x.start_time)
    return merged_list


def _normalize_time(time_str: str):
    return normalize_time_to_hhmm(time_str)


def _build_dashboard_context(request=None):
    """Production dashboard context: Schedule + Employee ORM → SPA template."""
    from django.conf import settings
    from django.utils import timezone
    from django.db import models
    from scheduler_api.models import Employee, Schedule, SwapRequest, SyllabusLog, UserProfile

    # _ensure_default_users() - Disabled for strict dynamic login

    try:
        now = timezone.localtime(timezone.now())
        current_day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][now.weekday()]
        current_time = now.strftime('%H:%M')

        celery_label = (
            'Celery Eager'
            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
            else 'Celery Distributed'
        )

        base_ctx = {
            'current_day': current_day,
            'current_time': current_time,
            'celery_mode_label': celery_label,
        }

        # Handle unauthenticated users
        if not request or not request.user.is_authenticated:
            base_ctx['is_unauthenticated'] = True
            from scheduler_api.models import Employee
            base_ctx['all_employees'] = Employee.objects.all().order_by('name')
            return base_ctx

        try:
            profile = request.user.profile
        except Exception:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)

        base_ctx['user'] = request.user
        base_ctx['profile'] = profile
        base_ctx['role'] = profile.role

        if profile.role == 'HOD':
            # ── HOD COMMAND CENTER ──
            dept = profile.department or 'CSE-AIDS'
            lectures_2nd = Schedule.objects.filter(day_of_week__iexact=current_day, academic_year='2nd Year', department=dept).select_related('employee').order_by('start_time')
            lectures_3rd = Schedule.objects.filter(day_of_week__iexact=current_day, academic_year='3rd Year', department=dept).select_related('employee').order_by('start_time')
            lectures_4th = Schedule.objects.filter(day_of_week__iexact=current_day, academic_year='4th Year', department=dept).select_related('employee').order_by('start_time')
            
            all_lectures_today = Schedule.objects.filter(day_of_week__iexact=current_day, department=dept).select_related('employee').order_by('start_time')
            active_proxy_count = all_lectures_today.filter(is_proxy=True).count()

            # Calculate active directories
            busy_employee_ids = set()
            busy_proxy_names = set()
            for entry in all_lectures_today:
                if point_in_slot(current_time, entry.start_time, entry.end_time):
                    busy_employee_ids.add(entry.employee_id)
                    if entry.is_proxy and entry.proxy_teacher_name:
                        busy_proxy_names.add(entry.proxy_teacher_name.strip().lower())

            # Get all employees belonging to this department OR teaching schedules of this department
            active_employees = Employee.objects.filter(
                models.Q(department=dept) | models.Q(schedules__department=dept)
            ).distinct().order_by('name')

            faculty_directory = []
            for employee in active_employees:
                name_key = employee.name.strip().lower()
                if employee.id in busy_employee_ids or name_key in busy_proxy_names:
                    status, status_class = 'In Lecture', 'rose'
                else:
                    status, status_class = 'Available', 'emerald'

                faculty_directory.append({
                    'name': employee.name,
                    'status': status,
                    'status_class': status_class,
                    'department': employee.department,
                })

            free_faculty_count = sum(1 for f in faculty_directory if f['status'] == 'Available')

            # Workload heatmaps
            faculty_load = []
            for emp in active_employees:
                weekly_classes = Schedule.objects.filter(employee=emp).count()
                daily_classes = Schedule.objects.filter(employee=emp, day_of_week=current_day).count()
                fatigue_pct = min(100, int((weekly_classes / 15) * 100))
                faculty_load.append({
                    'name': emp.name,
                    'weekly_classes': weekly_classes,
                    'daily_classes': daily_classes,
                    'fatigue_pct': fatigue_pct,
                })

            # Conflict checking
            conflicts = []
            schedules = Schedule.objects.filter(department=dept).select_related('employee')
            for i, s1 in enumerate(schedules):
                for s2 in schedules[i+1:]:
                    if s1.employee == s2.employee and s1.day_of_week == s2.day_of_week:
                        if point_in_slot(s1.start_time, s2.start_time, s2.end_time) or point_in_slot(s2.start_time, s1.start_time, s1.end_time):
                            conflicts.append(
                                f"⚠️ Conflict: {s1.employee.name} double-booked on {s1.day_of_week} at {s1.start_time}–{s1.end_time} "
                                f"between [{s1.academic_year} Sec {s1.section}] and [{s2.academic_year} Sec {s2.section}]!"
                            )

            # Pending swaps inbox
            pending_swaps = SwapRequest.objects.filter(status='Pending', requestor__department=dept).select_related('requestor', 'target_teacher', 'schedule_slot', 'target_slot')

            # Merge lectures on the fly for premium timeline view
            merged_lectures = _group_and_merge_schedules(all_lectures_today)

            base_ctx.update({
                'lectures_2nd': lectures_2nd,
                'lectures_3rd': lectures_3rd,
                'lectures_4th': lectures_4th,
                'lectures': merged_lectures, # compat
                'total_lectures_today': len(merged_lectures),
                'active_proxy_count': active_proxy_count,
                'free_faculty_count': free_faculty_count,
                'faculty_directory': faculty_directory,
                'faculty_load': faculty_load,
                'conflicts': conflicts,
                'pending_swaps': pending_swaps,
            })

        else:
            # ── FACULTY WORKSPACE ──
            faculty_emp = profile.employee
            my_lectures = []
            my_sent_requests = []
            my_received_requests = []
            my_syllabus_logs = []

            if faculty_emp:
                my_lectures = Schedule.objects.filter(
                    models.Q(employee=faculty_emp) |
                    models.Q(is_proxy=True, proxy_teacher_name=faculty_emp.name)
                ).order_by('day_of_week', 'start_time')

                my_sent_requests = SwapRequest.objects.filter(requestor=faculty_emp).select_related('target_teacher', 'schedule_slot', 'target_slot')
                my_received_requests = SwapRequest.objects.filter(target_teacher=faculty_emp).select_related('requestor', 'schedule_slot', 'target_slot')
                my_syllabus_logs = SyllabusLog.objects.filter(logged_by=faculty_emp).select_related('schedule')

            all_teachers = Employee.objects.all().order_by('name')
            all_lectures_today = Schedule.objects.filter(day_of_week__iexact=current_day).select_related('employee').order_by('start_time')
            active_proxy_count = all_lectures_today.filter(is_proxy=True).count()

            # Merge daily timeline on the fly for premium timeline view
            merged_lectures = _group_and_merge_schedules(all_lectures_today)

            base_ctx.update({
                'my_lectures': my_lectures,
                'my_sent_requests': my_sent_requests,
                'my_received_requests': my_received_requests,
                'my_syllabus_logs': my_syllabus_logs,
                'all_teachers': all_teachers,
                'lectures': merged_lectures, # compat
                'total_lectures_today': len(merged_lectures),
                'active_proxy_count': active_proxy_count,
            })

        return base_ctx

    except Exception as exc:
        logger.exception('Dashboard context build failed: %s', exc)
        return {
            'lectures': [],
            'current_day': '',
            'current_time': '',
            'total_lectures_today': 0,
            'active_proxy_count': 0,
            'free_faculty_count': 0,
            'faculty_directory': [],
            'celery_mode_label': 'Unknown',
            'dashboard_error': str(exc),
        }


def _ensure_default_users():
    """Seed HOD and Faculty user accounts automatically if missing."""
    from django.contrib.auth.models import User
    from scheduler_api.models import UserProfile, Employee
    try:
        # Seed HOD
        hod_user, created = User.objects.get_or_create(username='hod', defaults={'email': 'hod@sistec.ac.in'})
        if created or not hod_user.has_usable_password():
            hod_user.set_password('admin')
            hod_user.save()
        
        hod_profile, _ = UserProfile.objects.get_or_create(user=hod_user)
        hod_profile.role = 'HOD'
        hod_profile.save()

        # Cleanup old generic title-based accounts to keep database clean
        User.objects.filter(username__in=['prof_mr', 'prof_ms', 'prof_dr']).delete()

        # Seed Faculty accounts
        for employee in Employee.objects.all():
            parts = [p.strip() for p in employee.name.split() if p.strip()]
            
            # Skip titles like "Mr.", "Ms.", "Dr.", "Mrs."
            if parts and parts[0].lower() in ['mr.', 'mr', 'ms.', 'ms', 'mrs.', 'mrs', 'dr.', 'dr']:
                first_name = parts[1].lower() if len(parts) > 1 else 'faculty'
            else:
                first_name = parts[0].lower() if parts else 'faculty'
                
            first_name = "".join(c for c in first_name if c.isalnum())
            username = f"prof_{first_name}"

            fac_user, u_created = User.objects.get_or_create(username=username, defaults={'email': f"{first_name}@sistec.ac.in"})
            if u_created or not fac_user.has_usable_password():
                fac_user.set_password('faculty123')
                fac_user.save()

            fac_profile, _ = UserProfile.objects.get_or_create(user=fac_user)
            fac_profile.role = 'Faculty'
            fac_profile.employee = employee
            fac_profile.save()
    except Exception as exc:
        logger.warning('Default user seeding failed: %s', exc)


# ─────────────────────────────────────────────────────────────
# INDEX
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class IndexView(View):

    def get(self, request):
        from django.shortcuts import render

        try:
            context = _build_dashboard_context(request)
            return render(request, 'index.html', context)
        except Exception as exc:
            logger.exception('IndexView failed: %s', exc)
            return render(request, 'index.html', {'lectures': [], 'current_day': ''})


# ─────────────────────────────────────────────────────────────
# TIMETABLE UPLOAD
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class TimetableUploadView(View):

    def post(self, request):

        try:

            if 'file' not in request.FILES:

                return JsonResponse(
                    {'error': 'No file uploaded'},
                    status=400
                )

            uploaded_file = request.FILES['file']

            allowed_extensions = ['.png', '.jpg', '.jpeg']

            file_ext = os.path.splitext(
                uploaded_file.name
            )[1].lower()

            if file_ext not in allowed_extensions:

                return JsonResponse(
                    {'error': 'Invalid image type'},
                    status=400
                )

            from scheduler_api.models import TimetableFile

            timetable_record = TimetableFile(
                file=uploaded_file
            )

            timetable_record.save()

            file_path = timetable_record.file.path

            print(f"[ChronosAI] File saved to: {file_path}")

            from scheduler_api.utils import process_timetable_image

            parsed_data = process_timetable_image(file_path)

            schedule = parsed_data.get('schedule', [])

            if not schedule:

                return JsonResponse(
                    {'error': 'No schedule extracted'},
                    status=422
                )

            print(
                f"[ChronosAI] Returning {len(schedule)} rows."
            )

            return JsonResponse({
                'rows': schedule,
                'count': len(schedule)
            })

        except Exception as e:

            traceback.print_exc()

            return JsonResponse(
                {'error': str(e)},
                status=500
            )


# ─────────────────────────────────────────────────────────────
# TIMETABLE CONFIRM
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class TimetableConfirmView(View):

    def post(self, request):

        try:

            body = json.loads(request.body)

            rows = body.get('rows', [])

            if not rows:

                return JsonResponse(
                    {'error': 'No rows received'},
                    status=400
                )

            from scheduler_api.models import (
                Employee,
                Schedule
            )

            dept = 'CSE-AIDS'
            if request.user.is_authenticated:
                try:
                    dept = request.user.profile.department or 'CSE-AIDS'
                except Exception:
                    pass

            # Gather all academic years present in the confirmed rows
            years_to_update = set()
            for row in rows:
                ay = str(row.get('academic_year', '')).strip()
                if ay:
                    years_to_update.add(ay)

            with transaction.atomic():
                # Non-destructive deletion: only clear old schedules for the target years & department
                if years_to_update:
                    Schedule.objects.filter(academic_year__in=years_to_update, department=dept).delete()
                else:
                    Schedule.objects.filter(department=dept).delete()

                employee_cache = {}
                schedule_objects = []

                for row in rows:

                    day = str(
                        row.get('day', '')
                    ).strip()

                    start_time = str(
                        row.get('start_time', '')
                    ).strip()

                    end_time = str(
                        row.get('end_time', '')
                    ).strip()

                    subject = str(
                        row.get('subject', '')
                    ).strip()

                    faculty = str(
                        row.get('faculty', '')
                    ).strip()

                    # Phase 3 upgrades for multiple batches
                    academic_year = str(row.get('academic_year', '3rd Year')).strip()
                    semester = int(row.get('semester', 6))
                    section = str(row.get('section', 'A')).strip()
                    room_number = str(row.get('room_number', 'Room 302')).strip()

                    if not all([
                        day,
                        start_time,
                        subject,
                        faculty
                    ]):
                        continue

                    start_time = _normalize_time(start_time)
                    end_time = _normalize_time(end_time)

                    # Split joint/composite faculty names to prevent composite employee profiles
                    import re
                    faculty_parts = re.split(r'/|&|\band\b', faculty)
                    faculty_names = []
                    for p in faculty_parts:
                        name = p.strip()
                        name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                        if name and name.lower() not in ['new faculty', 'none', 'tg/lib']:
                            faculty_names.append(name)
                    
                    if not faculty_names:
                        faculty_names = [faculty.strip()]

                    for name in faculty_names:
                        if name not in employee_cache:
                            employee, _ = Employee.objects.get_or_create(
                                name=name,
                                defaults={'department': dept}
                            )
                            employee_cache[name] = employee

                        employee = employee_cache[name]

                        schedule_objects.append(
                            Schedule(
                                employee=employee,
                                day_of_week=day,
                                start_time=start_time,
                                end_time=end_time,
                                task_name=subject,
                                is_proxy=False,
                                academic_year=academic_year,
                                semester=semester,
                                section=section,
                                room_number=room_number,
                                department=dept,
                            )
                        )

                Schedule.objects.bulk_create(
                    schedule_objects
                )

            return JsonResponse({
                'success': True,
                'entries_saved': len(schedule_objects),
            })

        except Exception as e:

            traceback.print_exc()

            return JsonResponse(
                {'error': str(e)},
                status=500
            )


# ─────────────────────────────────────────────────────────────
# CHAT ASSISTANT
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class ChatAssistantView(View):

    def post(self, request):

        try:

            body = json.loads(request.body)

            query = str(
                body.get('query', '')
            ).strip()

            if not query:

                return JsonResponse(
                    {'error': 'Empty query'},
                    status=400
                )

            query_lower = query.lower()

            print(
                f"[ChronosAI Router] Query: {query}"
            )

            # FAST PATH 1

            if _is_bot_description_query(query_lower):

                return JsonResponse({
                    'response': _bot_description_response(),
                    'route': 'fast_path'
                })

            # Check if query contains any specific employee or subject/task name
            is_specific_query = False
            try:
                from scheduler_api.models import Employee, Schedule
                # Get all employee name parts (lowercase)
                emp_names = set()
                for emp in Employee.objects.all():
                    for part in emp.name.lower().split():
                        p = "".join(c for c in part if c.isalnum())
                        if p and p not in ['mr', 'ms', 'mrs', 'dr', 'prof']:
                            emp_names.add(p)
                
                # Get all distinct subject/task name parts (lowercase)
                subj_words = set()
                for task in Schedule.objects.values_list('task_name', flat=True).distinct():
                    for part in task.lower().split():
                        p = "".join(c for c in part if c.isalnum())
                        if p and len(p) > 2:
                            subj_words.add(p)
                
                # Tokenize the query
                query_tokens = ["".join(c for c in w if c.isalnum()) for w in query_lower.split()]
                
                # Check if any token matches
                for token in query_tokens:
                    if token in emp_names or token in subj_words:
                        is_specific_query = True
                        break
            except Exception as e:
                logger.warning("Failed to run specific query check: %s", e)

            # FAST PATH 2

            detected_day = _detect_day_in_query(query_lower)
            detected_year = _detect_academic_year_in_query(query_lower)

            is_schedule_query = any(
                kw in query_lower
                for kw in [
                    'schedule',
                    'class',
                    'lecture',
                    'timetable',
                    'show',
                    'all'
                ]
            )

            if (
                detected_day
                and is_schedule_query
                and not is_specific_query
                and not any(
                    kw in query_lower
                    for kw in (
                        FREE_FACULTY_KEYWORDS
                        + PROXY_KEYWORDS
                    )
                )
            ):
                dept = 'CSE-AIDS'
                if request.user.is_authenticated:
                    try:
                        dept = request.user.profile.department or 'CSE-AIDS'
                    except Exception:
                        pass

                response_text = _fast_day_schedule_response(
                    day=detected_day,
                    academic_year=detected_year,
                    department=dept
                )

                return JsonResponse({
                    'response': response_text,
                    'route': 'fast_path'
                })

            # Proxy / assign queries → LangGraph agent (assign_proxy_tool + conflict guard)

            # AGENT PATH

            print(
                "[ChronosAI Router] Routing to LangGraph"
            )

            from scheduler_api.agent_graph import (
                get_compiled_graph
            )

            compiled_graph = get_compiled_graph()

            if compiled_graph is None:

                return JsonResponse({
                    'response': (
                        "AI agent unavailable."
                    ),
                    'route': 'fallback'
                })

            from django.utils import timezone
            now = timezone.localtime(timezone.now())
            current_day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][now.weekday()]
            current_time = now.strftime('%H:%M')
            dept = 'CSE-AIDS'
            role = 'Faculty'
            if request.user.is_authenticated:
                try:
                    dept = request.user.profile.department or 'CSE-AIDS'
                    role = request.user.profile.role
                except Exception:
                    pass

            enriched_query = (
                f"[Context: Today is {current_day}, Current Time is {current_time}, User Department is {dept}, User Role is {role}]\n"
                f"Query: {query}"
            )

            messages = [
                HumanMessage(content=enriched_query)
            ]

            result = compiled_graph.invoke(
                {
                    "messages": messages
                },
                config={
                    "recursion_limit": 10
                }
            )

            graph_messages = result.get(
                "messages",
                []
            )

            final_response = ""

            for msg in reversed(graph_messages):

                if (
                    hasattr(msg, 'content')
                    and msg.content
                ):

                    if (
                        isinstance(msg.content, str)
                        and msg.content.strip()
                    ):

                        final_response = msg.content
                        break

            if not final_response:

                final_response = (
                    "No response generated."
                )

            print(
                f"[ChronosAI] Response: {final_response}"
            )

            return JsonResponse({
                'response': final_response,
                'route': 'agent'
            })

        except Exception as e:

            traceback.print_exc()

            return JsonResponse(
                {'error': str(e)},
                status=500
            )


# ─────────────────────────────────────────────────────────────
# MANUAL PROXY
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class ProxyManualView(View):

    def post(self, request):

        if not request.user.is_authenticated or request.user.profile.role != 'HOD':
            return JsonResponse(
                {'error': 'Access Denied. Only the HOD can assign proxy teachers.'},
                status=403
            )

        try:

            body = json.loads(request.body)

            day = body.get('day', '')
            time = body.get('time', '')
            absent_teacher = body.get(
                'absent_teacher',
                ''
            )

            proxy_teacher = body.get(
                'proxy_teacher',
                ''
            )

            if not all([
                day,
                time,
                absent_teacher,
                proxy_teacher
            ]):

                return JsonResponse(
                    {'error': 'Missing fields'},
                    status=400
                )

            from scheduler_api.models import (
                Schedule,
                Employee
            )

            normalized_time = _normalize_time(time)
            schedule_entry = resolve_schedule_slot(day, normalized_time, absent_teacher)

            if not schedule_entry:
                return JsonResponse(
                    {'error': 'Schedule not found for absent teacher at that slot'},
                    status=404,
                )

            proxy_employee = (
                Employee.objects
                .filter(name__icontains=proxy_teacher)
                .first()
            )

            if not proxy_employee:
                return JsonResponse(
                    {'error': 'Proxy teacher not found'},
                    status=404,
                )

            has_conflict, conflict_message = check_teacher_double_booking(
                day=day,
                slot_start=schedule_entry.start_time,
                slot_end=schedule_entry.end_time,
                teacher_name=proxy_employee.name,
                exclude_schedule_id=schedule_entry.pk,
            )

            if has_conflict:
                return JsonResponse(
                    {'error': conflict_message},
                    status=409,
                )

            schedule_entry.is_proxy = True
            schedule_entry.proxy_teacher_name = proxy_employee.name
            schedule_entry.save()

            try:
                from scheduler_api.tasks import send_proxy_alert_email
                slot_description = (
                    f'{schedule_entry.day_of_week} '
                    f'{schedule_entry.start_time}–{schedule_entry.end_time}'
                )
                send_proxy_alert_email.delay(
                    teacher_name=proxy_employee.name,
                    slot=slot_description,
                    subject=schedule_entry.task_name,
                )
            except Exception as celery_err:
                logger.warning('Proxy alert Celery dispatch failed: %s', celery_err)

            return JsonResponse({
                'success': True,
                'message': (
                    f"{proxy_employee.name} assigned successfully."
                )
            })

        except Exception as e:

            traceback.print_exc()

            return JsonResponse(
                {'error': str(e)},
                status=500
            )


# ─────────────────────────────────────────────────────────────
# AUTHENTICATIONS & APPROVALS (PHASE 3 EXTRA APIS)
# ─────────────────────────────────────────────────────────────

from django.contrib.auth import authenticate, login as django_login, logout as django_logout

@method_decorator(csrf_exempt, name='dispatch')
class AuthLoginView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            username = body.get('username', '').strip()
            password = body.get('password', '').strip()
            user = authenticate(request, username=username, password=password)
            if user is not None:
                django_login(request, user)
                role = 'Faculty'
                try:
                    role = user.profile.role
                except Exception:
                    pass
                return JsonResponse({'success': True, 'role': role, 'username': user.username})
            else:
                return JsonResponse({'error': 'Invalid username or password.'}, status=401)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AuthLogoutView(View):
    def post(self, request):
        django_logout(request)
        return JsonResponse({'success': True})


@method_decorator(csrf_exempt, name='dispatch')
class AuthRegisterView(View):
    def post(self, request):
        try:
            from django.contrib.auth.models import User
            from scheduler_api.models import UserProfile, Employee

            body = json.loads(request.body)
            username = body.get('username', '').strip()
            password = body.get('password', '').strip()
            email = body.get('email', '').strip()
            role = body.get('role', 'Faculty').strip()
            employee_id = body.get('employee_id')
            department = body.get('department', '').strip()

            if not username or not password:
                return JsonResponse({'error': 'Username and password are required.'}, status=400)

            if role == 'HOD':
                if not department:
                    return JsonResponse({'error': 'HOD accounts must select a department.'}, status=400)
                # Ensure only one HOD exists per department
                if UserProfile.objects.filter(role='HOD', department=department).exists():
                    existing_hod = UserProfile.objects.filter(role='HOD', department=department).first()
                    return JsonResponse({
                        'error': f"Department '{department}' already has an HOD account registered ('{existing_hod.user.username}'). Only one HOD is allowed per department."
                    }, status=400)

            if User.objects.filter(username__iexact=username).exists():
                return JsonResponse({'error': f"Username '{username}' already exists. Please choose a different username."}, status=400)

            # Validate employee profile linking for Faculty
            employee = None
            if role == 'Faculty':
                if not employee_id:
                    return JsonResponse({'error': 'Faculty accounts must be linked to an employee profile.'}, status=400)
                try:
                    employee = Employee.objects.get(pk=int(employee_id))
                except (Employee.DoesNotExist, ValueError):
                    return JsonResponse({'error': 'Selected faculty member profile does not exist.'}, status=404)

                # Check if employee is already linked to another user account
                if UserProfile.objects.filter(employee=employee).exists():
                    existing_profile = UserProfile.objects.filter(employee=employee).first()
                    return JsonResponse({
                        'error': f"Faculty profile '{employee.name}' is already linked to another account ('{existing_profile.user.username}')."
                    }, status=400)
                
                # Inherit department from the Employee record
                department = employee.department

            # Create standard User
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Create UserProfile
            profile = UserProfile.objects.create(
                user=user,
                role=role,
                employee=employee,
                department=department
            )

            # Auto login user immediately after registration
            django_login(request, user)

            return JsonResponse({
                'success': True,
                'role': role,
                'username': user.username,
                'message': 'Account registered successfully. Welcome to ChronosAI!'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SwapRequestCreateView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body)
            schedule_slot_id = body.get('schedule_slot')
            target_teacher_name = body.get('target_teacher')
            target_slot_id = body.get('target_slot')
            
            from scheduler_api.models import Schedule, Employee, SwapRequest
            
            requestor_profile = request.user.profile
            requestor_emp = requestor_profile.employee
            if not requestor_emp:
                return JsonResponse({'error': 'Your user account is not linked to any faculty employee profile.'}, status=400)
                
            target_emp = Employee.objects.filter(name__icontains=target_teacher_name).first()
            if not target_emp:
                return JsonResponse({'error': f"Target faculty member '{target_teacher_name}' not found in database."}, status=404)
                
            try:
                schedule_slot = Schedule.objects.get(pk=schedule_slot_id)
            except Schedule.DoesNotExist:
                return JsonResponse({'error': 'Your selected schedule slot was not found.'}, status=404)

            # Resolve target_slot either by pk or dynamically via day & start_time
            target_slot = None
            try:
                target_slot = Schedule.objects.get(pk=int(target_slot_id))
            except (ValueError, TypeError):
                # Dynamically look up using start_time, same day of week, and target teacher
                normalized_start = _normalize_time(str(target_slot_id).strip())
                target_slot = Schedule.objects.filter(
                    employee=target_emp,
                    day_of_week__iexact=schedule_slot.day_of_week,
                    start_time=normalized_start
                ).first()
                
            if not target_slot:
                return JsonResponse({
                    'error': f"Could not find a lecture slot for {target_emp.name} on {schedule_slot.day_of_week} starting at '{target_slot_id}'."
                }, status=404)
            
            swap_req = SwapRequest.objects.create(
                requestor=requestor_emp,
                target_teacher=target_emp,
                schedule_slot=schedule_slot,
                target_slot=target_slot,
                status='Pending'
            )
            
            return JsonResponse({
                'success': True, 
                'message': f"Mutual swap request between {requestor_emp.name} and {target_emp.name} sent to HOD Approval queue!"
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SwapRequestActionView(View):
    def post(self, request):
        if not request.user.is_authenticated or request.user.profile.role != 'HOD':
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body)
            request_id = body.get('request_id')
            action = body.get('action') # 'approve' or 'reject'
            
            from scheduler_api.models import SwapRequest
            swap_req = SwapRequest.objects.select_related('requestor', 'target_teacher', 'schedule_slot', 'target_slot').get(pk=request_id)
            
            if action == 'approve':
                with transaction.atomic():
                    slot_a = swap_req.schedule_slot
                    slot_b = swap_req.target_slot
                    
                    emp_a = slot_a.employee
                    emp_b = slot_b.employee
                    
                    # Swap teacher foreign key relations
                    slot_a.employee = emp_b
                    slot_b.employee = emp_a
                    
                    slot_a.save()
                    slot_b.save()
                    
                    swap_req.status = 'Approved'
                    swap_req.save()
                    
                # Simulated Celery Alert confirmations
                try:
                    from scheduler_api.tasks import send_swap_confirmation_email
                    send_swap_confirmation_email.delay(
                        teacher_a=emp_a.name,
                        teacher_b=emp_b.name,
                        slot_a=f"{slot_a.day_of_week} {slot_a.start_time}–{slot_a.end_time}",
                        slot_b=f"{slot_b.day_of_week} {slot_b.start_time}–{slot_b.end_time}",
                        subject_a=slot_a.task_name,
                        subject_b=slot_b.task_name,
                    )
                except Exception as celery_err:
                    logger.warning('Swap alert Celery dispatch failed: %s', celery_err)
                    
                return JsonResponse({'success': True, 'message': 'Swap request successfully approved. Timetables updated!'})
            else:
                swap_req.status = 'Rejected'
                swap_req.save()
                return JsonResponse({'success': True, 'message': 'Swap request rejected successfully.'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SyllabusLogCreateView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body)
            schedule_id = body.get('schedule_id')
            topic = body.get('topic_covered', '').strip()
            
            from scheduler_api.models import Schedule, SyllabusLog
            schedule = Schedule.objects.get(pk=schedule_id)
            faculty_emp = request.user.profile.employee
            
            if not faculty_emp:
                return JsonResponse({'error': 'No employee profile linked to your user.'}, status=400)
                
            SyllabusLog.objects.create(
                schedule=schedule,
                topic_covered=topic,
                logged_by=faculty_emp
            )
            return JsonResponse({'success': True, 'message': 'Syllabus/lecture topic successfully recorded.'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ProfileAlertUpdateView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body)
            phone = body.get('phone', '').strip()
            telegram_chat_id = body.get('telegram_chat_id', '').strip()
            
            profile = request.user.profile
            profile.phone = phone
            profile.telegram_chat_id = telegram_chat_id
            profile.save()
            
            return JsonResponse({'success': True, 'message': 'Omnichannel alert preferences saved successfully.'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class UpdateRoomView(View):
    def post(self, request):
        if not request.user.is_authenticated or request.user.profile.role != 'HOD':
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body)
            schedule_id = body.get('schedule_id')
            new_room = body.get('room_number', '').strip()
            
            if not new_room:
                return JsonResponse({'error': 'Room designation cannot be empty.'}, status=400)
                
            from scheduler_api.models import Schedule
            target = Schedule.objects.get(pk=schedule_id)
            
            # Find and update all entries sharing the exact same slot parameters to keep joint classes in the same room!
            joint_entries = Schedule.objects.filter(
                day_of_week=target.day_of_week,
                start_time=target.start_time,
                end_time=target.end_time,
                academic_year=target.academic_year,
                section=target.section,
                task_name=target.task_name,
                department=target.department
            )
            
            count = joint_entries.update(room_number=new_room)
            
            return JsonResponse({
                'success': True,
                'message': f"Room updated successfully to '{new_room}' for {count} lecture entries."
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ResetDemoDatabaseView(View):
    def post(self, request):
        if not request.user.is_authenticated or request.user.profile.role != 'HOD':
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            from django.db import transaction
            from scheduler_api.models import Schedule, Employee, TimetableFile, SyllabusLog, SwapRequest
            from scheduler_api.utils import (
                _get_local_4th_sem_a_schedule,
                _get_local_4th_sem_b_schedule,
                _get_local_6th_sem_a_schedule,
                _get_local_6th_sem_b_schedule,
                _get_local_8th_sem_schedule
            )
            
            with transaction.atomic():
                # Clear registered user accounts & profiles
                from django.contrib.auth.models import User
                from scheduler_api.models import UserProfile
                UserProfile.objects.all().delete()
                User.objects.all().delete()

                # Clear dynamic datasets
                SyllabusLog.objects.all().delete()
                SwapRequest.objects.all().delete()
                Schedule.objects.all().delete()
                TimetableFile.objects.all().delete()
                
                # Load fresh timetables
                schedules_to_load = []
                schedules_to_load.extend(_get_local_4th_sem_a_schedule()["schedule"])
                schedules_to_load.extend(_get_local_4th_sem_b_schedule()["schedule"])
                schedules_to_load.extend(_get_local_6th_sem_a_schedule()["schedule"])
                schedules_to_load.extend(_get_local_6th_sem_b_schedule()["schedule"])
                schedules_to_load.extend(_get_local_8th_sem_schedule()["schedule"])
                
                employee_cache = {}
                for emp in Employee.objects.all():
                    employee_cache[emp.name.strip()] = emp
                    
                schedule_objects = []
                for row in schedules_to_load:
                    day = row["day"]
                    start_time = row["start_time"]
                    end_time = row["end_time"]
                    subject = row["subject"]
                    faculty = row["faculty"]
                    academic_year = row["academic_year"]
                    semester = row["semester"]
                    section = row["section"]
                    room_number = row["room_number"]
                    dept = "CSE-AIDS"
                    
                    # Split joint/composite faculty names
                    import re
                    faculty_parts = re.split(r'/|&|\band\b', faculty)
                    faculty_names = []
                    for p in faculty_parts:
                        name = p.strip()
                        name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                        if name and name.lower() not in ['new faculty', 'none', 'tg/lib']:
                            faculty_names.append(name)
                    
                    if not faculty_names:
                        faculty_names = [faculty.strip()]
                        
                    for name in faculty_names:
                        if name not in employee_cache:
                            employee, _ = Employee.objects.get_or_create(
                                name=name,
                                defaults={'department': dept}
                            )
                            employee_cache[name] = employee
                            
                        employee = employee_cache[name]
                        
                        schedule_objects.append(
                            Schedule(
                                employee=employee,
                                day_of_week=day,
                                start_time=start_time,
                                end_time=end_time,
                                task_name=subject,
                                is_proxy=False,
                                academic_year=academic_year,
                                semester=semester,
                                section=section,
                                room_number=room_number,
                                department=dept
                            )
                        )
                        
                Schedule.objects.bulk_create(schedule_objects)
                
                # Re-seed default users
                _ensure_default_users()
                
            django_logout(request)
            return JsonResponse({
                'success': True,
                'message': f"Database wiped and successfully seeded with {len(schedule_objects)} conflict-free timetable entries."
            })
        except Exception as e:
            logger.exception("Database reset via panel failed: %s", e)
            return JsonResponse({'error': f"Failed to reset: {str(e)}"}, status=500)