import logging
import time

from celery import shared_task
from django.utils import timezone

from scheduler_api.reminder_dedup import (
    release_lecture_reminder_claim,
    try_claim_lecture_reminder,
    try_claim_proxy_alert,
    try_claim_swap_notification,
)
from scheduler_api.scheduling_utils import normalize_time_to_hhmm

logger = logging.getLogger('chronosai.tasks')


def _simulate_smtp_gateway_dispatch(
    recipient: str,
    subject_line: str,
    body: str,
    metadata: dict | None = None,
) -> dict:
    """
    Simulates an automated SMTP gateway dispatcher (console + structured log).
    Swap this function body with Django send_mail / SES in production.
    """
    metadata = metadata or {}
    try:
        print('\n' + '=' * 60)
        print('[ChronosAI SMTP Gateway] Dispatching notification payload')
        print('=' * 60)
        print(f'  TO       : {recipient}')
        print(f'  SUBJECT  : {subject_line}')
        print(f'  META     : {metadata}')
        print('-' * 60)
        print(body)
        print('=' * 60 + '\n')

        logger.info(
            'SMTP simulation dispatched | to=%s | subject=%s | meta=%s',
            recipient,
            subject_line,
            metadata,
        )

        time.sleep(0.5)

        return {
            'status': 'sent',
            'recipient': recipient,
            'subject': subject_line,
            'body': body,
            'metadata': metadata,
        }
    except Exception as exc:
        logger.exception('SMTP simulation failed: %s', exc)
        raise


def _simulate_whatsapp_gateway_dispatch(phone: str, message: str) -> dict:
    """Simulates WhatsApp push dispatcher via Twilio API node."""
    try:
        print('\n' + '=' * 60)
        print('[ChronosAI WhatsApp Gateway] Push payload dispatched successfully')
        print('=' * 60)
        print(f'  TO PHONE : {phone}')
        print('-' * 60)
        print(message)
        print('=' * 60 + '\n')
        
        logger.info('WhatsApp simulation dispatched | phone=%s', phone)
        time.sleep(0.2)
        return {'status': 'delivered_whatsapp', 'recipient_phone': phone}
    except Exception as exc:
        logger.exception('WhatsApp simulation failed: %s', exc)
        raise


def _simulate_telegram_gateway_dispatch(chat_id: str, message: str) -> dict:
    """Simulates Telegram bot API push notification."""
    try:
        print('\n' + '=' * 60)
        print('[ChronosAI Telegram Bot] Broadcast payload dispatched successfully')
        print('=' * 60)
        print(f'  CHAT ID  : {chat_id}')
        print('-' * 60)
        print(message)
        print('=' * 60 + '\n')
        
        logger.info('Telegram simulation dispatched | chat_id=%s', chat_id)
        time.sleep(0.2)
        return {'status': 'delivered_telegram', 'chat_id': chat_id}
    except Exception as exc:
        logger.exception('Telegram simulation failed: %s', exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_proxy_alert_email(self, teacher_name: str, slot: str, subject: str):
    """
    Asynchronous Celery task: proxy assignment / pre-lecture alert notification.
    Deduplicated via Redis/LocMem so Celery retries do not double-send.
    """
    try:
        if not try_claim_proxy_alert(teacher_name, slot, subject):
            return {
                'status': 'skipped',
                'reason': 'duplicate_proxy_alert',
                'recipient': teacher_name,
            }

        body = (
            f"Hello {teacher_name},\n\n"
            f"This is a reminder that your proxy lecture for '{subject}' "
            f"in slot {slot} is approaching. Please reach the classroom on time.\n\n"
            f"— ChronosAI Automated ERP (SISTec)"
        )
        
        # Omnichannel push message content
        wa_message = (
            f"🔔 *ChronosAI Proxy Assignment Alert* (SISTec)\n\n"
            f"Dear Professor *{teacher_name}*,\n"
            f"You have been assigned to cover a proxy class:\n"
            f"• *Subject:* {subject}\n"
            f"• *Slot:* {slot}\n\n"
            f"Please reach the classroom on time."
        )
        
        tg_message = (
            f"🚀 *[ChronosAI ERP]* Mutual proxy assigned successfully!\n\n"
            f"👤 *Proxy Faculty:* {teacher_name}\n"
            f"📚 *Subject:* {subject}\n"
            f"⏰ *Slot:* {slot}"
        )

        # 1. SMTP Email
        email_res = _simulate_smtp_gateway_dispatch(
            recipient=teacher_name,
            subject_line=f'[ChronosAI] Proxy Alert — {subject}',
            body=body,
            metadata={'slot': slot, 'task_id': str(self.request.id), 'type': 'proxy_alert'},
        )
        
        # 2. WhatsApp Push
        _simulate_whatsapp_gateway_dispatch(
            phone=f"+91 9111{abs(hash(teacher_name)) % 10000000:07d}",
            message=wa_message
        )
        
        # 3. Telegram Push
        _simulate_telegram_gateway_dispatch(
            chat_id=f"tg_{abs(hash(teacher_name)) % 10000000:07d}",
            message=tg_message
        )

        return email_res
    except Exception as exc:
        logger.exception('send_proxy_alert_email failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task(name='scheduler_api.tasks.check_and_send_daily_lecture_reminders')
def check_and_send_daily_lecture_reminders():
    """
    Periodic Celery Beat task (every minute):
    - Scans Schedule rows for the current weekday
    - Finds lectures starting exactly 10 minutes from now
    - Dispatches reminder once per lecture (Redis dedup key)
    """
    from datetime import timedelta

    from scheduler_api.models import Schedule

    try:
        now = timezone.localtime(timezone.now())
        current_day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][now.weekday()]
        target_time_obj = now + timedelta(minutes=10)
        target_time_str = target_time_obj.strftime('%H:%M')

        logger.debug(
            'Reminder scan | day=%s | target_start=%s | now=%s',
            current_day,
            target_time_str,
            now.strftime('%H:%M'),
        )

        day_lectures = Schedule.objects.filter(
            day_of_week__iexact=current_day,
        ).select_related('employee')

        upcoming_lectures = [
            lecture for lecture in day_lectures
            if normalize_time_to_hhmm(lecture.start_time) == target_time_str
        ]

        if not upcoming_lectures:
            msg = f'No lectures starting at {target_time_str} on {current_day}.'
            logger.debug(msg)
            return msg

        sent_count = 0
        skipped_count = 0

        for lecture in upcoming_lectures:
            if lecture.is_proxy and lecture.proxy_teacher_name:
                recipient = lecture.proxy_teacher_name
                role = 'proxy'
            else:
                recipient = lecture.employee.name
                role = 'regular'

            if not try_claim_lecture_reminder(lecture, role):
                skipped_count += 1
                continue

            slot_label = (
                f'{lecture.day_of_week} {lecture.start_time}–{lecture.end_time}'
            )
            body = (
                f"Hello Professor {recipient},\n\n"
                f"This is an automated reminder that your lecture for "
                f"'{lecture.task_name}' starts in 10 minutes "
                f'({lecture.start_time} – {lecture.end_time}).\n'
                f'Please reach the classroom.\n\n'
                f'— ChronosAI Lecture Reminder System'
            )

            try:
                _simulate_smtp_gateway_dispatch(
                    recipient=recipient,
                    subject_line=f'[ChronosAI] Lecture in 10 min — {lecture.task_name}',
                    body=body,
                    metadata={
                        'lecture_id': lecture.pk,
                        'role': role,
                        'slot': slot_label,
                        'is_proxy': lecture.is_proxy,
                        'dedup': 'claimed',
                    },
                )
                sent_count += 1
            except Exception as send_exc:
                release_lecture_reminder_claim(lecture, role)
                logger.exception(
                    'Reminder send failed; released dedup claim for retry | lecture_id=%s',
                    lecture.pk,
                )
                raise send_exc

        summary = (
            f'Processed {sent_count} reminder(s), skipped {skipped_count} duplicate(s) '
            f'for {current_day} at {target_time_str}.'
        )
        logger.info(summary)
        return summary

    except Exception as exc:
        logger.exception('check_and_send_daily_lecture_reminders failed: %s', exc)
        return f'Reminder task error: {exc}'


@shared_task(name='scheduler_api.tasks.send_swap_confirmation_email')
def send_swap_confirmation_email(
    teacher_a: str,
    teacher_b: str,
    slot_a: str,
    slot_b: str,
    subject_a: str,
    subject_b: str,
):
    """
    Simulated Celery task: Sends dual confirmation emails and omnichannel alerts for a mutually swapped lecture.
    """
    if not try_claim_swap_notification(teacher_a, teacher_b, slot_a, slot_b):
        logger.info('Swap confirmation email skipped (duplicate/burst swap notification).')
        return "Skipped duplicate/burst swap notification."
        
    try:
        body_a = (
            f"Hello Professor {teacher_a},\n\n"
            f"This email confirms that your lecture swap request with Professor {teacher_b} "
            f"has been approved and successfully executed.\n\n"
            f"Your New Slot: {slot_b} — Subject: {subject_b}\n"
            f"Original Slot: {slot_a} — Subject: {subject_a}\n\n"
            f"— ChronosAI Automated ERP (SISTec)"
        )
        
        body_b = (
            f"Hello Professor {teacher_b},\n\n"
            f"This email confirms that your lecture swap request with Professor {teacher_a} "
            f"has been approved and successfully executed.\n\n"
            f"Your New Slot: {slot_a} — Subject: {subject_a}\n"
            f"Original Slot: {slot_b} — Subject: {subject_b}\n\n"
            f"— ChronosAI Automated ERP (SISTec)"
        )

        # Omnichannel pushes for teacher_a
        wa_msg_a = (
            f"🔄 *ChronosAI Lecture Swap Approved* (SISTec)\n\n"
            f"Dear Professor *{teacher_a}*,\n"
            f"Your lecture swap with Professor *{teacher_b}* has been successfully executed.\n"
            f"• *New Slot:* {slot_b} ({subject_b})\n"
            f"• *Old Slot:* {slot_a} ({subject_a})"
        )
        tg_msg_a = (
            f"🔄 *[ChronosAI ERP]* Lecture swap executed successfully!\n\n"
            f"👤 *Faculty:* {teacher_a}\n"
            f"🔄 *Swapped with:* {teacher_b}\n"
            f"⏰ *New Slot:* {slot_b} — {subject_b}"
        )

        # Omnichannel pushes for teacher_b
        wa_msg_b = (
            f"🔄 *ChronosAI Lecture Swap Approved* (SISTec)\n\n"
            f"Dear Professor *{teacher_b}*,\n"
            f"Your lecture swap with Professor *{teacher_a}* has been successfully executed.\n"
            f"• *New Slot:* {slot_a} ({subject_a})\n"
            f"• *Old Slot:* {slot_b} ({subject_b})"
        )
        tg_msg_b = (
            f"🔄 *[ChronosAI ERP]* Lecture swap executed successfully!\n\n"
            f"👤 *Faculty:* {teacher_b}\n"
            f"🔄 *Swapped with:* {teacher_a}\n"
            f"⏰ *New Slot:* {slot_a} — {subject_a}"
        )

        # 1. SMTP Email for Teacher A
        _simulate_smtp_gateway_dispatch(
            recipient=teacher_a,
            subject_line=f"[ChronosAI] Swap Confirmation Receipt",
            body=body_a,
            metadata={"type": "swap_confirmation", "swapped_with": teacher_b}
        )
        
        # 2. WhatsApp for Teacher A
        _simulate_whatsapp_gateway_dispatch(
            phone=f"+91 9111{abs(hash(teacher_a)) % 10000000:07d}",
            message=wa_msg_a
        )

        # 3. Telegram for Teacher A
        _simulate_telegram_gateway_dispatch(
            chat_id=f"tg_{abs(hash(teacher_a)) % 10000000:07d}",
            message=tg_msg_a
        )

        # 4. SMTP Email for Teacher B
        _simulate_smtp_gateway_dispatch(
            recipient=teacher_b,
            subject_line=f"[ChronosAI] Swap Confirmation Receipt",
            body=body_b,
            metadata={"type": "swap_confirmation", "swapped_with": teacher_a}
        )

        # 5. WhatsApp for Teacher B
        _simulate_whatsapp_gateway_dispatch(
            phone=f"+91 9111{abs(hash(teacher_b)) % 10000000:07d}",
            message=wa_msg_b
        )

        # 6. Telegram for Teacher B
        _simulate_telegram_gateway_dispatch(
            chat_id=f"tg_{abs(hash(teacher_b)) % 10000000:07d}",
            message=tg_msg_b
        )

        return f"Dual confirmation receipts and omnichannel alerts successfully sent to {teacher_a} and {teacher_b}."
    except Exception as exc:
        logger.exception('send_swap_confirmation_email failed: %s', exc)
        raise
