from django.db import models
from django.utils import timezone


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True, primary_key=True)
    username = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"User {self.telegram_id}"


class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'tags'
        unique_together = [['user', 'name']]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.user.telegram_id})"


class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks')
    status = models.CharField(max_length=10, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    notified = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['due_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'due_date', 'notified']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.status})"

