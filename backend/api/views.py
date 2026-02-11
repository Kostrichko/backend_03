from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django_ratelimit.decorators import ratelimit
import json
from .models import User, Task, Tag
from . import tasks


def json_response(func):
    """Decorator for handling JSON requests and errors"""
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
        except Tag.DoesNotExist:
            return JsonResponse({'error': 'Tag not found'}, status=404)
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'Server error'}, status=500)
    return wrapper


def get_user(telegram_id):
    """Get or create user by telegram_id"""
    user, _ = User.objects.get_or_create(
        telegram_id=int(telegram_id),
        defaults={'username': ''}
    )
    return user


@csrf_exempt
@ratelimit(key='ip', rate='10/m', method='POST')
@json_response
def register(request):
    data = json.loads(request.body)
    user = get_user(data['telegram_id'])
    if data.get('username'):
        user.username = data['username']
        user.save()
    return JsonResponse({'telegram_id': user.telegram_id})


@csrf_exempt
@ratelimit(key='ip', rate='30/m', method='GET')
@json_response
def get_tasks(request):
    user = get_user(request.GET['telegram_id'])
    tasks = Task.objects.filter(
        user=user,
        status='pending'
    ).prefetch_related('tags').order_by('due_date', '-created_at')
    
    return JsonResponse({
        'tasks': [{
            'id': t.id,
            'title': t.title,
            'tags': [tag.name for tag in t.tags.all()],
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M'),
            'due_date': t.due_date.strftime('%Y-%m-%d %H:%M:%S') if t.due_date else None
        } for t in tasks]
    })


@csrf_exempt
@ratelimit(key='ip', rate='10/m', method='POST')
@json_response
@transaction.atomic
def create_task(request):
    data = json.loads(request.body)
    user = get_user(data['telegram_id'])
    
    if Task.objects.filter(user=user, status='pending').count() >= 6:
        return JsonResponse({'error': 'Лимит задач: 6'}, status=400)
    
    if not data.get('title', '').strip():
        return JsonResponse({'error': 'Title is required'}, status=400)
    
    due_date_str = data.get('due_date')
    due_date = parse_datetime(due_date_str) if due_date_str else None
    
    task = Task.objects.create(
        user=user,
        title=data['title'].strip(),
        due_date=due_date
    )
    
    if tag_names := data.get('tags', []):
        tags = Tag.objects.filter(user=user, name__in=tag_names)
        task.tags.set(tags)
    
    if due_date:
        tasks.send_task_notification.apply_async(
            args=[task.id],
            eta=due_date
        )
    
    return JsonResponse({'id': task.id, 'title': task.title})


@csrf_exempt
@ratelimit(key='ip', rate='30/m', method='GET')
@json_response
def get_tags(request):
    user = get_user(request.GET['telegram_id'])
    tags = Tag.objects.filter(user=user).order_by('name')
    return JsonResponse({
        'tags': [{'id': t.id, 'name': t.name} for t in tags]
    })


@csrf_exempt
@ratelimit(key='ip', rate='10/m', method='POST')
@json_response
@transaction.atomic
def create_tag(request):
    data = json.loads(request.body)
    user = get_user(data['telegram_id'])
    
    if Tag.objects.filter(user=user).count() >= 4:
        return JsonResponse({'error': 'Лимит тегов: 4'}, status=400)
    
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    if Tag.objects.filter(user=user, name=name).exists():
        return JsonResponse({'error': 'Tag already exists'}, status=400)
    
    tag = Tag.objects.create(user=user, name=name)
    return JsonResponse({'id': tag.id, 'name': tag.name})


@csrf_exempt
@ratelimit(key='ip', rate='20/m', method='GET')
@json_response
def get_archive(request):
    user = get_user(request.GET['telegram_id'])
    tasks = Task.objects.filter(
        user=user,
        status__in=['completed', 'deleted']
    ).prefetch_related('tags').order_by('-created_at')[:5]
    
    return JsonResponse({
        'tasks': [{
            'id': t.id,
            'title': t.title,
            'tags': [tag.name for tag in t.tags.all()],
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M'),
            'status': t.status
        } for t in tasks]
    })


@csrf_exempt
@json_response
@transaction.atomic
def complete_task(request):
    data = json.loads(request.body)
    user = get_user(data['telegram_id'])
    task = Task.objects.get(id=data['task_id'], user=user)
    task.status = 'completed'
    task.save(update_fields=['status'])
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@ratelimit(key='ip', rate='10/m', method='POST')
@json_response
@transaction.atomic
def delete_task(request):
    data = json.loads(request.body)
    user = get_user(data['telegram_id'])
    task = Task.objects.get(id=data['task_id'], user=user)
    task.status = 'deleted'
    task.save(update_fields=['status'])
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@ratelimit(key='ip', rate='10/m', method='POST')
@json_response
@transaction.atomic
def delete_tag(request):
    data = json.loads(request.body)
    user = get_user(data['telegram_id'])
    deleted = Tag.objects.filter(id=data['tag_id'], user=user).delete()
    if deleted[0] == 0:
        raise Tag.DoesNotExist
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@ratelimit(key='ip', rate='5/m', method='POST')
@json_response
@transaction.atomic
def clear_all(request):
    data = json.loads(request.body)
    user = get_user(data['telegram_id'])
    Task.objects.filter(user=user).delete()
    Tag.objects.filter(user=user).delete()
    return JsonResponse({'status': 'ok'})


@csrf_exempt
def notify(request):
    """Endpoint для приема уведомлений от Celery"""
    data = json.loads(request.body)
    return JsonResponse({'status': 'received'})

