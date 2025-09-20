# Database.py - добавляем новые методы
import aiosqlite
import json
from datetime import datetime
from typing import List, Dict, Any


class Database:
    def __init__(self, db_name: str = 'monitoring_bot.db'):
        self.db_name = db_name

    async def create_tables(self):
        """Создание таблиц в базе данных"""
        async with aiosqlite.connect(self.db_name) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TEXT
                )
            ''')

            # Таблица сайтов для мониторинга
            await db.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT NOT NULL,
                    added_date TEXT NOT NULL,
                    last_check TEXT,
                    status TEXT,
                    check_interval INTEGER DEFAULT 300,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Таблица ошибок мониторинга
            await db.execute('''
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    site_id INTEGER,
                    error_type TEXT,
                    error_message TEXT,
                    timestamp TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (site_id) REFERENCES sites (id)
                )
            ''')

            # Таблица истории проверок
            await db.execute('''
                CREATE TABLE IF NOT EXISTS check_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER,
                    status_code INTEGER,
                    response_time REAL,
                    timestamp TEXT NOT NULL,
                    success INTEGER,
                    FOREIGN KEY (site_id) REFERENCES sites (id)
                )
            ''')

            await db.commit()

    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        """Добавление пользователя в базу данных"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, created_at) VALUES (?, ?, ?, ?, ?)',
                (user_id, username, first_name, last_name, datetime.now().isoformat())
            )
            await db.commit()

    async def add_site(self, user_id: int, url: str) -> int:
        """Добавление сайта для мониторинга"""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'INSERT INTO sites (user_id, url, added_date, last_check, status) VALUES (?, ?, ?, ?, ?)',
                (user_id, url, datetime.now().isoformat(), datetime.now().isoformat(), 'pending')
            )
            await db.commit()
            return cursor.lastrowid

    async def update_site_status(self, site_id: int, status: str, status_code: int = None):
        """Обновление статуса сайта"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'UPDATE sites SET status = ?, last_check = ? WHERE id = ?',
                (status, datetime.now().isoformat(), site_id)
            )

            if status_code is not None:
                success = 1 if status == 'online' else 0
                await db.execute(
                    'INSERT INTO check_history (site_id, status_code, response_time, timestamp, success) VALUES (?, ?, ?, ?, ?)',
                    (site_id, status_code, 0, datetime.now().isoformat(), success)
                )

            await db.commit()

    async def add_error(self, user_id: int, site_id: int, error_type: str, error_message: str):
        """Добавление ошибки в базу данных"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'INSERT INTO errors (user_id, site_id, error_type, error_message, timestamp) VALUES (?, ?, ?, ?, ?)',
                (user_id, site_id, error_type, error_message, datetime.now().isoformat())
            )
            await db.commit()

    async def get_user_sites(self, user_id: int) -> List[Dict]:
        """Получение всех сайтов пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM sites WHERE user_id = ? ORDER BY added_date DESC',
                (user_id,)
            )
            sites = await cursor.fetchall()
            return [dict(site) for site in sites]

    async def get_site_by_url(self, user_id: int, url: str) -> Dict:
        """Получение сайта по URL"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM sites WHERE user_id = ? AND url = ?',
                (user_id, url)
            )
            site = await cursor.fetchone()
            return dict(site) if site else None

    async def get_site_by_id(self, site_id: int) -> Dict:
        """Получение сайта по ID"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM sites WHERE id = ?',
                (site_id,)
            )
            site = await cursor.fetchone()
            return dict(site) if site else None

    async def get_site_errors(self, user_id: int, site_id: int = None, limit: int = 10) -> List[Dict]:
        """Получение ошибок пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row

            if site_id:
                cursor = await db.execute(
                    '''SELECT e.*, s.url 
                       FROM errors e 
                       JOIN sites s ON e.site_id = s.id 
                       WHERE e.user_id = ? AND e.site_id = ? 
                       ORDER BY e.timestamp DESC 
                       LIMIT ?''',
                    (user_id, site_id, limit)
                )
            else:
                cursor = await db.execute(
                    '''SELECT e.*, s.url 
                       FROM errors e 
                       JOIN sites s ON e.site_id = s.id 
                       WHERE e.user_id = ? 
                       ORDER BY e.timestamp DESC 
                       LIMIT ?''',
                    (user_id, limit)
                )

            errors = await cursor.fetchall()
            return [dict(error) for error in errors]

    async def get_site_stats(self, site_id: int) -> Dict:
        """Получение статистики по сайту"""
        async with aiosqlite.connect(self.db_name) as db:
            # Общее количество проверок
            cursor = await db.execute(
                'SELECT COUNT(*) as total_checks FROM check_history WHERE site_id = ?',
                (site_id,)
            )
            total_checks = (await cursor.fetchone())[0]

            # Количество успешных проверок
            cursor = await db.execute(
                'SELECT COUNT(*) as success_checks FROM check_history WHERE site_id = ? AND success = 1',
                (site_id,)
            )
            success_checks = (await cursor.fetchone())[0]

            # Последние ошибки
            cursor = await db.execute(
                'SELECT COUNT(*) as error_count FROM errors WHERE site_id = ? AND resolved = 0',
                (site_id,)
            )
            error_count = (await cursor.fetchone())[0]

            return {
                'total_checks': total_checks,
                'success_checks': success_checks,
                'error_count': error_count,
                'uptime_percentage': (success_checks / total_checks * 100) if total_checks > 0 else 0
            }

    async def delete_site(self, user_id: int, site_id: int) -> bool:
        """Удаление сайта и связанных данных"""
        async with aiosqlite.connect(self.db_name) as db:
            # Проверяем, что сайт принадлежит пользователю
            cursor = await db.execute(
                'SELECT id FROM sites WHERE id = ? AND user_id = ?',
                (site_id, user_id)
            )
            site = await cursor.fetchone()

            if not site:
                return False

            # Удаляем связанные данные
            await db.execute('DELETE FROM errors WHERE site_id = ?', (site_id,))
            await db.execute('DELETE FROM check_history WHERE site_id = ?', (site_id,))
            await db.execute('DELETE FROM sites WHERE id = ?', (site_id,))
            await db.commit()
            return True

    async def mark_error_resolved(self, error_id: int):
        """Пометить ошибку как решенную"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('UPDATE errors SET resolved = 1 WHERE id = ?', (error_id,))
            await db.commit()