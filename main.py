import asyncio
import logging
import sqlite3
import uuid
import hendlers
import register
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.deep_linking import create_start_link
from config import *
from keyboards.keyboard import get_main_menu, count_players, change_name
from states.state import registration, registration_game, new_game
from keyboards.inline import *
from db import *
from aiogram.types import Update
import admin_panel
import game.tournaments

MAIN_ADMIN_ID = 1155076760
conn = sqlite3.connect("users_database.db")
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users_database (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    registration_date TEXT, 
    nfgame TEXT
)
"""
)
cursor.execute("PRAGMA table_info(users_database);")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]

if "unity_coin" not in column_names:
    cursor.execute(
        """
        ALTER TABLE users_database
        ADD COLUMN unity_coin INTEGER DEFAULT 0
        """
    )
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS user_game_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    UNIQUE(user_id, game_id, message_id)
);
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS game_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    game_id TEXT,
    game_start_time TEXT,
    game_end_time TEXT,
    game_winner TEXT
)
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invitee_id INTEGER,
        game_id TEXT,
        players_cnt INTEGER,
        needed_players INTEGER,
        is_started INTEGER,
        current_turn_user_id INTEGER,  
        number_of_cards INTEGER,
        FOREIGN KEY(inviter_id) REFERENCES users_database(user_id),
        FOREIGN KEY(invitee_id) REFERENCES users_database(user_id),
        UNIQUE(inviter_id, invitee_id, game_id)
    )
    """
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER UNIQUE
    );
"""
)
cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MAIN_ADMIN_ID,))
cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS game_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            player_id TEXT,
            cards TEXT,
            last_cards TEXT,
            current_table TEXT, 
            real_bullet TEXT,
            blanks_count INTEGER,
            life_status TEXT,
            UNIQUE(game_id, player_id)
        )
    """
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS tournaments_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id TEXT,
    tournament_prize TEXT,
    tournament_start_time TEXT,
    tournament_end_time TEXT,
    tournament_register_start_time TEXT,
    tournament_register_end_time TEXT,
    tournament_winner TEXT,
    maximum_players INTEGER
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS tournament_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id TEXT,
    user_id INTEGER,
    UNIQUE(tournament_id, user_id)

)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS tournament_rounds_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id TEXT,
    round_number TEXT,
    round_user_id TEXT,
    group_number TEXT,
    round_winner TEXT,
    UNIQUE (tournament_id, round_number, group_number, round_user_id, round_winner)
)
"""
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS withdraw_options (
        three_month_premium TEXT,
        six_month_premium TEXT,
        twelve_month_premium TEXT,
        hundrad_stars TEXT,
        five_hundrad_stars TEXT,
        thousand_stars TEXT
    )
    """
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users_referral (
    user_id INTEGER PRIMARY KEY,
    referred_by INTEGER
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS unity_coin_referral (
    unity_coin_refferal INTEGER
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS game_coin_table (
    game_coin INTEGER DEFAULT 5
)
"""
)
cursor.execute("SELECT COUNT(*) FROM unity_coin_referral")
count = cursor.fetchone()[0]
if count == 0:
    cursor.execute("INSERT INTO unity_coin_referral (unity_coin_refferal) VALUES (10)")

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS excludeds (
    game_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    number_of_excluded INTEGER DEFAULT 0,
    UNIQUE(game_id, user_id)
);
"""
)
cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS daily_bonus (
            user_id INTEGER PRIMARY KEY,
            last_claim TEXT
        )
        """
)
# cursor.execute("DELETE FROM tournament_rounds_users;")
# cursor.execute("DELETE FROM tournament_users;")
# cursor.execute("DELETE FROM tournaments_table;")
conn.commit()
conn.close()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    payload = message.text.split(" ", 1)[-1] if " " in message.text else ""
    await state.update_data(payload=payload)
    if "game_" in payload:
        if not is_user_registered(message.from_user.id):
            await message.answer(
                "Welcome to the bot! Please enter your username.\n\n"
                "⚠️ Note: Your username must be UNIQUE and can only contain:\n"
                "- Latin alphabet characters (a-z, A-Z)\n"
                "- Numbers (0-9)\n"
                "- Underscores (_)\n"
                "and you can use up to 30 characters"
            )
            await state.set_state(registration_game.pref1_name)
            return
        game_id = payload.split("game_")[1]
        if get_player_count(game_id) == 0:
            await message.answer(
                f"Game has already finished or been stopped. ☹️",
                reply_markup=get_main_menu(message.from_user.id),
            )
            return
        if game_id == get_game_id_by_user(message.from_user.id):
            if message.from_user.id == get_game_inviter_id(game_id):
                await message.answer(
                    "You are already in this game as a creator",
                    reply_markup=get_main_menu(message.from_user.id),
                )
            else:
                await message.answer(
                    "You are already in this game! 😇", reply_markup=cancel_g
                )
            return
        if get_needed_players(game_id) <= get_player_count(game_id):
            await message.answer(
                f"There is no available space for another player or the game has already finished 😞",
                reply_markup=get_main_menu(message.from_user.id),
            )

            await state.clear()
            return
        user = message.from_user
        inviter_id = get_game_inviter_id(game_id)
        if not inviter_id:
            await message.answer(
                f"This game has finished or been stopped by the creator.",
                reply_markup=get_main_menu(user.id),
            )
            await state.clear()
            return
        if inviter_id and inviter_id == user.id:
            await message.answer("You are already in this game as the creator!")
            return
        if is_user_in_game(game_id, user.id):
            await message.answer("You are already in this game!", reply_markup=cancel_g)
            return
        if not inviter_id:
            await message.answer(
                f"This game has finished or been stopped by the creator.",
                reply_markup=get_main_menu(user.id),
            )

            await state.clear()
            return
        if has_incomplete_games(message.from_user.id):
            await message.answer(
                f"You have incomplete games! \nPlease stop them first and try again.",
                reply_markup=stop_incomplete_games,
            )

            await state.clear()
            return
        insert_invitation(inviter_id, user.id, game_id)
        player_count = get_player_count(game_id)
        if player_count < 2:
            await message.answer(
                f"This game has finished or been stopped by the creator.",
                reply_markup=get_main_menu(user.id),
            )
            await state.clear()
            return

        await message.answer(
            f"You have successfully joined the game! 🤩\nCurrent number of players: {player_count}\nWaiting for everyone to be ready...",
            reply_markup=cancel_g,
        )

        name = get_user_nfgame(user.id)
        await bot.send_message(
            inviter_id,
            f"User {name} has joined the game!\nPlayers in the game: {player_count}",
        )
        if get_needed_players(game_id) == get_player_count(game_id):
            await bot.send_message(
                inviter_id,
                f"All players ready. You can start the game right now.",
                reply_markup=start_stop_game,
            )
        await state.clear()
    else:
        user = message.from_user
        if is_user_registered(user.id):
            await message.answer(
                "Welcome back! You are in the main menu.",
                reply_markup=get_main_menu(user.id),
            )
        else:
            await message.answer(
                "Welcome to the bot! Please enter your username.\n\n"
                "⚠️ Note: Your username must be UNIQUE and can only contain:\n"
                "- Latin alphabet characters (a-z, A-Z)\n"
                "- Numbers (0-9)\n"
                "- Underscores (_)\n"
                "and you can use up to 30 characters"
            )
            await state.set_state(registration.pref_name)


@dp.message(F.text == "start game 🎮")
async def start_game_handler(message: types.Message, state: FSMContext):
    if is_user_in_tournament_and_active(message.from_user.id):
        await message.answer(
            f"You are participating in a tournament and can't use this button until the tournament ends!"
        )
        return
    if message.chat.type == "private":
        if has_incomplete_games(message.from_user.id):
            await message.answer(
                "You have incomplete games. Please finish or stop them before creating a new one.",
                reply_markup=stop_incomplete_games,
            )

            return
        await message.answer(
            "Choose the number of players: ⬇️", reply_markup=count_players
        )
        await state.set_state(new_game.number_of_players)
    else:
        await message.answer("Please use this option in a private chat.")


@dp.message(F.text == "back to main menu 🔙")
async def start_game_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"You are in main manu.",
        reply_markup=get_main_menu(message.from_user.id),
    )


@dp.message(new_game.number_of_players)
async def get_name(message: types.Message, state: FSMContext):
    cnt = 0
    if message.text == "2️⃣":
        cnt = 2
    elif message.text == "3️⃣":
        cnt = 3
    elif message.text == "4️⃣":
        cnt = 4
    else:
        await message.answer(
            "You have entered wrong information! Please choose one of these numbers: ⬇️",
            reply_markup=count_players,
        )
        await state.set_state(new_game.number_of_players)
        return

    user = message.from_user
    game_id = str(uuid.uuid4())
    invite_link = await create_start_link(bot, payload=f"game_{game_id}")
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO invitations (inviter_id, game_id, needed_players)
        VALUES (?, ?, ?)
        """,
        (user.id, game_id, cnt),
    )
    conn.commit()
    conn.close()
    await message.answer(
        f"Here is your invitation link. Share this link with your friends to play the game together👇. Game starts as soon as {cnt} players gathered.",
        reply_markup=get_main_menu(user.id),
    )

    sharable_message = (
        "🎮 **Join the Game!** 🎮\n\n"
        "I just created a game, and I'd love for you to join!\n\n"
        "Click the link below to join the game:\n"
        f"\n{invite_link}\n\n"
    )

    await message.answer(
        sharable_message,
    )
    await state.clear()


# @dp.message(F.text == "game status 🌟")
# async def start_game_handler(message: types.Message, state: FSMContext):
#     if is_user_in_tournament_and_active(message.from_user.id):
#         await message.answer(f"You are participating in a tournament and can't use this button until the tournament ends!")
#         return
#     game_id = get_game_id_by_user(message.from_user.id)
#     if not has_incomplete_games(message.from_user.id):
#         await message.answer(
#             f"You are not participating in any game currently.",
#             reply_markup=get_main_menu(message.from_user.id),
#         )
#     else:
#         msg = f"Current game status: active ✅\n"
#         if message.from_user.id == get_game_inviter_id(game_id):
#             msg += f"You are creator of this game 👨‍💻\nNumber of participants: {get_player_count(game_id)}"
#             await message.answer(msg, reply_markup=generate_exclude_keyboard(game_id))
#         else:
#             msg += f"You are participant in this game 👤\nNumber of participants: {get_player_count(game_id)}"
#             await message.answer(msg, reply_markup=cancel_g)


@dp.message()
async def any_word(msg: types.Message):
    await msg.answer(f"You entered unfamiliar information.")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
