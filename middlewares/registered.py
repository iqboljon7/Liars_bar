from aiogram.types import Update
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from db import is_user_registered
from functools import wraps
from aiogram import types

import sqlite3
MAIN_ADMIN_ID = 1155076760
conn = sqlite3.connect("users_database.db")
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER UNIQUE
    );
"""
)
cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MAIN_ADMIN_ID,))
conn.commit()
conn.close()
from aiogram.fsm.context import FSMContext

class RegistrationMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        user_id = None
        state: FSMContext = data.get("state")
        current_state = await state.get_state() if state else None

        if event.message:
            user_id = event.message.from_user.id
            command = event.message.text.strip().lower() if event.message.text else None
            if "/start" in command:
                return await handler(event, data)

        elif event.callback_query:
            user_id = event.callback_query.from_user.id

        if user_id:
            registered = is_user_registered(user_id)
            if not registered and current_state != "registration:pref_name" and current_state != "registration_game:pref1_name":
                if event.message:
                    await event.message.answer("Please register first by sending /start.")
                elif event.callback_query:
                    await event.callback_query.answer(
                        "Please register first by sending /start.", show_alert=True
                    )
                return
        return await handler(event, data)
def get_admins():
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    admins = [row[0] for row in cursor.fetchall()]
    conn.close()
    return admins
def admin_required():
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: types.Message, *args, **kwargs):
            admin_list = list(get_admins())
            user_id = message.from_user.id
            if not user_id in admin_list:
                await message.answer("Siz noto'g'ri buyruq yubordingiz!")
                return
            return await handler(message, *args, **kwargs)

        return wrapper
    return decorator
