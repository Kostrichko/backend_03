from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime

from ..models import Tag, Task, User


class TaskService:
    @staticmethod
    def get_pending_tasks_for_user(user: User):
        """Get pending tasks for user with tags"""
        return (
            Task.objects.filter(user=user, status="pending")
            .prefetch_related("tags")
            .order_by("due_date", "-created_at")
        )

    @staticmethod
    def get_archive_tasks_for_user(user: User):
        """Get completed/deleted tasks for user (last 5)"""
        return (
            Task.objects.filter(user=user, status__in=["completed", "deleted"])
            .prefetch_related("tags")
            .order_by("-created_at")[: settings.MAX_ARCHIVE_TASKS_PER_USER]
        )

    @staticmethod
    def create_task(
        user: User,
        title: str,
        due_date_str: str | None = None,
        tag_names: list[str] | None = None,
    ) -> Task:
        """Create a new task for user"""
        if (
            Task.objects.filter(user=user, status="pending").count()
            >= settings.MAX_PENDING_TASKS_PER_USER
        ):
            raise ValueError(f"Лимит задач: {settings.MAX_PENDING_TASKS_PER_USER}")

        # Validation moved to serializer
        due_date = parse_datetime(due_date_str) if due_date_str else None

        task = Task.objects.create(user=user, title=title, due_date=due_date)

        if tag_names:
            tags = Tag.objects.filter(user=user, name__in=tag_names)
            task.tags.set(tags)

        return task

    @staticmethod
    def complete_task(user: User, task_id: int):
        """Mark task as completed"""
        task = Task.objects.get(id=task_id, user=user)
        task.status = "completed"
        task.save(update_fields=["status"])

    @staticmethod
    def delete_task(user: User, task_id: int):
        """Mark task as deleted"""
        task = Task.objects.get(id=task_id, user=user)
        task.status = "deleted"
        task.save(update_fields=["status"])

    @staticmethod
    def clear_all_tasks_and_tags(user: User):
        """Delete all tasks and tags for user"""
        Task.objects.filter(user=user).delete()
        Tag.objects.filter(user=user).delete()
