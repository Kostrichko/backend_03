from ..models import Tag, User
from django.db import transaction


class TagService:
    @staticmethod
    def get_tags_for_user(user: User):
        """Get all tags for a user"""
        return Tag.objects.filter(user=user).order_by('name')

    @staticmethod
    def create_tag(user: User, name: str) -> Tag:
        """Create a new tag for user"""
        if Tag.objects.filter(user=user).count() >= 4:
            raise ValueError("Лимит тегов: 4")

        name = name.strip()
        if not name:
            raise ValueError("Name is required")

        if Tag.objects.filter(user=user, name=name).exists():
            raise ValueError("Tag already exists")

        return Tag.objects.create(user=user, name=name)

    @staticmethod
    def delete_tag(user: User, tag_id: int):
        """Delete a tag by id for user"""
        deleted = Tag.objects.filter(id=tag_id, user=user).delete()
        if deleted[0] == 0:
            raise Tag.DoesNotExist("Tag not found")