from celery import shared_task
from django.utils import timezone
from django.conf import settings
from .models import Task
import requests


def send_telegram_message(chat_id, text):
    """Send message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


@shared_task
def send_task_notification(task_id):
    try:
        task = Task.objects.get(id=task_id)
        
        if task.notified or task.status != 'pending':
            return f"Task {task_id} skipped"
        
        if send_telegram_message(task.user.telegram_id, f"⏰ Напоминание: {task.title}"):
            task.notified = True
            task.status = 'completed'
            task.save(update_fields=['notified', 'status'])
            return f"Notified task {task_id}"
        
        return f"Failed to notify task {task_id}"
        
    except Task.DoesNotExist:
        return f"Task {task_id} not found"




