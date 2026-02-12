"""
Model tests for User, Task, and Tag models.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from api.models import User, Task, Tag


class UserModelTest(TestCase):
    """Test suite for User model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create(
            telegram_id=123456789,
            username='testuser'
        )

    def test_user_creation(self):
        """Test user can be created with telegram_id and username."""
        self.assertEqual(self.user.telegram_id, 123456789)
        self.assertEqual(self.user.username, 'testuser')
        self.assertIsNotNone(self.user.pk)

    def test_user_str_representation(self):
        """Test user string representation."""
        self.assertIn(str(self.user.telegram_id), str(self.user))


class TagModelTest(TestCase):
    """Test suite for Tag model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create(telegram_id=123456789)
        self.tag = Tag.objects.create(user=self.user, name='work')

    def test_tag_creation(self):
        """Test tag can be created with user and name."""
        self.assertEqual(self.tag.name, 'work')
        self.assertEqual(self.tag.user, self.user)
        self.assertIsNotNone(self.tag.id)

    def test_tag_str_representation(self):
        """Test tag string representation."""
        self.assertIn('work', str(self.tag))

    def test_tag_ordering(self):
        """Test tags are ordered by name."""
        tag2 = Tag.objects.create(user=self.user, name='home')
        tag3 = Tag.objects.create(user=self.user, name='urgent')
        
        tags = Tag.objects.filter(user=self.user).all()
        self.assertEqual(list(tags), [tag2, tag3, self.tag])  # home, urgent, work


class TaskModelTest(TestCase):
    """Test suite for Task model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create(telegram_id=123456789)
        self.tag = Tag.objects.create(user=self.user, name='work')

    def test_task_creation_minimal(self):
        """Test task can be created with minimal required fields."""
        task = Task.objects.create(
            user=self.user,
            title='Test task'
        )
        self.assertEqual(task.title, 'Test task')
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.status, 'pending')
        self.assertIsNotNone(task.created_at)

    def test_task_creation_with_tags(self):
        """Test task can be created with tags."""
        task = Task.objects.create(
            user=self.user,
            title='Test task'
        )
        task.tags.add(self.tag)
        
        self.assertEqual(task.tags.count(), 1)
        self.assertEqual(task.tags.first(), self.tag)

    def test_task_creation_with_due_date(self):
        """Test task can be created with due date."""
        due_date = timezone.now() + timedelta(days=1)
        task = Task.objects.create(
            user=self.user,
            title='Test task',
            due_date=due_date
        )
        self.assertEqual(task.due_date, due_date)

    def test_task_status_choices(self):
        """Test task status can be updated to valid choices."""
        task = Task.objects.create(user=self.user, title='Test')
        
        task.status = 'completed'
        task.save()
        self.assertEqual(task.status, 'completed')
        
        task.status = 'deleted'
        task.save()
        self.assertEqual(task.status, 'deleted')

    def test_task_str_representation(self):
        """Test task string representation."""
        task = Task.objects.create(user=self.user, title='Test task')
        self.assertIn('Test task', str(task))
