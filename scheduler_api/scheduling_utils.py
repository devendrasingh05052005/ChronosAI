"""
Shared scheduling utilities: time normalization, overlap detection,
and double-booking guards used by views, Celery tasks, and LangGraph tools.
"""
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger('chronosai.scheduling')


def normalize_time_to_hhmm(time_str: str) -> str:
    """Normalize AM/PM or HH:MM strings to 24-hour HH:MM."""
    if not time_str:
        return ''

    s = str(time_str).strip().upper()

    am_pm_match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$', s)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        minute = int(am_pm_match.group(2) or 0)
        period = am_pm_match.group(3)
        if period == 'PM' and hour != 12:
            hour += 12
        if period == 'AM' and hour == 12:
            hour = 0
        return f'{hour:02d}:{minute:02d}'

    hm_match = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if hm_match:
        return f'{int(hm_match.group(1)):02d}:{hm_match.group(2)}'

    return s


def time_to_minutes(time_str: str) -> Optional[int]:
    """Convert HH:MM to minutes from midnight; returns None if invalid."""
    normalized = normalize_time_to_hhmm(time_str)
    match = re.match(r'^(\d{1,2}):(\d{2})$', normalized)
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def time_ranges_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """True when two half-open intervals [start, end) overlap."""
    a_start = time_to_minutes(start_a)
    a_end = time_to_minutes(end_a)
    b_start = time_to_minutes(start_b)
    b_end = time_to_minutes(end_b)

    if None in (a_start, a_end, b_start, b_end):
        return False

    return a_start < b_end and b_start < a_end


def point_in_slot(time_point: str, slot_start: str, slot_end: str) -> bool:
    """True when time_point falls inside [slot_start, slot_end)."""
    point = time_to_minutes(normalize_time_to_hhmm(time_point))
    start = time_to_minutes(slot_start)
    end = time_to_minutes(slot_end)
    if point is None or start is None or end is None:
        return False
    return start <= point < end


def check_teacher_double_booking(
    day: str,
    slot_start: str,
    slot_end: str,
    teacher_name: str,
    exclude_schedule_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Verify a teacher is not already booked (regular or proxy) in an overlapping slot.

    Returns:
        (has_conflict, message) — message is empty when no conflict.
    """
    from scheduler_api.models import Schedule

    try:
        day_filter = day.strip()
        teacher_filter = teacher_name.strip()

        if not all([day_filter, slot_start, slot_end, teacher_filter]):
            return True, 'Validation failed: day, time range, and teacher name are required.'

        slot_start = normalize_time_to_hhmm(slot_start)
        slot_end = normalize_time_to_hhmm(slot_end)

        candidates = Schedule.objects.filter(
            day_of_week__icontains=day_filter,
        ).select_related('employee')

        if exclude_schedule_id is not None:
            candidates = candidates.exclude(pk=exclude_schedule_id)

        for entry in candidates:
            if not time_ranges_overlap(
                slot_start, slot_end, entry.start_time, entry.end_time
            ):
                continue

            if entry.employee.name.lower().find(teacher_filter.lower()) >= 0 or \
               teacher_filter.lower() in entry.employee.name.lower():
                return True, (
                    f'CONFLICT DETECTED: {entry.employee.name} is already scheduled for '
                    f'"{entry.task_name}" on {entry.day_of_week} from '
                    f'{entry.start_time} to {entry.end_time} (regular assignment). '
                    f'Choose a different proxy teacher.'
                )

            if entry.is_proxy and entry.proxy_teacher_name:
                proxy_name = entry.proxy_teacher_name
                if teacher_filter.lower() in proxy_name.lower() or \
                   proxy_name.lower() in teacher_filter.lower():
                    return True, (
                        f'CONFLICT DETECTED: {proxy_name} is already assigned as PROXY for '
                        f'"{entry.task_name}" on {entry.day_of_week} from '
                        f'{entry.start_time} to {entry.end_time}. '
                        f'Double-booking is not permitted.'
                    )

        return False, ''

    except Exception as exc:
        logger.exception('Double-booking check failed: %s', exc)
        return True, f'Validation error while checking conflicts: {exc}'


def resolve_schedule_slot(day: str, time: str, teacher_name: str):
    """Find a schedule row for an absent teacher at day/time (point-in-slot)."""
    from scheduler_api.models import Schedule

    normalized_time = normalize_time_to_hhmm(time)
    entries = Schedule.objects.filter(
        employee__name__icontains=teacher_name,
        day_of_week__icontains=day,
    ).select_related('employee')

    for entry in entries:
        if point_in_slot(normalized_time, entry.start_time, entry.end_time):
            return entry

    return entries.filter(start_time=normalized_time).first()


def build_lecture_display_rows(queryset):
    """
    Enrich Schedule queryset rows for template rendering (proxy-aware labels).
    """
    rows = []
    for lecture in queryset:
        rows.append({
            'instance': lecture,
            'start_time': lecture.start_time,
            'end_time': lecture.end_time,
            'task_name': lecture.task_name,
            'is_proxy': lecture.is_proxy,
            'display_faculty': (
                lecture.proxy_teacher_name
                if lecture.is_proxy and lecture.proxy_teacher_name
                else lecture.employee.name
            ),
            'original_faculty': lecture.employee.name,
            'proxy_teacher_name': lecture.proxy_teacher_name or '',
        })
    return rows
