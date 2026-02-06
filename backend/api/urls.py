from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register),
    path('tasks/', views.get_tasks),
    path('tasks/create/', views.create_task),
    path('tasks/delete/', views.delete_task),
    path('archive/', views.get_archive),
    path('tags/', views.get_tags),
    path('tags/create/', views.create_tag),
    path('tags/delete/', views.delete_tag),
    path('clear/', views.clear_all),
    path('notify/', views.notify),
]
