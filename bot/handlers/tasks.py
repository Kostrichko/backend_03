from datetime import datetime, timedelta, timezone

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton

from config import (
    MAX_ARCHIVE_TASKS_PER_USER,
    MAX_PENDING_TASKS_PER_USER,
    MAX_TAGS_PER_USER,
)
from handlers.common import create_keyboard, get_main_keyboard
from services import api_client


class CreateTaskState(StatesGroup):
    title = State()
    notify_time = State()
    tags = State()


async def cmd_new_task(message: types.Message, state: FSMContext):
    await state.set_state(CreateTaskState.title)
    await message.answer("Введите название задачи:")


async def process_task_title(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым")
        return

    await state.update_data(title=message.text.strip())
    keyboard = create_keyboard(
        [
            [
                InlineKeyboardButton(text="⏰ 1 минута", callback_data="notify_1"),
                InlineKeyboardButton(text="⏰ 2 минуты", callback_data="notify_2"),
            ],
            [
                InlineKeyboardButton(text="⏰ 5 минут", callback_data="notify_5"),
                InlineKeyboardButton(text="⏰ 10 минут", callback_data="notify_10"),
            ],
            [InlineKeyboardButton(text="⏰ 1 час", callback_data="notify_60")],
        ]
    )
    await message.answer("Когда напомнить?", reply_markup=keyboard)
    await state.set_state(CreateTaskState.notify_time)


async def process_notify_time(callback: types.CallbackQuery, state: FSMContext):
    minutes = int(callback.data.split("_")[1])
    due_date = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    await state.update_data(due_date=due_date)

    result = await api_client.api_request(
        "GET", "/tags/", params={"telegram_id": callback.from_user.id}
    )
    tags = result.get("tags", [])

    if not tags:
        await callback.message.answer("У вас нет тегов. Создаётся без тегов...")
        await finalize_task_creation(callback.from_user.id, state, callback.message)
        await state.clear()
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(text=f"🏷 {t['name']}", callback_data=f"tag_{t['id']}")]
        for t in tags
    ]
    buttons.append(
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="tags_skip")]
    )
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="tags_done")])

    await callback.message.answer(
        f"Выберите теги (макс. {MAX_TAGS_PER_USER}):",
        reply_markup=create_keyboard(buttons),
    )
    await state.update_data(selected_tags=[])
    await state.set_state(CreateTaskState.tags)
    await callback.answer()


async def toggle_tag_selection(callback: types.CallbackQuery, state: FSMContext):
    tag_id = callback.data.replace("tag_", "")
    data = await state.get_data()
    selected = data.get("selected_tags", [])

    if tag_id in selected:
        selected.remove(tag_id)
    else:
        if len(selected) >= MAX_TAGS_PER_USER:
            await callback.answer(
                f"Максимум {MAX_TAGS_PER_USER} тега!", show_alert=True
            )
            return
        selected.append(tag_id)

    await state.update_data(selected_tags=selected)
    await callback.answer(f"Выбрано: {len(selected)}")


async def finish_tag_selection(callback: types.CallbackQuery, state: FSMContext):
    await finalize_task_creation(callback.from_user.id, state, callback.message)
    await state.clear()
    await callback.answer()


async def skip_tag_selection(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_tags=[])
    await finalize_task_creation(callback.from_user.id, state, callback.message)
    await state.clear()
    await callback.answer()


async def finalize_task_creation(user_id, state: FSMContext, message):
    data = await state.get_data()
    tag_ids = data.get("selected_tags", [])

    tag_names = []
    if tag_ids:
        tags_result = await api_client.api_request(
            "GET", "/tags/", params={"telegram_id": user_id}
        )
        tag_names = [
            t["name"]
            for t in tags_result.get("tags", [])
            if str(t["id"]) in [str(tid) for tid in tag_ids]
        ]

    result = await api_client.api_request(
        "POST",
        "/tasks/create/",
        json={
            "telegram_id": user_id,
            "title": data["title"],
            "due_date": data.get("due_date"),
            "tags": tag_names,
        },
    )

    if "error" in result:
        await message.answer(f"❌ {result['error']}", reply_markup=get_main_keyboard())
    else:
        await message.answer(
            f"✅ Задача создана: {data['title']}", reply_markup=get_main_keyboard()
        )


async def cmd_list_tasks(message: types.Message):
    result = await api_client.api_request(
        "GET", "/tasks/", params={"telegram_id": message.from_user.id}
    )
    tasks = result.get("tasks", [])

    if not tasks:
        await message.answer("📋 Нет активных задач", reply_markup=get_main_keyboard())
        return

    text = f"📋 Задачи ({len(tasks)}/{MAX_PENDING_TASKS_PER_USER}):\n\n"
    for t in tasks:
        tags = f" [{', '.join(t['tags'])}]" if t["tags"] else ""
        due = f"\n  ⏰ {t['due_date']}" if t["due_date"] else ""
        text += f"• {t['title']}{tags}\n  📅 {t['created_at']}{due}\n\n"

    await message.answer(text, reply_markup=get_main_keyboard())


async def cmd_archive(message: types.Message):
    result = await api_client.api_request(
        "GET", "/archive/", params={"telegram_id": message.from_user.id}
    )
    tasks = result.get("tasks", [])

    if not tasks:
        await message.answer("📦 Архив пуст", reply_markup=get_main_keyboard())
        return

    text = f"📦 Архив (последние {MAX_ARCHIVE_TASKS_PER_USER}):\n\n"
    for t in tasks:
        status = "✅" if t["status"] == "completed" else "🗑"
        tags = f" [{', '.join(t['tags'])}]" if t["tags"] else ""
        text += f"{status} {t['title']}{tags}\n  📅 {t['created_at']}\n\n"
    await message.answer(text, reply_markup=get_main_keyboard())


async def cmd_delete_task_start(message: types.Message):
    result = await api_client.api_request(
        "GET", "/tasks/", params={"telegram_id": message.from_user.id}
    )
    tasks = result.get("tasks", [])

    if not tasks:
        await message.answer("Нет задач для удаления", reply_markup=get_main_keyboard())
        return

    buttons = [
        [InlineKeyboardButton(text=t["title"], callback_data=f"del_task_{t['id']}")]
        for t in tasks
    ]
    await message.answer(
        "Выберите задачу для удаления:", reply_markup=create_keyboard(buttons)
    )


async def cmd_delete_task_confirm(callback: types.CallbackQuery):
    task_id = callback.data.replace("del_task_", "")
    result = await api_client.api_request(
        "POST",
        "/tasks/delete/",
        json={"telegram_id": callback.from_user.id, "task_id": task_id},
    )
    if "error" in result:
        await callback.message.edit_text(f"❌ {result['error']}")
    else:
        await callback.message.answer(
            "✅ Задача удалена", reply_markup=get_main_keyboard()
        )
        await callback.message.delete()
    await callback.answer()
