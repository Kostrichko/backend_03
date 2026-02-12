from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import MAX_ARCHIVE_TASKS_PER_USER, MAX_TAGS_PER_USER
from services import api_client


def create_keyboard(buttons):
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Новая задача"),
                KeyboardButton(text="📋 Мои задачи"),
            ],
            [KeyboardButton(text="🏷 Теги"), KeyboardButton(text="📦 Архив")],
            [
                KeyboardButton(text="🗑 Удалить задачу"),
                KeyboardButton(text="➕ Новый тег"),
            ],
        ],
        resize_keyboard=True,
    )
    return keyboard


async def cmd_start(message: types.Message):
    await api_client.api_request(
        "POST",
        "/register/",
        json={
            "telegram_id": message.from_user.id,
            "username": message.from_user.username or "",
        },
    )

    await message.answer(
        "🤖 Бот управления задачами\n\n"
        "➕ Новая задача - создать с уведомлением (1мин, 2мин, 5мин, 10мин, 1час)\n"
        "📋 Мои задачи - активные задачи (макс. 6)\n"
        f"🏷 Теги - управление тегами (макс. {MAX_TAGS_PER_USER})\n"
        f"📦 Архив - последние {MAX_ARCHIVE_TASKS_PER_USER} завершённых\n"
        "🗑 Удалить задачу\n"
        "➕ Новый тег - быстрое создание",
        reply_markup=get_main_keyboard(),
    )
