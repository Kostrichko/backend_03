from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from config import MAX_TAGS_PER_USER
from handlers.common import create_keyboard, get_main_keyboard
from services import api_client


class CreateTagState(StatesGroup):
    name = State()


async def create_tag(user_id, name, message):
    result = await api_client.api_request(
        "POST", "/tags/create/", json={"telegram_id": user_id, "name": name}
    )
    if "error" in result:
        await message.answer(f"❌ {result['error']}", reply_markup=get_main_keyboard())
    else:
        await message.answer(f"✅ Тег создан: {name}", reply_markup=get_main_keyboard())


async def cmd_new_tag_start(message: types.Message, state: FSMContext):
    await state.set_state(CreateTagState.name)
    await message.answer("Введите название тега:")


async def cmd_create_tag(message: types.Message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Использование: /tag название", reply_markup=get_main_keyboard()
        )
        return
    await create_tag(message.from_user.id, parts[1].strip(), message)


async def process_tag_name(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым")
        return
    await create_tag(message.from_user.id, message.text.strip(), message)
    await state.clear()


async def cmd_list_tags(message: types.Message):
    result = await api_client.api_request(
        "GET", "/tags/", params={"telegram_id": message.from_user.id}
    )
    tags = result.get("tags", [])

    if not tags:
        await message.answer("🏷 Нет тегов", reply_markup=get_main_keyboard())
        return

    text = f"🏷 Теги ({len(tags)}/{MAX_TAGS_PER_USER}):\n\n" + "\n".join(
        f"• {t['name']}" for t in tags
    )
    buttons = [
        [InlineKeyboardButton(text="➕ Создать тег", callback_data="create_tag_ask")],
        [InlineKeyboardButton(text="🗑 Удалить тег", callback_data="delete_tag_list")],
    ]
    await message.answer(text, reply_markup=create_keyboard(buttons))


async def handle_create_tag_ask(callback: types.CallbackQuery):
    await callback.message.answer("Введите название тега")
    await callback.answer()


async def cmd_delete_tag_confirm(callback: types.CallbackQuery):
    tag_id = callback.data.replace("del_tag_", "")
    result = await api_client.api_request(
        "POST",
        "/tags/delete/",
        json={"telegram_id": callback.from_user.id, "tag_id": tag_id},
    )
    if "error" in result:
        await callback.message.edit_text(f"❌ {result['error']}")
    else:
        await callback.message.answer("✅ Тег удалён", reply_markup=get_main_keyboard())
        await callback.message.delete()
    await callback.answer()


async def cmd_delete_tag_start(message: types.Message):
    result = await api_client.api_request(
        "GET", "/tags/", params={"telegram_id": message.from_user.id}
    )
    tags = result.get("tags", [])

    if not tags:
        await message.answer("Нет тегов для удаления", reply_markup=get_main_keyboard())
        return

    buttons = [
        [InlineKeyboardButton(text=t["name"], callback_data=f"del_tag_{t['id']}")]
        for t in tags
    ]
    await message.answer(
        "Выберите тег для удаления:", reply_markup=create_keyboard(buttons)
    )


async def handle_delete_tag_list(callback: types.CallbackQuery):
    result = await api_client.api_request(
        "GET", "/tags/", params={"telegram_id": callback.from_user.id}
    )
    tags = result.get("tags", [])

    if not tags:
        await callback.message.answer(
            "Нет тегов для удаления", reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(text=t["name"], callback_data=f"del_tag_{t['id']}")]
        for t in tags
    ]
    await callback.message.answer(
        "Выберите тег для удаления:", reply_markup=create_keyboard(buttons)
    )
    await callback.answer()
