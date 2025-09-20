import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
import aiohttp
from datetime import datetime
import os
from dotenv import load_dotenv
from Database import Database

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и базы данных
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()
db = Database()


# Инициализация базы данных при старте
async def on_startup():
    await db.create_tables()
    logging.info("База данных инициализирована")


# Создаем клавиатуру
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить сайт для мониторинга")],
            [KeyboardButton(text="Вывести данные об ошибках")],
            [KeyboardButton(text="Данные о сайте")],
            [KeyboardButton(text="Мои сайты"), KeyboardButton(text="Статистика")]
        ],
        resize_keyboard=True
    )
    return keyboard


# Функция для проверки доступности сайта
async def check_site_availability(url):
    try:
        start_time = datetime.now()
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                return True, response.status, response_time
    except Exception as e:
        return False, str(e), 0


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Добавляем пользователя в базу данных
    await db.add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

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

    # Проверяем, не добавлен ли уже сайт
    existing_site = await db.get_site_by_url(user_id, url)
    if existing_site:
        await message.answer("❌ Этот сайт уже добавлен для мониторинга!")
        return

    # Проверяем доступность сайта
    is_available, status, response_time = await check_site_availability(url)

    if is_available:
        # Добавляем сайт в базу данных
        site_id = await db.add_site(user_id, url)
        await db.update_site_status(site_id, 'online', status)

        await message.answer(
            f"✅ Сайт {url} успешно добавлен для мониторинга!\n"
            f"Статус: онлайн (код: {status})\n"
            f"Время ответа: {response_time:.2f} сек",
            reply_markup=get_main_keyboard()
        )
    else:
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

    # Добавляем сайт в базу данных
    site_id = await db.add_site(user_id, url)
    await db.update_site_status(site_id, 'offline')
    await db.add_error(user_id, site_id, 'connection_error', 'Сайт был недоступен при добавлении')

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

    errors = await db.get_site_errors(user_id, limit=10)

    if not errors:
        await message.answer("✅ У вас нет ошибок мониторинга!")
        return

    response = "📊 Последние ошибки мониторинга:\n\n"
    for i, error in enumerate(errors, 1):
        timestamp = datetime.fromisoformat(error['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        response += f"{i}. {error['url']}\n"
        response += f"   Время: {timestamp}\n"
        response += f"   Ошибка: {error['error_message']}\n"
        response += f"   Статус: {'✅ Решена' if error['resolved'] else '❌ Активна'}\n\n"

    await message.answer(response)


# Обработка кнопки "Данные о сайте"
@dp.message(F.text == "Данные о сайте")
async def show_site_data(message: types.Message):
    user_id = message.from_user.id

    sites = await db.get_user_sites(user_id)

    if not sites:
        await message.answer("❌ У вас нет добавленных сайтов для мониторинга.")
        return

    # Создаем inline клавиатуру с сайтами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for site in sites:
        status_emoji = "✅" if site['status'] == 'online' else "❌"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {site['url']}",
                callback_data=f"site_info:{site['id']}"
            )
        ])

    await message.answer("Выберите сайт для просмотра информации:", reply_markup=keyboard)


# Обработка выбора сайта
@dp.callback_query(F.data.startswith("site_info:"))
async def show_specific_site_info(callback: types.CallbackQuery):
    site_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Получаем информацию о сайте
    sites = await db.get_user_sites(user_id)
    site = next((s for s in sites if s['id'] == site_id), None)

    if not site:
        await callback.answer("Сайт не найден")
        return

    # Проверяем текущий статус
    is_available, status, response_time = await check_site_availability(site['url'])
    new_status = 'online' if is_available else 'offline'
    await db.update_site_status(site_id, new_status, status if is_available else None)

    # Получаем статистику
    stats = await db.get_site_stats(site_id)

    added_date = datetime.fromisoformat(site['added_date']).strftime("%Y-%m-%d %H:%M:%S")
    last_check = datetime.fromisoformat(site['last_check']).strftime("%Y-%m-%d %H:%M:%S")

    response = f"🌐 Информация о сайте: {site['url']}\n\n"
    response += f"📅 Добавлен: {added_date}\n"
    response += f"⏰ Последняя проверка: {last_check}\n"
    response += f"📊 Текущий статус: {'✅ Онлайн' if is_available else '❌ Оффлайн'}\n"

    if is_available:
        response += f"⚡ Время ответа: {response_time:.2f} сек\n"
        response += f"🔢 Код ответа: {status}\n"
    else:
        response += f"🔧 Причина: {status}\n"

    response += f"\n📈 Статистика:\n"
    response += f"   Всего проверок: {stats['total_checks']}\n"
    response += f"   Успешных: {stats['success_checks']}\n"
    response += f"   Ошибок: {stats['error_count']}\n"
    response += f"   Uptime: {stats['uptime_percentage']:.1f}%\n"

    # Добавляем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить сейчас", callback_data=f"check_now:{site_id}"),
         InlineKeyboardButton(text="❌ Удалить сайт", callback_data=f"delete_site:{site_id}")],
        [InlineKeyboardButton(text="📊 Ошибки сайта", callback_data=f"site_errors:{site_id}")]
    ])

    await callback.message.edit_text(response, reply_markup=keyboard)
    await callback.answer()


@dp.message(F.text == "Мои сайты")
async def list_sites(message: types.Message):
    user_id = message.from_user.id

    sites = await db.get_user_sites(user_id)

    if not sites:
        await message.answer("❌ У вас нет добавленных сайтов.")
        return

    response = "📋 Ваши сайты для мониторинга:\n\n"
    for i, site in enumerate(sites, 1):
        last_check = datetime.fromisoformat(site['last_check']).strftime("%Y-%m-%d %H:%M")
        status_emoji = "✅" if site['status'] == 'online' else "❌"
        response += f"{i}. {status_emoji} {site['url']}\n"
        response += f"   Последняя проверка: {last_check}\n"
        response += f"   Статус: {site['status']}\n\n"

    await message.answer(response)


# Обработка кнопки "Статистика"
@dp.message(F.text == "Статистика")
async def show_stats(message: types.Message):
    user_id = message.from_user.id

    sites = await db.get_user_sites(user_id)

    if not sites:
        await message.answer("❌ У вас нет сайтов для отображения статистики.")
        return

    response = "📊 Общая статистика мониторинга:\n\n"

    total_sites = len(sites)
    online_sites = sum(1 for site in sites if site['status'] == 'online')
    offline_sites = total_sites - online_sites

    response += f"🌐 Всего сайтов: {total_sites}\n"
    response += f"✅ Онлайн: {online_sites}\n"
    response += f"❌ Оффлайн: {offline_sites}\n"
    response += f"📈 Uptime: {(online_sites / total_sites * 100):.1f}%\n\n"

    response += "Сайты по статусу:\n"
    for site in sites:
        status_emoji = "✅" if site['status'] == 'online' else "❌"
        response += f"{status_emoji} {site['url']}\n"

    await message.answer(response)


# Обработка кнопки "Проверить сейчас"
@dp.callback_query(F.data.startswith("check_now:"))
async def check_site_now(callback: types.CallbackQuery):
    site_id = int(callback.data.split(":")[1])

    # Получаем информацию о сайте
    sites = await db.get_user_sites(callback.from_user.id)
    site = next((s for s in sites if s['id'] == site_id), None)

    if not site:
        await callback.answer("Сайт не найден")
        return

    # Проверяем сайт
    is_available, status, response_time = await check_site_availability(site['url'])
    new_status = 'online' if is_available else 'offline'
    await db.update_site_status(site_id, new_status, status if is_available else None)

    # Формируем ответ
    response = f"🔍 Результат проверки {site['url']}:\n\n"
    response += f"Статус: {'✅ Доступен' if is_available else '❌ Недоступен'}\n"

    if is_available:
        response += f"Код ответа: {status}\n"
        response += f"Время ответа: {response_time:.2f} сек"
    else:
        response += f"Ошибка: {status}"
        # Добавляем ошибку в базу данных
        await db.add_error(callback.from_user.id, site_id, 'connection_error', str(status))

    await callback.answer(response, show_alert=True)


# Обработка кнопки "Удалить сайт"
@dp.callback_query(F.data.startswith("delete_site:"))
async def delete_site_handler(callback: types.CallbackQuery):
    site_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Получаем информацию о сайте перед удалением
    site = await db.get_site_by_id(site_id)
    if not site:
        await callback.answer("❌ Сайт не найден!")
        return

    # Проверяем, что сайт принадлежит пользователю
    if site['user_id'] != user_id:
        await callback.answer("❌ У вас нет прав для удаления этого сайта!")
        return

    # Подтверждение удаления
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить сайт?\n\n"
        f"URL: {site['url']}\n\n"
        f"Это действие нельзя отменить! Все данные о сайте будут удалены.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{site_id}"),
             InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_delete:{site_id}")]
        ])
    )
    await callback.answer()


# Подтверждение удаления сайта
@dp.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_site(callback: types.CallbackQuery):
    site_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Получаем информацию о сайте перед удалением
    site = await db.get_site_by_id(site_id)
    if not site:
        await callback.answer("❌ Сайт не найден!")
        return

    # Удаляем сайт
    success = await db.delete_site(user_id, site_id)

    if success:
        await callback.message.edit_text(
            f"✅ Сайт успешно удален!\n\n"
            f"URL: {site['url']}\n\n"
            f"Все данные о сайте были удалены из системы."
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось удалить сайт. Возможно, у вас нет прав на это действие."
        )
    await callback.answer()


# Отмена удаления сайта
@dp.callback_query(F.data.startswith("cancel_delete:"))
async def cancel_delete_site(callback: types.CallbackQuery):
    site_id = int(callback.data.split(":")[1])

    # Возвращаемся к информации о сайте
    sites = await db.get_user_sites(callback.from_user.id)
    site = next((s for s in sites if s['id'] == site_id), None)

    if not site:
        await callback.answer("Сайт не найден")
        return

    # Проверяем текущий статус
    is_available, status, response_time = await check_site_availability(site['url'])
    new_status = 'online' if is_available else 'offline'
    await db.update_site_status(site_id, new_status, status if is_available else None)

    # Получаем статистику
    stats = await db.get_site_stats(site_id)

    # Формируем ответ
    added_date = datetime.fromisoformat(site['added_date']).strftime("%Y-%m-%d %H:%M:%S")
    last_check = datetime.fromisoformat(site['last_check']).strftime("%Y-%m-%d %H:%M:%S")

    response = f"🌐 Информация о сайте: {site['url']}\n\n"
    response += f"📅 Добавлен: {added_date}\n"
    response += f"⏰ Последняя проверка: {last_check}\n"
    response += f"📊 Текущий статус: {'✅ Онлайн' if is_available else '❌ Оффлайн'}\n"

    if is_available:
        response += f"⚡ Время ответа: {response_time:.2f} сек\n"
        response += f"🔢 Код ответа: {status}\n"
    else:
        response += f"🔧 Причина: {status}\n"

    response += f"\n📈 Статистика:\n"
    response += f"   Всего проверок: {stats['total_checks']}\n"
    response += f"   Успешных: {stats['success_checks']}\n"
    response += f"   Ошибок: {stats['error_count']}\n"
    response += f"   Uptime: {stats['uptime_percentage']:.1f}%\n"

    # Добавляем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить сейчас", callback_data=f"check_now:{site_id}"),
         InlineKeyboardButton(text="❌ Удалить сайт", callback_data=f"delete_site:{site_id}")],
        [InlineKeyboardButton(text="📊 Ошибки сайта", callback_data=f"site_errors:{site_id}")]
    ])

    await callback.message.edit_text(response, reply_markup=keyboard)
    await callback.answer()


# Обработка кнопки "Ошибки сайта"
@dp.callback_query(F.data.startswith("site_errors:"))
async def show_site_errors(callback: types.CallbackQuery):
    site_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Получаем информацию о сайте
    site = await db.get_site_by_id(site_id)
    if not site:
        await callback.answer("❌ Сайт не найден!")
        return

    # Проверяем, что сайт принадлежит пользователю
    if site['user_id'] != user_id:
        await callback.answer("❌ У вас нет прав для просмотра ошибок этого сайта!")
        return

    # Получаем последние 5 ошибок для этого сайта
    errors = await db.get_site_errors(user_id, site_id=site_id, limit=5)

    if not errors:
        response = f"✅ Для сайта {site['url']} нет ошибок!\n\n"
        response += "Система мониторинга не обнаружила проблем с этим сайтом."

        await callback.message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад к информации", callback_data=f"site_info:{site_id}")]
            ])
        )
    else:
        response = f"📊 Последние ошибки сайта: {site['url']}\n\n"

        for i, error in enumerate(errors, 1):
            timestamp = datetime.fromisoformat(error['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            status_emoji = "✅" if error['resolved'] else "❌"
            response += f"{i}. {timestamp}\n"
            response += f"   Тип: {error['error_type']}\n"
            response += f"   Ошибка: {error['error_message']}\n"
            response += f"   Статус: {status_emoji} {'Решена' if error['resolved'] else 'Активна'}\n\n"

        response += f"Всего ошибок: {len(errors)}"

        await callback.message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад к информации", callback_data=f"site_info:{site_id}"),
                 InlineKeyboardButton(text="🗑️ Очистить ошибки", callback_data=f"clear_errors:{site_id}")]
            ])
        )

    await callback.answer()


# Обработка кнопки "Очистить ошибки"
@dp.callback_query(F.data.startswith("clear_errors:"))
async def clear_site_errors(callback: types.CallbackQuery):
    site_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Помечаем все ошибки сайта как решенные
    async with aiosqlite.connect('monitoring_bot.db') as conn:
        await conn.execute(
            'UPDATE errors SET resolved = 1 WHERE site_id = ? AND user_id = ?',
            (site_id, user_id)
        )
        await conn.commit()

    # Получаем информацию о сайте
    site = await db.get_site_by_id(site_id)

    await callback.message.edit_text(
        f"✅ Все ошибки для сайта {site['url']} помечены как решенные!\n\n"
        f"Система продолжит мониторинг сайта на наличие новых ошибок.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад к информации", callback_data=f"site_info:{site_id}")]
        ])
    )
    await callback.answer()


# Запуск бота с инициализацией БД
async def main():
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())