import os
import re
import asyncio
import logging
import phonenumbers
from phonenumbers import geocoder, carrier

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Ключи Telegram API (my.telegram.org)
API_ID = 35453067
API_HASH = "0bf17f13f8fda37bb4aa857debb02295"

# Токен бота получаем из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация aiogram
dp = Dispatcher()
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Подключение сессии Telethon (использует checker_session.session из папки)
session_file = "checker_session"
telethon_client = TelegramClient(session_file, API_ID, API_HASH)

# --- ФУНКЦИИ ОСИНТ-ПОИСКА ---

def analyze_phone(phone_str: str) -> str:
    """Анализ номера телефона."""
    try:
        parsed = phonenumbers.parse(phone_str if phone_str.startswith("+") else f"+{phone_str}")
        if not phonenumbers.is_valid_number(parsed):
            return "❌ <b>Невалидный номер телефона.</b>"
        
        country = geocoder.country_name_for_number(parsed, "ru")
        region = geocoder.description_for_number(parsed, "ru")
        operator = carrier.name_for_number(parsed, "ru")
        intl_fmt = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        raw_num = str(parsed.national_number)
        
        return (
            f"📱 <b>Анализ номера телефона:</b>\n\n"
            f"▪️ <b>Формат:</b> <code>{intl_fmt}</code>\n"
            f"▪️ <b>Страна:</b> {country or 'Не определена'}\n"
            f"▪️ <b>Регион:</b> {region or 'Не определён'}\n"
            f"▪️ <b>Оператор:</b> {operator or 'Не определён'}\n\n"
            f"🔗 <b>Быстрые ссылки:</b>\n"
            f"• <a href='https://t.me/{raw_num}'>Telegram</a> | "
            f"<a href='https://wa.me/{raw_num}'>WhatsApp</a> | "
            f"<a href='https://viber.click/{raw_num}'>Viber</a>\n"
            f"• <a href='https://www.google.com/search?q=%22{intl_fmt}%22'>Поиск в Google</a>"
        )
    except Exception as e:
        return f"⚠️ Ошибка обработки номера: {e}"

async def analyze_username(username: str) -> str:
    """Проверка Telegram Username."""
    username = username.lstrip("@")
    
    if telethon_client:
        try:
            entity = await telethon_client.get_entity(username)
            entity_id = entity.id
            title = getattr(entity, 'title', None) or getattr(entity, 'first_name', '')
            last_name = getattr(entity, 'last_name', '') or ''
            is_bot = getattr(entity, 'bot', False)
            scam = getattr(entity, 'scam', False)
            
            return (
                f"👤 <b>Профиль Telegram:</b>\n\n"
                f"▪️ <b>ID:</b> <code>{entity_id}</code>\n"
                f"▪️ <b>Имя:</b> {title} {last_name}\n"
                f"▪️ <b>Юзернейм:</b> @{username}\n"
                f"▪️ <b>Тип:</b> {'Бот' if is_bot else 'Пользователь/Канал'}\n"
                f"▪️ <b>SCAM:</b> {'⚠️ ДА' if scam else '❌ Нет'}\n\n"
                f"🔗 <b>Ссылки:</b>\n"
                f"• <a href='https://t.me/{username}'>Открыть в Telegram</a>\n"
                f"• <a href='https://fragment.com/username/{username}'>Fragment.com</a>"
            )
        except UsernameNotOccupiedError:
            return f"ℹ️ Юзернейм @{username} <b>свободен</b>."
        except Exception:
            pass

    return (
        f"🔍 <b>Юзернейм:</b> @{username}\n\n"
        f"🔗 <b>Проверка по базам:</b>\n"
        f"• <a href='https://t.me/{username}'>Открыть в Telegram</a>\n"
        f"• <a href='https://fragment.com/username/{username}'>Проверить NFT на Fragment</a>\n"
        f"• <a href='https://www.google.com/search?q=%22{username}%22'>Искать упоминания в Google</a>"
    )

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👁 <b>OSINT Search Bot запущен!</b>\n\n"
        "Отправь данные для поиска:\n"
        "• <b>Номер:</b> <code>+79991234567</code>\n"
        "• <b>Юзернейм:</b> <code>@username</code>\n"
        "• <b>Email:</b> <code>mail@gmail.com</code>\n"
        "• <b>ID:</b> <code>123456789</code>"
    )

@dp.message(F.text)
async def handle_search(message: types.Message):
    query = message.text.strip()
    status = await message.answer("🔎 <i>Анализ данных...</i>")
    
    # Email
    if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", query):
        res = (
            f"📧 <b>Анализ Email:</b> <code>{query}</code>\n\n"
            f"🔗 <b>Проверка утечек:</b>\n"
            f"• <a href='https://haveibeenpwned.com/'>HaveIBeenPwned</a>\n"
            f"• <a href='https://intelx.io/search?s={query}'>IntelX</a>\n"
            f"• <a href='https://www.google.com/search?q=%22{query}%22'>Google</a>"
        )
    # Phone
    elif re.match(r"^\+?[0-9]{10,14}$", query.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")):
        res = analyze_phone(re.sub(r"[^\d+]", "", query))
    # Username
    elif query.startswith("@") or (re.match(r"^[a-zA-Z0-9_]{5,32}$", query) and not query.isdigit()):
        res = await analyze_username(query)
    # ID
    elif query.isdigit():
        res = (
            f"🆔 <b>Telegram ID:</b> <code>{query}</code>\n\n"
            f"🔗 <a href='tg://user?id={query}'>Открыть профиль в Telegram</a>\n"
            f"🔗 <a href='https://www.google.com/search?q=%22{query}%22'>Искать ID в Google</a>"
        )
    else:
        res = "❌ Неверный формат запроса."
        
    await status.edit_text(res, disable_web_page_preview=True)

# --- ЗАПУСК ---

async def main():
    if telethon_client:
        await telethon_client.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())