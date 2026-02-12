from django.conf import settings
from django.db import transaction

from ..models import Tag, User


class TagService:
    @staticmethod
    def get_tags_for_user(user: User):
        return Tag.objects.filter(user=user).order_by("name")

    @staticmethod
    def create_tag(user: User, name: str) -> Tag:
        if Tag.objects.filter(user=user).count() >= settings.MAX_TAGS_PER_USER:
            raise ValueError(f"Лимит тегов: {settings.MAX_TAGS_PER_USER}")

        name = name.strip()
        if not name:
            raise ValueError("Name is required")

        if Tag.objects.filter(user=user, name=name).exists():
            raise ValueError("Tag already exists")

        return Tag.objects.create(user=user, name=name)

    @staticmethod
    def delete_tag(user: User, tag_id: int):
        deleted = Tag.objects.filter(id=tag_id, user=user).delete()
        if deleted[0] == 0:
            raise Tag.DoesNotExist("Tag not found")
