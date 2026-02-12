from rest_framework import serializers

from .models import Tag, Task, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["telegram_id", "username"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class TaskSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(many=True, slug_field="name", queryset=Tag.objects.all(), required=False)

    class Meta:
        model = Task
        fields = ["id", "title", "status", "created_at", "due_date", "tags"]
        read_only_fields = ["id", "created_at", "status"]

    def create(self, validated_data):
        tags_data = validated_data.pop("tags", [])
        task = Task.objects.create(**validated_data)

        if tags_data:
            tags = Tag.objects.filter(user=validated_data["user"], name__in=[tag.name for tag in tags_data])
            task.tags.set(tags)

        return task


class TaskCreateSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=[])

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required")
        return value.strip()

    def validate_tags(self, value):
        if len(value) > 4:  # Assuming max 4 tags per task
            raise serializers.ValidationError("Too many tags")
        return value


class TagCreateSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    name = serializers.CharField(max_length=50)

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Name is required")
        return name


class RegisterSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    username = serializers.CharField(max_length=100, required=False, allow_blank=True)


class TaskActionSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    task_id = serializers.IntegerField()


class TagActionSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    tag_id = serializers.IntegerField()


class ClearAllSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
