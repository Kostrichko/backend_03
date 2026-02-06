from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from .models import User, Tag, Task
import json


class TagTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(telegram_id=123456789, username='testuser')

    def test_create_tag(self):
        response = self.client.post('/api/tags/create/',
            json.dumps({'telegram_id': self.user.telegram_id, 'name': 'work'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tag.objects.count(), 1)
        tag = Tag.objects.first()
        self.assertEqual(tag.name, 'work')
        self.assertEqual(tag.user, self.user)

    def test_create_duplicate_tag(self):
        Tag.objects.create(user=self.user, name='work')
        response = self.client.post('/api/tags/create/',
            json.dumps({'telegram_id': self.user.telegram_id, 'name': 'work'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_create_tag_limit(self):
        for i in range(4):
            Tag.objects.create(user=self.user, name=f'tag{i}')
        response = self.client.post('/api/tags/create/',
            json.dumps({'telegram_id': self.user.telegram_id, 'name': 'tag5'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_get_tags(self):
        Tag.objects.create(user=self.user, name='work')
        Tag.objects.create(user=self.user, name='home')
        response = self.client.get(f'/api/tags/?telegram_id={self.user.telegram_id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['tags']), 2)

    def test_delete_tag(self):
        tag = Tag.objects.create(user=self.user, name='work')
        response = self.client.post('/api/tags/delete/',
            json.dumps({'telegram_id': self.user.telegram_id, 'tag_id': tag.id}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tag.objects.count(), 0)


class TaskTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(telegram_id=123456789, username='testuser')
        self.tag1 = Tag.objects.create(user=self.user, name='work')
        self.tag2 = Tag.objects.create(user=self.user, name='urgent')

    def test_create_task(self):
        due_date = (timezone.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        response = self.client.post('/api/tasks/create/',
            json.dumps({
                'telegram_id': self.user.telegram_id,
                'title': 'Test task',
                'due_date': due_date,
                'tags': ['work']
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), 1)
        task = Task.objects.first()
        self.assertEqual(task.title, 'Test task')
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.tags.count(), 1)

    def test_create_task_limit(self):
        for i in range(6):
            Task.objects.create(user=self.user, title=f'Task {i}', status='pending')
        response = self.client.post('/api/tasks/create/',
            json.dumps({
                'telegram_id': self.user.telegram_id,
                'title': 'Task 7',
                'tags': []
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_get_tasks(self):
        Task.objects.create(user=self.user, title='Task 1', status='pending')
        Task.objects.create(user=self.user, title='Task 2', status='pending')
        Task.objects.create(user=self.user, title='Task 3', status='completed')
        response = self.client.get(f'/api/tasks/?telegram_id={self.user.telegram_id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['tasks']), 2)

    def test_delete_task(self):
        task = Task.objects.create(user=self.user, title='Task 1', status='pending')
        response = self.client.post('/api/tasks/delete/',
            json.dumps({'telegram_id': self.user.telegram_id, 'task_id': task.id}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, 'deleted')

    def test_get_archive(self):
        Task.objects.create(user=self.user, title='Task 1', status='completed')
        Task.objects.create(user=self.user, title='Task 2', status='deleted')
        Task.objects.create(user=self.user, title='Task 3', status='pending')
        response = self.client.get(f'/api/archive/?telegram_id={self.user.telegram_id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['tasks']), 2)

    def test_clear_all(self):
        Task.objects.create(user=self.user, title='Task 1', status='pending')
        Tag.objects.create(user=self.user, name='test')
        response = self.client.post('/api/clear/',
            json.dumps({'telegram_id': self.user.telegram_id}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Tag.objects.filter(user=self.user).count(), 0)

    def test_task_with_multiple_tags(self):
        response = self.client.post('/api/tasks/create/',
            json.dumps({
                'telegram_id': self.user.telegram_id,
                'title': 'Multi-tag task',
                'tags': ['work', 'urgent']
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        task = Task.objects.first()
        self.assertEqual(task.tags.count(), 2)
        tag_names = [tag.name for tag in task.tags.all()]
        self.assertIn('work', tag_names)
        self.assertIn('urgent', tag_names)


class TaskNotificationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(telegram_id=123456789, username='testuser')

    def test_task_notification_scheduling(self):
        due_date = (timezone.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        response = self.client.post('/api/tasks/create/',
            json.dumps({
                'telegram_id': self.user.telegram_id,
                'title': 'Notification task',
                'due_date': due_date,
                'tags': []
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        task = Task.objects.first()
        self.assertIsNotNone(task.due_date)
        self.assertFalse(task.notified)

    def test_task_without_notification(self):
        response = self.client.post('/api/tasks/create/',
            json.dumps({
                'telegram_id': self.user.telegram_id,
                'title': 'No notification task',
                'tags': []
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        task = Task.objects.first()
        self.assertIsNone(task.due_date)
        self.assertFalse(task.notified)

