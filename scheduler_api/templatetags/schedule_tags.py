"""
Django template tags/filters for ChronosAI schedule dashboard rendering.
"""
from django import template

register = template.Library()


@register.filter
def faculty_display_name(lecture):
    """Return proxy substitute or primary employee name for UI."""
    if getattr(lecture, 'is_proxy', False) and getattr(lecture, 'proxy_teacher_name', None):
        return lecture.proxy_teacher_name
    if hasattr(lecture, 'employee'):
        return lecture.employee.name
    return ''


@register.filter
def is_proxy_active(lecture):
    return bool(getattr(lecture, 'is_proxy', False))


@register.simple_tag
def proxy_badge_label(lecture):
    if getattr(lecture, 'is_proxy', False):
        return 'Proxy Active'
    return 'Schedule Locked'
