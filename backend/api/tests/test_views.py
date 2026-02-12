"""
API endpoint integration tests.
"""

import json

from django.test import Client, TestCase

from api.models import Tag, Task, User


class APITestMixin:
    """Mixin with common test utilities."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create(telegram_id=123456789, username="testuser")
        self.api_key_header = {"HTTP_X_API_KEY": "test-api-key"}

    def post_json(self, url, data):
        """Helper method to POST JSON data."""
        return self.client.post(url, json.dumps(data), content_type="application/json", **self.api_key_header)

    def get_json(self, url, params=None):
        """Helper method to GET with query params."""
        return self.client.get(url, params, **self.api_key_header)


class RegisterViewTest(APITestMixin, TestCase):
    """Test suite for register endpoint."""

    def test_register_new_user(self):
        """Test registering a new user."""
        data = {"telegram_id": 987654321, "username": "newuser"}
        response = self.post_json("/api/register/", data)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["telegram_id"], 987654321)
        self.assertEqual(response_data["username"], "newuser")

        # Verify user created in database
        self.assertTrue(User.objects.filter(telegram_id=987654321).exists())

    def test_register_existing_user(self):
        """Test registering existing user returns same user."""
        data = {"telegram_id": self.user.telegram_id, "username": "updated"}
        response = self.post_json("/api/register/", data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)


class TagViewTest(APITestMixin, TestCase):
    """Test suite for tag endpoints."""

    def test_create_tag(self):
        """Test creating a tag."""
        data = {"telegram_id": self.user.telegram_id, "name": "work"}
        response = self.post_json("/api/tags/create/", data)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["name"], "work")
        self.assertIn("id", response_data)

    def test_get_tags(self):
        """Test getting user tags."""
        Tag.objects.create(user=self.user, name="work")
        Tag.objects.create(user=self.user, name="home")

        response = self.get_json("/api/tags/", {"telegram_id": self.user.telegram_id})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tags", data)
        self.assertEqual(len(data["tags"]), 2)

    def test_delete_tag(self):
        """Test deleting a tag."""
        tag = Tag.objects.create(user=self.user, name="work")
        data = {"telegram_id": self.user.telegram_id, "tag_id": tag.id}

        response = self.post_json("/api/tags/delete/", data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_create_tag_validation_error(self):
        """Test tag creation with empty name fails."""
        data = {"telegram_id": self.user.telegram_id, "name": ""}
        response = self.post_json("/api/tags/create/", data)

        self.assertEqual(response.status_code, 400)


class TaskViewTest(APITestMixin, TestCase):
    """Test suite for task endpoints."""

    def test_create_task(self):
        """Test creating a task."""
        data = {"telegram_id": self.user.telegram_id, "title": "Test task", "tags": []}
        response = self.post_json("/api/tasks/create/", data)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["title"], "Test task")
        self.assertEqual(response_data["status"], "pending")
        self.assertIn("id", response_data)

    def test_create_task_with_tags(self):
        """Test creating a task with tags."""
        Tag.objects.create(user=self.user, name="work")

        data = {
            "telegram_id": self.user.telegram_id,
            "title": "Task with tags",
            "tags": ["work"],
        }
        response = self.post_json("/api/tasks/create/", data)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify task has tag
        task = Task.objects.get(id=response_data["id"])
        self.assertEqual(task.tags.count(), 1)

    def test_get_tasks(self):
        """Test getting user tasks."""
        Task.objects.create(user=self.user, title="Task 1", status="pending")
        Task.objects.create(user=self.user, title="Task 2", status="pending")

        response = self.get_json("/api/tasks/", {"telegram_id": self.user.telegram_id})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tasks", data)
        self.assertEqual(len(data["tasks"]), 2)

    def test_delete_task(self):
        """Test deleting a task."""
        task = Task.objects.create(user=self.user, title="Test task")
        data = {"telegram_id": self.user.telegram_id, "task_id": task.id}

        response = self.post_json("/api/tasks/delete/", data)

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "deleted")

    def test_get_archive(self):
        """Test getting archive tasks."""
        Task.objects.create(user=self.user, title="Task 1", status="completed")
        Task.objects.create(user=self.user, title="Task 2", status="deleted")
        Task.objects.create(user=self.user, title="Task 3", status="pending")

        response = self.get_json("/api/archive/", {"telegram_id": self.user.telegram_id})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tasks", data)
        self.assertEqual(len(data["tasks"]), 2)

    def test_create_task_validation_error(self):
        """Test task creation with empty title fails."""
        data = {"telegram_id": self.user.telegram_id, "title": "", "tags": []}
        response = self.post_json("/api/tasks/create/", data)

        self.assertEqual(response.status_code, 400)


class ClearAllViewTest(APITestMixin, TestCase):
    """Test suite for clear all endpoint."""

    def test_clear_all_data(self):
        """Test clearing all user data."""
        Tag.objects.create(user=self.user, name="work")
        Task.objects.create(user=self.user, title="Task 1")
        Task.objects.create(user=self.user, title="Task 2")

        data = {"telegram_id": self.user.telegram_id}
        response = self.post_json("/api/clear/", data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tag.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)


class APIKeyMiddlewareTest(TestCase):
    """Test suite for API key middleware."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create(telegram_id=123456789)

    def test_api_key_required(self):
        """Test that API key is required."""
        data = {"telegram_id": self.user.telegram_id, "name": "work"}
        response = self.client.post("/api/tags/create/", json.dumps(data), content_type="application/json")

        self.assertEqual(response.status_code, 401)

    def test_api_key_valid(self):
        """Test that valid API key allows access."""
        data = {"telegram_id": self.user.telegram_id, "name": "work"}
        response = self.client.post(
            "/api/tags/create/",
            json.dumps(data),
            content_type="application/json",
            HTTP_X_API_KEY="test-api-key",
        )

        self.assertEqual(response.status_code, 200)
