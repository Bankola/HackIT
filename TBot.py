import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
import aiohttp
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = "8155714124:AAGOK9riUWH1uIk0Gsr5NaXEuVNJWy3uDko"
# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище данных (в реальном проекте используйте базу данных)
monitored_sites = {}
error_logs = {}


# Создаем клавиатуру
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить сайт для мониторинга")],
            [KeyboardButton(text="Вывести данные об ошибках")],
            [KeyboardButton(text="Данные о сайте")]
        ],
        resize_keyboard=True
    )
    return keyboard


# Функция для проверки доступности сайта
async def check_site_availability(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                return response.status == 200, response.status
    except Exception as e:
        return False, str(e)


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в бот для мониторинга сайтов!\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )


# Обработка кнопки "Добавить сайт для мониторинга"
@dp.message(F.text == "Добавить сайт для мониторинга")
async def add_site(message: types.Message):
    await message.answer(
        "Введите URL сайта для мониторинга (например: https://example.com):\n"
        "Убедитесь, что URL начинается с http:// или https://"
    )


# Обработка ввода URL
@dp.message(F.text.startswith(('http://', 'https://')))
async def process_url(message: types.Message):
    url = message.text.strip()
    user_id = message.from_user.id

    # Проверяем доступность сайта
    is_available, status = await check_site_availability(url)

    if is_available:
        # Сохраняем сайт
        if user_id not in monitored_sites:
            monitored_sites[user_id] = []

        site_data = {
            'url': url,
            'added_date': datetime.now().isoformat(),
            'last_check': datetime.now().isoformat(),
            'status': 'online'
        }

        monitored_sites[user_id].append(site_data)

        await message.answer(
            f"✅ Сайт {url} успешно добавлен для мониторинга!\n"
            f"Статус: онлайн (код: {status})",
            reply_markup=get_main_keyboard()
        )
    else:
        # Сохраняем ошибку
        if user_id not in error_logs:
            error_logs[user_id] = []

        error_data = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'error': f"Сайт недоступен. Статус/ошибка: {status}",
            'type': 'connection_error'
        }

        error_logs[user_id].append(error_data)

        await message.answer(
            f"❌ Сайт {url} недоступен!\n"
            f"Ошибка: {status}\n"
            "Хотите добавить его для мониторинга несмотря на это?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data=f"add_anyway:{url}"),
                 InlineKeyboardButton(text="Нет", callback_data="cancel_add")]
            ])
        )


# Обработка callback для добавления несмотря на ошибку
@dp.callback_query(F.data.startswith("add_anyway:"))
async def add_site_anyway(callback: types.CallbackQuery):
    url = callback.data.split(":")[1]
    user_id = callback.from_user.id

    if user_id not in monitored_sites:
        monitored_sites[user_id] = []

    site_data = {
        'url': url,
        'added_date': datetime.now().isoformat(),
        'last_check': datetime.now().isoformat(),
        'status': 'offline'
    }

    monitored_sites[user_id].append(site_data)

    await callback.message.edit_text(
        f"⚠️ Сайт {url} добавлен для мониторинга (статус: оффлайн)"
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel_add")
async def cancel_add(callback: types.CallbackQuery):
    await callback.message.edit_text("Добавление сайта отменено")
    await callback.answer()


# Обработка кнопки "Вывести данные об ошибках"
@dp.message(F.text == "Вывести данные об ошибках")
async def show_errors(message: types.Message):
    user_id = message.from_user.id

    if user_id not in error_logs or not error_logs[user_id]:
        await message.answer("❌ У вас нет записей об ошибках.")
        return

    errors = error_logs[user_id][-10:]  # Последние 10 ошибок

    response = "📊 Последние ошибки мониторинга:\n\n"
    for i, error in enumerate(errors, 1):
        timestamp = datetime.fromisoformat(error['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        response += f"{i}. {error['url']}\n"
        response += f"   Время: {timestamp}\n"
        response += f"   Ошибка: {error['error']}\n\n"

    await message.answer(response)


# Обработка кнопки "Данные о сайте"
@dp.message(F.text == "Данные о сайте")
async def show_site_data(message: types.Message):
    user_id = message.from_user.id

    if user_id not in monitored_sites or not monitored_sites[user_id]:
        await message.answer("❌ У вас нет добавленных сайтов для мониторинга.")
        return

    # Создаем inline клавиатуру с сайтами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for site in monitored_sites[user_id]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=site['url'],
                callback_data=f"site_info:{site['url']}"
            )
        ])

    await message.answer("Выберите сайт для просмотра информации:", reply_markup=keyboard)


# Обработка выбора сайта
@dp.callback_query(F.data.startswith("site_info:"))
async def show_specific_site_info(callback: types.CallbackQuery):
    url = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Находим сайт
    site = None
    for s in monitored_sites.get(user_id, []):
        if s['url'] == url:
            site = s
            break

    if not site:
        await callback.answer("Сайт не найден")
        return

    # Проверяем текущий статус
    is_available, status = await check_site_availability(url)
    site['last_check'] = datetime.now().isoformat()
    site['status'] = 'online' if is_available else 'offline'

    # Формируем ответ
    added_date = datetime.fromisoformat(site['added_date']).strftime("%Y-%m-%d %H:%M:%S")
    last_check = datetime.fromisoformat(site['last_check']).strftime("%Y-%m-%d %H:%M:%S")

    response = f"🌐 Информация о сайте: {url}\n\n"
    response += f"📅 Добавлен: {added_date}\n"
    response += f"⏰ Последняя проверка: {last_check}\n"
    response += f"📊 Текущий статус: {'✅ Онлайн' if is_available else '❌ Оффлайн'}\n"

    if not is_available:
        response += f"🔧 Причина: {status}\n"

    # Добавляем кнопку для проверки сейчас
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить сейчас", callback_data=f"check_now:{url}")]
    ])

    await callback.message.edit_text(response, reply_markup=keyboard)
    await callback.answer()


# Обработка кнопки "Проверить сейчас"
@dp.callback_query(F.data.startswith("check_now:"))
async def check_site_now(callback: types.CallbackQuery):
    url = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Проверяем сайт
    is_available, status = await check_site_availability(url)

    # Обновляем данные
    for site in monitored_sites.get(user_id, []):
        if site['url'] == url:
            site['last_check'] = datetime.now().isoformat()
            site['status'] = 'online' if is_available else 'offline'
            break

    # Формируем ответ
    response = f"🔍 Результат проверки {url}:\n\n"
    response += f"Статус: {'✅ Доступен' if is_available else '❌ Недоступен'}\n"

    if is_available:
        response += f"Код ответа: {status}"
    else:
        response += f"Ошибка: {status}"

    await callback.answer(response, show_alert=True)


# Команда для проверки всех сайтов
@dp.message(Command("check_all"))
async def check_all_sites(message: types.Message):
    user_id = message.from_user.id

    if user_id not in monitored_sites or not monitored_sites[user_id]:
        await message.answer("❌ У вас нет сайтов для проверки.")
        return

    await message.answer("🔄 Начинаю проверку всех сайтов...")

    results = []
    for site in monitored_sites[user_id]:
        is_available, status = await check_site_availability(site['url'])
        site['last_check'] = datetime.now().isoformat()
        site['status'] = 'online' if is_available else 'offline'

        status_emoji = "✅" if is_available else "❌"
        results.append(f"{status_emoji} {site['url']} - {'Доступен' if is_available else 'Недоступен'}")

    response = "📊 Результаты проверки всех сайтов:\n\n" + "\n".join(results)
    await message.answer(response)


# Команда для просмотра всех сайтов
@dp.message(Command("sites"))
async def list_sites(message: types.Message):
    user_id = message.from_user.id

    if user_id not in monitored_sites or not monitored_sites[user_id]:
        await message.answer("❌ У вас нет добавленных сайтов.")
        return

    response = "📋 Ваши сайты для мониторинга:\n\n"
    for i, site in enumerate(monitored_sites[user_id], 1):
        last_check = datetime.fromisoformat(site['last_check']).strftime("%Y-%m-%d %H:%M")
        status_emoji = "✅" if site['status'] == 'online' else "❌"
        response += f"{i}. {status_emoji} {site['url']}\n   Последняя проверка: {last_check}\n\n"

    await message.answer(response)


# Обработка неизвестных команд
@dp.message()
async def unknown_command(message: types.Message):
    await message.answer(
        "Я не понимаю эту команду. Используйте кнопки меню или команды:\n"
        "/start - начать работу\n"
        "/check_all - проверить все сайты\n"
        "/sites - показать все сайты",
        reply_markup=get_main_keyboard()
    )


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
