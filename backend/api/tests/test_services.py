"""
Service layer tests for UserService, TagService, and TaskService.
"""
from django.test import TestCase
from api.models import User, Task, Tag
from api.services import UserService, TagService, TaskService


class UserServiceTest(TestCase):
    """Test suite for UserService."""

    def test_get_or_create_user_creates_new(self):
        """Test get_or_create_user creates new user."""
        user = UserService.get_or_create_user(123456789, 'testuser')
        
        self.assertEqual(user.telegram_id, 123456789)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(User.objects.count(), 1)

    def test_get_or_create_user_returns_existing(self):
        """Test get_or_create_user returns existing user."""
        user1 = UserService.get_or_create_user(123456789, 'testuser')
        user2 = UserService.get_or_create_user(123456789, 'testuser')
        
        self.assertEqual(user1.pk, user2.pk)
        self.assertEqual(User.objects.count(), 1)


class TagServiceTest(TestCase):
    """Test suite for TagService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create(telegram_id=123456789)

    def test_create_tag(self):
        """Test tag creation."""
        tag = TagService.create_tag(self.user, 'work')
        
        self.assertEqual(tag.name, 'work')
        self.assertEqual(tag.user, self.user)
        self.assertEqual(Tag.objects.count(), 1)

    def test_create_tag_duplicate_raises_error(self):
        """Test creating duplicate tag raises error."""
        TagService.create_tag(self.user, 'work')
        
        with self.assertRaises(ValueError):
            TagService.create_tag(self.user, 'work')

    def test_create_tag_limit_exceeded(self):
        """Test tag creation fails when limit exceeded."""
        for i in range(4):
            TagService.create_tag(self.user, f'tag{i}')
        
        with self.assertRaises(ValueError) as cm:
            TagService.create_tag(self.user, 'tag5')
        
        self.assertIn('Лимит тегов', str(cm.exception))

    def test_get_tags_for_user(self):
        """Test getting tags for user."""
        tag1 = TagService.create_tag(self.user, 'work')
        tag2 = TagService.create_tag(self.user, 'home')
        
        tags = TagService.get_tags_for_user(self.user)
        
        self.assertEqual(len(tags), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_delete_tag(self):
        """Test tag deletion."""
        tag = TagService.create_tag(self.user, 'work')
        
        TagService.delete_tag(self.user, tag.id)
        
        self.assertEqual(Tag.objects.count(), 0)

    def test_delete_nonexistent_tag_raises_error(self):
        """Test deleting non-existent tag raises error."""
        with self.assertRaises(Tag.DoesNotExist):
            TagService.delete_tag(self.user, 999)


class TaskServiceTest(TestCase):
    """Test suite for TaskService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create(telegram_id=123456789)

    def test_create_task(self):
        """Test task creation."""
        task = TaskService.create_task(self.user, 'Test task')
        
        self.assertEqual(task.title, 'Test task')
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.status, 'pending')

    def test_create_task_with_tags(self):
        """Test task creation with tags."""
        TagService.create_tag(self.user, 'work')
        
        task = TaskService.create_task(self.user, 'Test task', tag_names=['work'])
        
        self.assertEqual(task.tags.count(), 1)
        self.assertEqual(task.tags.first().name, 'work')

    def test_create_task_limit_exceeded(self):
        """Test task creation fails when limit exceeded."""
        for i in range(6):
            TaskService.create_task(self.user, f'Task {i}')
        
        with self.assertRaises(ValueError) as cm:
            TaskService.create_task(self.user, 'Task 7')
        
        self.assertIn('Лимит задач', str(cm.exception))

    def test_get_pending_tasks_for_user(self):
        """Test getting pending tasks."""
        task1 = TaskService.create_task(self.user, 'Task 1')
        task2 = TaskService.create_task(self.user, 'Task 2')
        
        # Create completed task (should not be in pending)
        task3 = TaskService.create_task(self.user, 'Task 3')
        TaskService.complete_task(self.user, task3.id)
        
        pending_tasks = TaskService.get_pending_tasks_for_user(self.user)
        
        self.assertEqual(len(pending_tasks), 2)
        self.assertIn(task1, pending_tasks)
        self.assertIn(task2, pending_tasks)

    def test_get_archive_tasks_for_user(self):
        """Test getting archive tasks."""
        task1 = TaskService.create_task(self.user, 'Task 1')
        TaskService.complete_task(self.user, task1.id)
        
        task2 = TaskService.create_task(self.user, 'Task 2')
        TaskService.delete_task(self.user, task2.id)
        
        # Pending task should not be in archive
        TaskService.create_task(self.user, 'Task 3')
        
        archive_tasks = TaskService.get_archive_tasks_for_user(self.user)
        
        self.assertEqual(len(archive_tasks), 2)

    def test_complete_task(self):
        """Test task completion."""
        task = TaskService.create_task(self.user, 'Test task')
        
        TaskService.complete_task(self.user, task.id)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'completed')

    def test_delete_task(self):
        """Test task deletion (marks as deleted)."""
        task = TaskService.create_task(self.user, 'Test task')
        
        TaskService.delete_task(self.user, task.id)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'deleted')

    def test_clear_all_tasks_and_tags(self):
        """Test clearing all user data."""
        TagService.create_tag(self.user, 'work')
        TaskService.create_task(self.user, 'Task 1')
        TaskService.create_task(self.user, 'Task 2')
        
        TaskService.clear_all_tasks_and_tags(self.user)
        
        self.assertEqual(Tag.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)
