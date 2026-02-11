from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from .models import User, Tag, Task
import json


class IntegrationStressTest(TestCase):
    """Full-cycle integration test: create many tags/tasks, duplicates, deletions.

    Checks:
    - No 5xx responses from API
    - DB remains consistent (no duplicate tags by name per user)
    - Tasks have valid statuses after operations
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(telegram_id=99999, username='integration')

    @patch('requests.post')
    def test_full_cycle_stress(self, mock_post):
        # Mock Telegram API to always succeed
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        # 1) Mass-create tags (attempt more than typical limit)
        created_tag_names = set()
        for i in range(20):
            name = f"tag_{i % 10}"  # intentionally create duplicates
            resp = self.client.post('/api/tags/create/',
                json.dumps({'telegram_id': self.user.telegram_id, 'name': name}),
                content_type='application/json')
            # Ensure no 5xx
            self.assertLess(resp.status_code, 500, msg=f"Tag create returned {resp.status_code}")
            if resp.status_code == 200:
                created_tag_names.add(name)

        # Verify DB has at most one tag per unique name per user
        tags = Tag.objects.filter(user=self.user)
        names_in_db = set(t.name for t in tags)
        self.assertEqual(names_in_db, created_tag_names)

        # 2) Create many tasks with combinations of tags and due_dates
        created_task_ids = []
        for i in range(100):
            title = f"Task {i}"
            # randomly attach tags by cycling
            tags_list = list(names_in_db)[: (i % (len(names_in_db) or 1))]
            due = None
            if i % 7 == 0:
                due = (timezone.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')

            payload = {
                'telegram_id': self.user.telegram_id,
                'title': title,
                'tags': tags_list,
            }
            if due:
                payload['due_date'] = due

            resp = self.client.post('/api/tasks/create/', json.dumps(payload), content_type='application/json')
            self.assertLess(resp.status_code, 500, msg=f"Task create returned {resp.status_code}")
            if resp.status_code == 200:
                created_task_ids.append(resp.json().get('id') or '')

        # 3) Get tasks list and ensure no server error and statuses valid
        resp = self.client.get(f'/api/tasks/?telegram_id={self.user.telegram_id}')
        self.assertLess(resp.status_code, 500)
        data = resp.json()
        for t in data.get('tasks', []):
            self.assertIn(t.get('status'), ['pending', 'completed', 'deleted'])

        # 4) Attempt deletions on some tasks
        tasks_qs = Task.objects.filter(user=self.user)
        to_delete = list(tasks_qs[:10])
        for t in to_delete:
            resp = self.client.post('/api/tasks/delete/',
                json.dumps({'telegram_id': self.user.telegram_id, 'task_id': t.id}),
                content_type='application/json')
            self.assertLess(resp.status_code, 500)
            t.refresh_from_db()
            self.assertEqual(t.status, 'deleted')

        # 5) Clear all data via API
        resp = self.client.post('/api/clear/', json.dumps({'telegram_id': self.user.telegram_id}), content_type='application/json')
        self.assertLess(resp.status_code, 500)

        # Final: ensure no tasks and no tags for user
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Tag.objects.filter(user=self.user).count(), 0)
