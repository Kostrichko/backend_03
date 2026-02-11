from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from .models import User, Tag, Task
import json


class ModelsLimitsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(telegram_id=111, username='u')

    def test_tag_limit(self):
        for i in range(4):
            Tag.objects.create(user=self.user, name=f't{i}')
        with self.assertRaises(Exception):
            Tag.objects.create(user=self.user, name='overflow')

    def test_task_limit(self):
        for i in range(6):
            Task.objects.create(user=self.user, title=f'T{i}', status='pending')
        with self.assertRaises(Exception):
            Task.objects.create(user=self.user, title='overflow', status='pending')


class ApiEndpointsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(telegram_id=222, username='client')

    def test_create_tag_via_api(self):
        response = self.client.post('/api/tags/create/',
            json.dumps({'telegram_id': self.user.telegram_id, 'name': 'work'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tag.objects.filter(user=self.user).count(), 1)

    def test_create_task_via_api_triggers_schedule(self):
        due_date = (timezone.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        with patch('api.tasks.send_task_notification.apply_async') as mock_apply:
            response = self.client.post('/api/tasks/create/',
                json.dumps({
                    'telegram_id': self.user.telegram_id,
                    'title': 'API task',
                    'due_date': due_date,
                    'tags': []
                }),
                content_type='application/json')
            self.assertEqual(response.status_code, 200)
            # assert apply_async was called once
            self.assertTrue(mock_apply.called)


class CeleryTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(telegram_id=333, username='celery')
        self.task = Task.objects.create(user=self.user, title='to notify', status='pending')

    @patch('requests.post')
    def test_send_task_notification_success(self, mock_post):
        # simulate successful Telegram API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        from api.tasks import send_task_notification

        result = send_task_notification(self.task.id)
        self.task.refresh_from_db()
        self.assertTrue(self.task.notified or self.task.status == 'completed')
