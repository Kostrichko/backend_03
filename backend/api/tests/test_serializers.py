"""
Serializer validation tests.
"""

from django.test import TestCase

from api.models import Tag, Task, User
from api.serializers import (
    ClearAllSerializer,
    RegisterSerializer,
    TagActionSerializer,
    TagCreateSerializer,
    TagSerializer,
    TaskActionSerializer,
    TaskCreateSerializer,
    TaskSerializer,
    UserSerializer,)


class UserSerializerTest(TestCase):
    """Test suite for UserSerializer."""

    def test_user_serializer(self):
        """Test UserSerializer serializes user data correctly."""
        user = User.objects.create(telegram_id=123456789, username="testuser")
        serializer = UserSerializer(user)

        self.assertEqual(serializer.data["telegram_id"], 123456789)
        self.assertEqual(serializer.data["username"], "testuser")


class TagSerializerTest(TestCase):
    """Test suite for TagSerializer."""

    def test_tag_serializer(self):
        """Test TagSerializer serializes tag data correctly."""
        user = User.objects.create(telegram_id=123456789)
        tag = Tag.objects.create(user=user, name="work")
        serializer = TagSerializer(tag)

        self.assertEqual(serializer.data["id"], tag.id)
        self.assertEqual(serializer.data["name"], "work")


class TaskSerializerTest(TestCase):
    """Test suite for TaskSerializer."""

    def test_task_serializer(self):
        """Test TaskSerializer serializes task data correctly."""
        user = User.objects.create(telegram_id=123456789)
        task = Task.objects.create(user=user, title="Test task", status="pending")
        serializer = TaskSerializer(task)

        self.assertEqual(serializer.data["title"], "Test task")
        self.assertEqual(serializer.data["status"], "pending")
        self.assertIn("id", serializer.data)
        self.assertIn("created_at", serializer.data)


class RegisterSerializerTest(TestCase):
    """Test suite for RegisterSerializer."""

    def test_register_serializer_valid_with_username(self):
        """Test RegisterSerializer with valid data including username."""
        data = {"telegram_id": 123456789, "username": "testuser"}
        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["telegram_id"], 123456789)
        self.assertEqual(serializer.validated_data["username"], "testuser")

    def test_register_serializer_valid_without_username(self):
        """Test RegisterSerializer with valid data without username."""
        data = {"telegram_id": 123456789}
        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["telegram_id"], 123456789)


class TagCreateSerializerTest(TestCase):
    """Test suite for TagCreateSerializer."""

    def test_tag_create_serializer_valid(self):
        """Test TagCreateSerializer with valid data."""
        data = {"telegram_id": 123456789, "name": "work"}
        serializer = TagCreateSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["name"], "work")

    def test_tag_create_serializer_empty_name(self):
        """Test TagCreateSerializer rejects empty name."""
        data = {"telegram_id": 123456789, "name": ""}
        serializer = TagCreateSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)


class TaskCreateSerializerTest(TestCase):
    """Test suite for TaskCreateSerializer."""

    def test_task_create_serializer_valid(self):
        """Test TaskCreateSerializer with valid data."""
        data = {"telegram_id": 123456789, "title": "Test task", "tags": []}
        serializer = TaskCreateSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["title"], "Test task")

    def test_task_create_serializer_empty_title(self):
        """Test TaskCreateSerializer rejects empty title."""
        data = {"telegram_id": 123456789, "title": "", "tags": []}
        serializer = TaskCreateSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_task_create_serializer_with_tags(self):
        """Test TaskCreateSerializer with tags."""
        data = {
            "telegram_id": 123456789,
            "title": "Test task",
            "tags": ["work", "urgent"]}
        
        serializer = TaskCreateSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(len(serializer.validated_data["tags"]), 2)


class TaskActionSerializerTest(TestCase):
    """Test suite for TaskActionSerializer."""

    def test_task_action_serializer_valid(self):
        """Test TaskActionSerializer with valid data."""
        data = {"telegram_id": 123456789, "task_id": 1}
        serializer = TaskActionSerializer(data=data)

        self.assertTrue(serializer.is_valid())


class TagActionSerializerTest(TestCase):
    """Test suite for TagActionSerializer."""

    def test_tag_action_serializer_valid(self):
        """Test TagActionSerializer with valid data."""
        data = {"telegram_id": 123456789, "tag_id": 1}
        serializer = TagActionSerializer(data=data)

        self.assertTrue(serializer.is_valid())


class ClearAllSerializerTest(TestCase):
    """Test suite for ClearAllSerializer."""

    def test_clear_all_serializer_valid(self):
        """Test ClearAllSerializer with valid data."""
        data = {"telegram_id": 123456789}
        serializer = ClearAllSerializer(data=data)

        self.assertTrue(serializer.is_valid())
