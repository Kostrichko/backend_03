from aiogram import Dispatcher, F
from aiogram.filters import Command

from .common import cmd_start
from .tags import (
    CreateTagState,
    cmd_create_tag,
    cmd_delete_tag_confirm,
    cmd_delete_tag_start,
    cmd_list_tags,
    cmd_new_tag_start,
    handle_create_tag_ask,
    handle_delete_tag_list,
    process_tag_name,
)
from .tasks import (
    CreateTaskState,
    cmd_archive,
    cmd_delete_task_confirm,
    cmd_delete_task_start,
    cmd_list_tasks,
    cmd_new_task,
    finish_tag_selection,
    process_notify_time,
    process_task_title,
    skip_tag_selection,
    toggle_tag_selection,
)


def register_handlers(dp: Dispatcher):
    # Common
    dp.message.register(cmd_start, Command("start"))

    # Tasks
    dp.message.register(cmd_new_task, Command("new"))
    dp.message.register(cmd_new_task, F.text == "➕ Новая задача")
    dp.message.register(cmd_list_tasks, Command("list"))
    dp.message.register(cmd_list_tasks, F.text == "📋 Мои задачи")
    dp.message.register(cmd_archive, Command("archive"))
    dp.message.register(cmd_archive, F.text == "📦 Архив")
    dp.message.register(cmd_delete_task_start, Command("delete_task"))
    dp.message.register(cmd_delete_task_start, F.text == "🗑 Удалить задачу")

    # Task FSM
    dp.message.register(process_task_title, CreateTaskState.title)
    dp.callback_query.register(
        process_notify_time, CreateTaskState.notify_time, F.data.startswith("notify_")
    )
    dp.callback_query.register(
        toggle_tag_selection, CreateTaskState.tags, F.data.startswith("tag_")
    )
    dp.callback_query.register(
        finish_tag_selection, CreateTaskState.tags, F.data == "tags_done"
    )
    dp.callback_query.register(
        skip_tag_selection, CreateTaskState.tags, F.data == "tags_skip"
    )
    dp.callback_query.register(cmd_delete_task_confirm, F.data.startswith("del_task_"))

    # Tags
    dp.message.register(cmd_list_tags, Command("tags"))
    dp.message.register(cmd_list_tags, F.text == "🏷 Теги")
    dp.message.register(cmd_new_tag_start, F.text == "➕ Новый тег")
    dp.message.register(cmd_create_tag, Command("tag"))
    dp.message.register(cmd_delete_tag_start, Command("delete_tag"))

    # Tag FSM
    dp.message.register(process_tag_name, CreateTagState.name)
    dp.callback_query.register(cmd_delete_tag_confirm, F.data.startswith("del_tag_"))
    dp.callback_query.register(handle_create_tag_ask, F.data == "create_tag_ask")
    dp.callback_query.register(handle_delete_tag_list, F.data == "delete_tag_list")
