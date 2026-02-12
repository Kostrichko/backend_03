import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django_ratelimit.decorators import ratelimit
from rest_framework.exceptions import ValidationError as DRFValidationError

from . import tasks
from .models import Tag, Task, User
from .serializers import (
    ClearAllSerializer,
    RegisterSerializer,
    TagActionSerializer,
    TagCreateSerializer,
    TagSerializer,
    TaskActionSerializer,
    TaskCreateSerializer,
    TaskSerializer,
    UserSerializer,
)
from .services import TagService, TaskService, UserService


def json_response(func):
    """Decorator for handling JSON requests and errors"""

    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except (ValidationError, DRFValidationError) as e:
            return JsonResponse({"error": str(e)}, status=400)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        except Task.DoesNotExist:
            return JsonResponse({"error": "Task not found"}, status=404)
        except Tag.DoesNotExist:
            return JsonResponse({"error": "Tag not found"}, status=404)
        except Exception as e:
            import traceback

            traceback.print_exc()
            return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

    return wrapper


def get_user(telegram_id):
    """Get or create user by telegram_id"""
    return UserService.get_or_create_user(int(telegram_id))


@csrf_exempt
@ratelimit(key="ip", rate="10/m", method="POST")
@json_response
def register(request):
    serializer = RegisterSerializer(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)

    user = get_user(serializer.validated_data["telegram_id"])
    if serializer.validated_data.get("username"):
        user.username = serializer.validated_data["username"]
        user.save()

    user_serializer = UserSerializer(user)
    return JsonResponse(user_serializer.data)


@csrf_exempt
@ratelimit(key="ip", rate="30/m", method="GET")
@json_response
def get_tasks(request):
    user = get_user(request.GET["telegram_id"])
    tasks = TaskService.get_pending_tasks_for_user(user)

    serializer = TaskSerializer(tasks, many=True)
    return JsonResponse({"tasks": serializer.data})


@csrf_exempt
@ratelimit(key="ip", rate="10/m", method="POST")
@json_response
@transaction.atomic
def create_task(request):
    serializer = TaskCreateSerializer(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)

    user = get_user(serializer.validated_data["telegram_id"])

    task = TaskService.create_task(
        user=user,
        title=serializer.validated_data["title"],
        due_date_str=serializer.validated_data.get("due_date"),
        tag_names=serializer.validated_data.get("tags", []),
    )

    if task.due_date:
        tasks.send_task_notification.apply_async(args=[task.id], eta=task.due_date)

    task_serializer = TaskSerializer(task)
    return JsonResponse(task_serializer.data)


@csrf_exempt
@ratelimit(key="ip", rate="30/m", method="GET")
@json_response
def get_tags(request):
    user = get_user(request.GET["telegram_id"])
    tags = TagService.get_tags_for_user(user)
    serializer = TagSerializer(tags, many=True)
    return JsonResponse({"tags": serializer.data})


@csrf_exempt
@ratelimit(key="ip", rate="10/m", method="POST")
@json_response
@transaction.atomic
def create_tag(request):
    serializer = TagCreateSerializer(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)

    user = get_user(serializer.validated_data["telegram_id"])
    tag = TagService.create_tag(user=user, name=serializer.validated_data["name"])

    tag_serializer = TagSerializer(tag)
    return JsonResponse(tag_serializer.data)


@csrf_exempt
@ratelimit(key="ip", rate="20/m", method="GET")
@json_response
def get_archive(request):
    user = get_user(request.GET["telegram_id"])
    tasks = TaskService.get_archive_tasks_for_user(user)

    serializer = TaskSerializer(tasks, many=True)
    return JsonResponse({"tasks": serializer.data})


@csrf_exempt
@ratelimit(key="ip", rate="10/m", method="POST")
@json_response
@transaction.atomic
def complete_task(request):
    serializer = TaskActionSerializer(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)

    user = get_user(serializer.validated_data["telegram_id"])
    TaskService.complete_task(user=user, task_id=serializer.validated_data["task_id"])
    return JsonResponse({"status": "ok"})


@csrf_exempt
@ratelimit(key="ip", rate="10/m", method="POST")
@json_response
@transaction.atomic
def delete_task(request):
    serializer = TaskActionSerializer(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)

    user = get_user(serializer.validated_data["telegram_id"])
    TaskService.delete_task(user=user, task_id=serializer.validated_data["task_id"])
    return JsonResponse({"status": "ok"})


@csrf_exempt
@ratelimit(key="ip", rate="10/m", method="POST")
@json_response
@transaction.atomic
def delete_tag(request):
    serializer = TagActionSerializer(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)

    user = get_user(serializer.validated_data["telegram_id"])
    TagService.delete_tag(user=user, tag_id=serializer.validated_data["tag_id"])
    return JsonResponse({"status": "ok"})


@csrf_exempt
@ratelimit(key="ip", rate="5/m", method="POST")
@json_response
@transaction.atomic
def clear_all(request):
    serializer = ClearAllSerializer(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)

    user = get_user(serializer.validated_data["telegram_id"])
    TaskService.clear_all_tasks_and_tags(user=user)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def notify(request):
    """Endpoint для приема уведомлений от Celery"""
    data = json.loads(request.body)
    return JsonResponse({"status": "received"})
