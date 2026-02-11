from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta, timezone
import aiohttp
import os

API_URL = os.getenv('API_URL', 'http://web:8000/api')
API_KEY = os.getenv('API_KEY', '12345')


class CreateTaskState(StatesGroup):
    title = State()
    notify_time = State()
    tags = State()


class CreateTagState(StatesGroup):
    name = State()


async def api_request(method, endpoint, **kwargs):
    url = f"{API_URL}{endpoint}"
    headers = kwargs.get('headers', {})
    headers['X-API-Key'] = API_KEY
    kwargs['headers'] = headers
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    return {'error': f'HTTP {response.status}'}
                return await response.json()
    except Exception as e:
        return {'error': str(e)}


def create_keyboard(buttons):
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Новая задача"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="🏷 Теги"), KeyboardButton(text="📦 Архив")],
            [KeyboardButton(text="🗑 Удалить задачу"), KeyboardButton(text="➕ Новый тег")]
        ],
        resize_keyboard=True
    )
    return keyboard


async def send_error(message, text="Произошла ошибка"):
    await message.answer(f"❌ {text}")


async def cmd_start(message: types.Message):
    await api_request('POST', '/register/', json={
        'telegram_id': message.from_user.id,
        'username': message.from_user.username or ''
    })
    
    await message.answer(
        "🤖 Бот управления задачами\n\n"
        "➕ Новая задача - создать с уведомлением (1мин, 2мин, 5мин, 10мин, 1час)\n"
        "📋 Мои задачи - активные задачи (макс. 6)\n"
        "🏷 Теги - управление тегами (макс. 4)\n"
        "📦 Архив - последние 5 завершённых\n"
        "🗑 Удалить задачу\n"
        "➕ Новый тег - быстрое создание",
        reply_markup=get_main_keyboard()
    )


async def cmd_new_task(message: types.Message, state: FSMContext):
    await state.set_state(CreateTaskState.title)
    await message.answer("Введите название задачи:")


async def process_task_title(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым")
        return
    
    await state.update_data(title=message.text.strip())
    keyboard = create_keyboard([
        [InlineKeyboardButton(text="⏰ 1 минута", callback_data="notify_1"),
         InlineKeyboardButton(text="⏰ 2 минуты", callback_data="notify_2")],
        [InlineKeyboardButton(text="⏰ 5 минут", callback_data="notify_5"),
         InlineKeyboardButton(text="⏰ 10 минут", callback_data="notify_10")],
        [InlineKeyboardButton(text="⏰ 1 час", callback_data="notify_60")]
    ])
    await message.answer("Когда напомнить?", reply_markup=keyboard)
    await state.set_state(CreateTaskState.notify_time)


async def process_notify_time(callback: types.CallbackQuery, state: FSMContext):
    minutes = int(callback.data.split("_")[1])
    due_date = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    await state.update_data(due_date=due_date)
    
    result = await api_request('GET', '/tags/', params={'telegram_id': callback.from_user.id})
    tags = result.get('tags', [])
    
    if not tags:
        await callback.message.answer("У вас нет тегов. Создаётся без тегов...")
        await finalize_task_creation(callback.from_user.id, state, callback.message)
        await state.clear()
        await callback.answer()
        return
    
    buttons = [[InlineKeyboardButton(text=f"🏷 {t['name']}", callback_data=f"tag_{t['id']}")] for t in tags]
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="tags_skip")])
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="tags_done")])
    
    await callback.message.answer("Выберите теги (макс. 4):", reply_markup=create_keyboard(buttons))
    await state.update_data(selected_tags=[])
    await state.set_state(CreateTaskState.tags)
    await callback.answer()


async def toggle_tag_selection(callback: types.CallbackQuery, state: FSMContext):
    tag_id = callback.data.replace("tag_", "")
    data = await state.get_data()
    selected = data.get('selected_tags', [])
    
    if tag_id in selected:
        selected.remove(tag_id)
    else:
        if len(selected) >= 4:
            await callback.answer("Максимум 4 тега!", show_alert=True)
            return
        selected.append(tag_id)
    
    await state.update_data(selected_tags=selected)
    await callback.answer(f"Выбрано: {len(selected)}")


async def finish_tag_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "tags_skip":
        await state.update_data(selected_tags=[])
    
    await finalize_task_creation(callback.from_user.id, state, callback.message)
    await state.clear()
    await callback.answer()


async def finalize_task_creation(user_id, state: FSMContext, message):
    data = await state.get_data()
    tag_ids = data.get('selected_tags', [])
    
    tag_names = []
    if tag_ids:
        tags_result = await api_request('GET', '/tags/', params={'telegram_id': user_id})
        tag_names = [t['name'] for t in tags_result.get('tags', []) if t['id'] in tag_ids]
    
    result = await api_request('POST', '/tasks/create/', json={
        'telegram_id': user_id,
        'title': data['title'],
        'due_date': data.get('due_date'),
        'tags': tag_names
    })
    
    if 'error' in result:
        await message.answer(f"❌ {result['error']}", reply_markup=get_main_keyboard())
    else:
        await message.answer(f"✅ Задача создана: {data['title']}", reply_markup=get_main_keyboard())


async def cmd_list_tasks(message: types.Message):
    result = await api_request('GET', '/tasks/', params={'telegram_id': message.from_user.id})
    tasks = result.get('tasks', [])
    
    if not tasks:
        await message.answer("📋 Нет активных задач", reply_markup=get_main_keyboard())
        return
    
    text = f"📋 Задачи ({len(tasks)}/6):\n\n"
    for t in tasks:
        tags = f" [{', '.join(t['tags'])}]" if t['tags'] else ""
        due = f"\n  ⏰ {t['due_date']}" if t['due_date'] else ""
        text += f"• {t['title']}{tags}\n  📅 {t['created_at']}{due}\n\n"
    
    await message.answer(text, reply_markup=get_main_keyboard())


async def create_tag(user_id, name, message):
    result = await api_request('POST', '/tags/create/', json={'telegram_id': user_id, 'name': name})
    if 'error' in result:
        await message.answer(f"❌ {result['error']}", reply_markup=get_main_keyboard())
    else:
        await message.answer(f"✅ Тег создан: {name}", reply_markup=get_main_keyboard())


async def cmd_create_tag(message: types.Message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /tag название", reply_markup=get_main_keyboard())
        return
    await create_tag(message.from_user.id, parts[1].strip(), message)


async def cmd_new_tag_start(message: types.Message, state: FSMContext):
    await state.set_state(CreateTagState.name)
    await message.answer("Введите название тега:")


async def process_tag_name(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым")
        return
    await create_tag(message.from_user.id, message.text.strip(), message)
    await state.clear()


async def cmd_list_tags(message: types.Message):
    result = await api_request('GET', '/tags/', params={'telegram_id': message.from_user.id})
    tags = result.get('tags', [])
    
    if not tags:
        await message.answer("🏷 Нет тегов", reply_markup=get_main_keyboard())
        return
    
    text = f"🏷 Теги ({len(tags)}/4):\n\n" + "\n".join(f"• {t['name']}" for t in tags)
    buttons = [
        [InlineKeyboardButton(text="➕ Создать тег", callback_data="create_tag_ask")],
        [InlineKeyboardButton(text="🗑 Удалить тег", callback_data="delete_tag_list")]
    ]
    await message.answer(text, reply_markup=create_keyboard(buttons))


async def cmd_archive(message: types.Message):
    result = await api_request('GET', '/archive/', params={'telegram_id': message.from_user.id})
    tasks = result.get('tasks', [])
    
    if not tasks:
        await message.answer("📦 Архив пуст", reply_markup=get_main_keyboard())
        return
    
    text = "📦 Архив (последние 5):\n\n"
    for t in tasks:
        status = "✅" if t['status'] == 'completed' else "🗑"
        tags = f" [{', '.join(t['tags'])}]" if t['tags'] else ""
        text += f"{status} {t['title']}{tags}\n  📅 {t['created_at']}\n\n"
    await message.answer(text, reply_markup=get_main_keyboard())


async def show_items_for_deletion(user_id, endpoint, item_type, callback_prefix):
    result = await api_request('GET', endpoint, params={'telegram_id': user_id})
    items = result.get('tags' if item_type == 'тег' else 'tasks', [])
    
    if not items:
        return None, f"Нет {item_type}ов для удаления"
    
    buttons = [[InlineKeyboardButton(
        text=item['name'] if item_type == 'тег' else item['title'],
        callback_data=f"{callback_prefix}_{item['id']}"
    )] for item in items]
    return create_keyboard(buttons), f"Выберите {item_type} для удаления:"


async def cmd_delete_task_start(message: types.Message):
    keyboard, text = await show_items_for_deletion(
        message.from_user.id, '/tasks/', 'задач', 'del_task'
    )
    if keyboard:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=get_main_keyboard())


async def cmd_delete_tag_start(message: types.Message):
    keyboard, text = await show_items_for_deletion(
        message.from_user.id, '/tags/', 'тег', 'del_tag'
    )
    if keyboard:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=get_main_keyboard())


async def delete_item(callback: types.CallbackQuery, item_id, endpoint, success_msg):
    result = await api_request('POST', endpoint, json={
        'telegram_id': callback.from_user.id,
        f"{'tag' if 'tag' in endpoint else 'task'}_id": item_id
    })
    if 'error' in result:
        await callback.message.edit_text(f"❌ {result['error']}")
    else:
        await callback.message.answer(success_msg, reply_markup=get_main_keyboard())
        await callback.message.delete()
    await callback.answer()


async def cmd_delete_task_confirm(callback: types.CallbackQuery):
    task_id = callback.data.replace("del_task_", "")
    await delete_item(callback, task_id, '/tasks/delete/', "✅ Задача удалена")


async def cmd_delete_tag_confirm(callback: types.CallbackQuery):
    tag_id = callback.data.replace("del_tag_", "")
    await delete_item(callback, tag_id, '/tags/delete/', "✅ Тег удалён")


async def handle_create_tag_ask(callback: types.CallbackQuery):
    await callback.message.answer("Введите название тега")
    await callback.answer()


async def handle_delete_tag_list(callback: types.CallbackQuery):
    keyboard, text = await show_items_for_deletion(
        callback.from_user.id, '/tags/', 'тег', 'del_tag'
    )
    if keyboard:
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        await callback.message.answer(text, reply_markup=get_main_keyboard())
    await callback.answer()


def register_handlers(dp):
    dp.message.register(cmd_start, Command('start'))
    dp.message.register(cmd_new_task, Command('new'))
    dp.message.register(cmd_list_tasks, Command('list'))
    dp.message.register(cmd_create_tag, Command('tag'))
    dp.message.register(cmd_list_tags, Command('tags'))
    dp.message.register(cmd_archive, Command('archive'))
    dp.message.register(cmd_delete_task_start, Command('delete_task'))
    dp.message.register(cmd_delete_tag_start, Command('delete_tag'))
    
    dp.message.register(cmd_new_task, F.text == "➕ Новая задача")
    dp.message.register(cmd_list_tasks, F.text == "📋 Мои задачи")
    dp.message.register(cmd_list_tags, F.text == "🏷 Теги")
    dp.message.register(cmd_archive, F.text == "📦 Архив")
    dp.message.register(cmd_delete_task_start, F.text == "🗑 Удалить задачу")
    dp.message.register(cmd_new_tag_start, F.text == "➕ Новый тег")
    
    dp.message.register(process_task_title, CreateTaskState.title)
    dp.callback_query.register(process_notify_time, CreateTaskState.notify_time, F.data.startswith("notify_"))
    dp.callback_query.register(toggle_tag_selection, CreateTaskState.tags, F.data.startswith("tag_"))
    dp.callback_query.register(finish_tag_selection, CreateTaskState.tags, F.data.in_(["tags_done", "tags_skip"]))
    dp.message.register(process_tag_name, CreateTagState.name)
    
    dp.callback_query.register(cmd_delete_task_confirm, F.data.startswith("del_task_"))
    dp.callback_query.register(cmd_delete_tag_confirm, F.data.startswith("del_tag_"))
    dp.callback_query.register(handle_create_tag_ask, F.data == "create_tag_ask")
    dp.callback_query.register(handle_delete_tag_list, F.data == "delete_tag_list")
