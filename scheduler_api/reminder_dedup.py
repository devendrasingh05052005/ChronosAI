"""
Idempotent reminder deduplication via Django cache (Redis in production, LocMem fallback).

Uses cache.add() (SET NX) so only the first Beat tick / retry claims a lecture reminder.
"""
import hashlib
import logging

from django.conf import settings
from django.core.cache import caches
from django.utils import timezone

from scheduler_api.scheduling_utils import normalize_time_to_hhmm

logger = logging.getLogger('chronosai.tasks')

REMINDER_KEY_PREFIX = 'chronosai:lecture_reminder:v1'
PROXY_ALERT_KEY_PREFIX = 'chronosai:proxy_alert:v1'


def _cache_aliases() -> tuple[str, ...]:
    """Redis first in production; LocMem-only when CHRONOSAI_DEDUP_REDIS_ENABLED=false."""
    if getattr(settings, 'CHRONOSAI_DEDUP_REDIS_ENABLED', True):
        return ('reminder_dedup', 'reminder_dedup_fallback')
    return ('reminder_dedup_fallback',)


def _dedup_ttl_seconds() -> int:
    return int(getattr(settings, 'CHRONOSAI_REMINDER_DEDUP_TTL', 7200))


def build_lecture_reminder_key(
    lecture_id: int,
    day_of_week: str,
    start_time: str,
    recipient_role: str,
    reminder_date: str | None = None,
) -> str:
    """Unique key per lecture occurrence (calendar day + slot + role)."""
    if reminder_date is None:
        reminder_date = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')
    day = day_of_week.strip()
    start = normalize_time_to_hhmm(start_time)
    role = recipient_role.strip().lower()
    return f'{REMINDER_KEY_PREFIX}:{reminder_date}:{day}:{lecture_id}:{role}:{start}'


def build_proxy_alert_key(teacher_name: str, slot: str, subject: str) -> str:
    """Unique key per proxy alert dispatch (hashed subject keeps keys short)."""
    subject_hash = hashlib.sha256(subject.encode('utf-8')).hexdigest()[:16]
    teacher = teacher_name.strip().lower().replace(' ', '_')
    slot_norm = slot.strip().lower().replace(' ', '_')
    return f'{PROXY_ALERT_KEY_PREFIX}:{teacher}:{slot_norm}:{subject_hash}'


def _try_claim_on_cache(cache_alias: str, key: str, ttl: int) -> bool | None:
    """
    Attempt atomic claim on a cache backend.

    Returns:
        True  — claimed (caller should send)
        False — already claimed (skip duplicate)
        None  — backend unavailable (try next alias)
    """
    try:
        backend = caches[cache_alias]
        claimed = backend.add(key, timezone.now().isoformat(), timeout=ttl)
        return bool(claimed)
    except Exception as exc:
        logger.warning(
            'Reminder dedup cache [%s] unavailable: %s',
            cache_alias,
            exc,
        )
        return None


def try_claim_lecture_reminder(
    lecture,
    recipient_role: str,
) -> bool:
    """
    Atomically claim the 10-minute lecture reminder for this row.

    Returns True if this worker should send; False if already sent.
    """
    key = build_lecture_reminder_key(
        lecture_id=lecture.pk,
        day_of_week=lecture.day_of_week,
        start_time=lecture.start_time,
        recipient_role=recipient_role,
    )
    ttl = _dedup_ttl_seconds()

    for alias in _cache_aliases():
        result = _try_claim_on_cache(alias, key, ttl)
        if result is True:
            logger.debug('Reminder dedup claimed | key=%s | cache=%s', key, alias)
            return True
        if result is False:
            logger.info(
                'Reminder dedup skip (duplicate) | key=%s | cache=%s',
                key,
                alias,
            )
            return False

    logger.error(
        'Reminder dedup: no cache backend available; skipping send to avoid duplicates | key=%s',
        key,
    )
    return False


def try_claim_proxy_alert(teacher_name: str, slot: str, subject: str) -> bool:
    """Atomically claim a proxy alert email (prevents Celery retry duplicates)."""
    key = build_proxy_alert_key(teacher_name, slot, subject)
    ttl = _dedup_ttl_seconds()

    for alias in _cache_aliases():
        result = _try_claim_on_cache(alias, key, ttl)
        if result is True:
            return True
        if result is False:
            logger.info('Proxy alert dedup skip | key=%s', key)
            return False

    logger.error('Proxy alert dedup: no cache backend; skipping | key=%s', key)
    return False


def try_claim_swap_notification(teacher_a: str, teacher_b: str, slot_a: str, slot_b: str) -> bool:
    """Atomically claim a swap confirmation notification to prevent instant loops/spams."""
    ts = sorted([teacher_a.strip().lower(), teacher_b.strip().lower()])
    ss = sorted([slot_a.strip().lower(), slot_b.strip().lower()])
    
    key_str = f"chronosai:swap_dedup:v1:{ts[0]}:{ts[1]}:{ss[0]}:{ss[1]}"
    key = hashlib.sha256(key_str.encode('utf-8')).hexdigest()[:32]
    
    # 10 seconds TTL is plenty to filter out burst loops while allowing genuine future swaps
    ttl = 10

    for alias in _cache_aliases():
        result = _try_claim_on_cache(alias, key, ttl)
        if result is True:
            return True
        if result is False:
            logger.info('Swap notification dedup skip | key=%s', key)
            return False

    return True


def release_lecture_reminder_claim(lecture, recipient_role: str) -> None:
    """
    Release a claim after a failed SMTP dispatch so Beat can retry on the next tick.
    Optional — only call when send fails after a successful claim.
    """
    key = build_lecture_reminder_key(
        lecture_id=lecture.pk,
        day_of_week=lecture.day_of_week,
        start_time=lecture.start_time,
        recipient_role=recipient_role,
    )
    for alias in _cache_aliases():
        try:
            caches[alias].delete(key)
        except Exception as exc:
            logger.debug('Could not release dedup key on %s: %s', alias, exc)
