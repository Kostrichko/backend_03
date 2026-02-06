import asyncio
from aiogram import Bot, Dispatcher
import os
from handlers import register_handlers

BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

register_handlers(dp)


async def main():
    try:
        me = await bot.get_me()
        await dp.start_polling(bot)
    except Exception as e:
        pass


if __name__ == '__main__':
    asyncio.run(main())
