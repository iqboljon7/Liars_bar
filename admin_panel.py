import sqlite3
from aiogram import types
from aiogram.fsm.context import FSMContext
from middlewares.registered import admin_required
from keyboards.keyboard import *
from config import *
from db import *
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from states.state import *
from hendlers import get_user_game_archive
from datetime import datetime, timedelta
from aiogram.types import Message, ChatInviteLink
from keyboards.inline import generate_courses_keyboard

# from aiogram.utils.markdown import mention


def generate_callback(action: str, admin_id: int) -> str:
    return f"{action}:{admin_id}"


def get_admins2():
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    admins = [
        {"id": row[0], "name": f"{get_user_nfgame(row[0])}"}
        for row in cursor.fetchall()
    ]
    conn.close()
    return admins


def get_statistics():
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users_database")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT game_id) FROM game_archive")
    total_games = cursor.fetchone()[0]

    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime(
        "%Y-%m-%d"
    )
    cursor.execute(
        "SELECT COUNT(*) FROM users_database WHERE registration_date >= ?",
        (week_start,),
    )
    users_joined_this_week = cursor.fetchone()[0]

    # Number of tournaments ended
    cursor.execute(
        "SELECT COUNT(*) FROM tournaments_table WHERE tournament_end_time <= datetime('now',  '+5 hours')"
    )
    tournaments_ended = cursor.fetchone()[0]

    # Number of upcoming tournaments
    cursor.execute(
        "SELECT COUNT(*) FROM tournaments_table WHERE tournament_start_time > datetime('now',  '+5 hours')"
    )
    upcoming_tournaments = cursor.fetchone()[0]

    # Create the statistics message
    stats_message = (
        "📊 *Game Statistics*\n\n"
        f"👥 *Total Users:* {total_users}\n"
        f"🎮 *Total Games Played:* {total_games}\n"
        f"🆕 *Users Joined This Week:* {users_joined_this_week}\n"
        f"🏁 *Tournaments Ended:* {tournaments_ended}\n"
        f"⏳ *Upcoming Tournaments:* {upcoming_tournaments}\n"
    )

    conn.close()
    return stats_message


@dp.message(F.text == "📊 statistics")
@admin_required()
async def main_to_menu(message: types.Message, state: FSMContext):
    try:
        stats_message = get_statistics()
        await message.answer(stats_message, parse_mode="Markdown")
    except Exception as e:
        await message.answer("❌ An error occurred while fetching statistics.")
        print(f"Error: {e}")


USERS_PER_PAGE = 10


def generate_user_list(users, page):
    start_index = (page - 1) * USERS_PER_PAGE
    end_index = start_index + USERS_PER_PAGE
    page_users = users[start_index:end_index]

    user_list = []
    for index, (user_id, nfgame) in enumerate(page_users, start=start_index + 1):
        user_list.append(
            f"{index}. <a href='tg://openmessage?user_id={user_id}'>{user_id}</a> — {nfgame}"
        )

    return user_list


def create_pagination_buttons(page, total_users):
    keyboard = []
    if page > 1:
        keyboard.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"page_{page - 1}")
        )
    if page * USERS_PER_PAGE < total_users:
        keyboard.append(
            InlineKeyboardButton(text="➡️", callback_data=f"page_{page + 1}")
        )
    return InlineKeyboardMarkup(inline_keyboard=[keyboard])


def get_user_statistics(user_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT username, first_name, last_name, registration_date, nfgame, unity_coin
            FROM users_database WHERE user_id = ? OR nfgame = ?
            """,
            (user_id, user_id),
        )
        user_data = cursor.fetchone()
        if not user_data:
            return "❌ No user found with the given ID."
        username, first_name, last_name, registration_date, nfgame, unity_coin = (
            user_data
        )
        is_admin = "admin 🧑‍💻" if is_user_admin(user_id) else "user 🙍‍♂️"

        stats_message = (
            f"📊 User Statistics 📊\n\n"
            f"🙇‍♂️ Role: {is_admin} \n\n"
            f"👤 Username: {"@" + username if username else 'N/A'}\n\n"
            f"📛 First Name: {first_name if first_name else 'N/A'}\n\n"
            f"📜 Last Name: {last_name if last_name else 'N/A'}\n\n"
            f"🗓️ Registr Date: {registration_date if registration_date else 'N/A'}\n\n"
            f"🎮 Username in bot: {nfgame if nfgame else 'N/A'}\n\n"
            f"👥 referrals: {get_number_of_referrals(user_id)}\n\n"
            f"💰 Unity Coins: {unity_coin}"
        )

    except sqlite3.Error as e:
        stats_message = f"❌ Database error occurred: {e}"
    finally:
        conn.close()

    return stats_message


@dp.message(F.text == "🔙 main menu")
@admin_required()
async def main_to_menu(message: types.Message, state: FSMContext):
    await message.answer(
        f"You are in main menu.", reply_markup=get_main_menu(message.from_user.id)
    )


@dp.message(F.text == "🧑‍💻 admin panel")
@admin_required()
async def admin_panel(message: types.Message):
    await message.answer("You are in admin panel ⬇️", reply_markup=admin_panel_button)


@dp.message(F.text == "cancel 🚫")
@admin_required()
async def cancel_butt(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Action is canceled. ✔️You are in admin panel ⬇️",
        reply_markup=admin_panel_button,
    )


@dp.message(F.text == "back to admin panel 🔙")
@admin_required()
async def back_buttton(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(f"You are in admin panel ⬇️", reply_markup=admin_panel_button)


@dp.message(F.text == "👤 Admins")
@admin_required()
async def admins_button(message: types.Message):
    await message.answer(
        f"In this section, you can add, delete admins or see the list of them. ",
        reply_markup=admins_list_button,
    )


@dp.message(F.text == "➕ add admin")
@admin_required()
async def add_admin_command(message: types.Message, state: FSMContext):
    await message.answer(
        f"Enter the ID of the user that you want to make admin",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(Adminid.admin_id)


@dp.message(Adminid.admin_id)
async def add_admin_state(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    i_d = message.text.strip()
    if not i_d.isdigit():
        await message.answer(
            f"❌ You entered wrong information. Please try again.",
            reply_markup=back_to_admin_panel,
        )
    elif not is_user_registered(i_d):
        await message.answer(
            f"❌ User not found or is not membor of the bot",
            reply_markup=admin_panel_button,
        )
        await state.clear()
    else:
        try:
            user_id = int(message.text.strip())
            add_admin(user_id)
            await message.answer(
                f"✅ User {user_id} has been added as an admin.",
                reply_markup=admin_panel_button,
            )
            await bot.send_message(
                chat_id=user_id,
                text="You are given an admin ✅",
                reply_markup=get_main_menu(user_id),
            )
            await state.clear()
        except ValueError:
            await message.answer(
                "❌ You entered wrong information. Please try again.",
                reply_markup=back_to_admin_panel,
            )
        await state.clear()


@dp.message(F.text == "🧾 list of admins")
@admin_required()
async def list_admins(message: types.Message):
    admins = get_admins2()
    keyboard = InlineKeyboardBuilder()
    for admin in admins:
        callback_data = generate_callback("delete_admin", admin["id"])
        keyboard.row(
            InlineKeyboardButton(
                text=f"❌ {admin['name']}",
                callback_data=callback_data,
            )
        )
    await message.answer(
        "Here is the list of admins:", reply_markup=keyboard.as_markup()
    )


@dp.callback_query(F.data.startswith("delete_admin"))
async def delete_admin_callback(query: types.CallbackQuery):
    callback_data = query.data.split(":")
    action = callback_data[0]
    admin_id = int(callback_data[1])

    if int(query.from_user.id) != 1155076760 and int(query.from_user.id) != 6807731973:
        await query.answer(
            f"You can not delete admin's because you are not the main admin ❗️"
        )
        return
    elif admin_id in [1155076760, 6807731973]:
        await query.answer(f"It is not possible to delete main admins.")
    else:
        if action == "delete_admin":
            conn = sqlite3.connect("users_database.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admins WHERE user_id = ?", (admin_id,))
            conn.commit()
            conn.close()
            await query.answer("Admin was deleted successfully.")

            conn = sqlite3.connect("users_database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM admins")
            remaining_admins = [get_user_nfgame(row[0]) for row in cursor.fetchall()]
            conn.close()
            keyboard_builder = InlineKeyboardBuilder()
            for admin in remaining_admins:
                keyboard_builder.button(
                    text=f"❌ {admin}", callback_data=f"delete_admin:{admin}"
                )
            keyboard = keyboard_builder.as_markup()
            await query.message.edit_reply_markup(reply_markup=keyboard)


@dp.message(F.text == "📤 send message")
@admin_required()
async def choose_send_option(message: types.Message, state: FSMContext):
    await message.answer(
        "Here you can send a message anonymously.\nChoose one of these options ⏬",
        reply_markup=send_messages,
    )


@dp.message(F.text == "📨 send message to all")
@admin_required()
async def send_to_all_anonymously(message: types.Message, state: FSMContext):
    await message.answer(
        "Send me the message in *English* 📝",
        reply_markup=back_to_admin_panel,
        parse_mode="Markdown",
    )
    await state.set_state(msgtoall.english)


@dp.message(msgtoall.english)
async def get_english_message(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return

    await state.update_data(english=message.text)
    await message.answer(
        "Now send me the message in *Russian* 🇷🇺", parse_mode="Markdown"
    )
    await state.set_state(msgtoall.russian)


@dp.message(msgtoall.russian)
async def get_russian_message(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return

    await state.update_data(russian=message.text)
    await message.answer(
        "Finally, send me the message in *Uzbek* 🇺🇿", parse_mode="Markdown"
    )
    await state.set_state(msgtoall.uzbek)


@dp.message(msgtoall.uzbek)
async def get_uzbek_message(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return

    await state.update_data(uzbek=message.text)
    data = await state.get_data()
    english_text = data.get("english")
    russian_text = data.get("russian")
    uzbek_text = data.get("uzbek")

    users = get_all_user_ids()
    cnt = 0
    for user_id in users:
        try:
            user_lang = get_user_language(user_id)
            if user_lang == "ru":
                msg_text = russian_text
            elif user_lang == "uz":
                msg_text = uzbek_text
            else:
                msg_text = english_text

            await bot.send_message(
                user_id, msg_text, reply_markup=get_main_menu(user_id)
            )

        except Exception:
            cnt += 1
            continue

    await message.answer(
        f"Message was forwarded anonymously to {len(users) - cnt} users from {len(users)} successfully ✅",
        reply_markup=admin_panel_button,
    )
    await state.clear()


@dp.message(F.text == "📩 send message to one")
@admin_required()
async def send_to_one_anonymously(message: types.Message, state: FSMContext):
    await message.answer(
        "Enter the ID of the user you want to send the message to 📝",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(msgtoindividual.userid)


@dp.message(msgtoindividual.userid)
async def capture_user_id(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    user_id = message.text.strip()
    if not user_id.isdigit():
        await message.answer("❌ You entered an invalid ID. Please try again.")
        return
    user_id = int(user_id)
    if user_id == message.from_user.id:
        await message.answer(
            "You cannot send a message to yourself.",
            reply_markup=admin_panel_button,
        )
        await state.clear()
        return
    await state.update_data(userid=user_id)
    await message.answer("Now send me the message or post to forward anonymously 📝")
    await state.set_state(msgtoindividual.sendtoone)


@dp.message(msgtoindividual.sendtoone)
async def forward_to_individual(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = int(data["userid"])

    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await message.answer(
            "Message was forwarded anonymously to the user successfully ✅",
            reply_markup=admin_panel_button,
        )
    except Exception as e:
        await message.answer(
            f"An error occurred while sending the message: {e}",
            reply_markup=admin_panel_button,
        )
    finally:
        await state.clear()


@dp.message(F.text == "🧑‍🎓 users")
@admin_required()
async def users_butn(message: types.Message):
    await message.answer(
        f"In this section, you can get information of users.",
        reply_markup=users_control_button,
    )


@dp.message(F.text == "🪪 List of users")
@admin_required()
async def list_users(message: types.Message):
    try:
        with sqlite3.connect("users_database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, nfgame FROM users_database")
            users = cursor.fetchall()
    except sqlite3.Error as e:
        await message.answer("An error has occured ...")
        return

    async def show_users(page=1):
        user_list = generate_user_list(users, page)
        user_details = "\n".join(user_list)
        pagination_buttons = create_pagination_buttons(page, len(users))
        await message.answer(
            f"Here is the list of users (page {page}):\n\n{user_details}",
            parse_mode="HTML",
            reply_markup=pagination_buttons,
        )

    await show_users(page=1)


@dp.callback_query(lambda c: c.data.startswith("page_"))
async def paginate_users(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split("_")[1])
    try:
        with sqlite3.connect("users_database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, nfgame FROM users_database")
            users = cursor.fetchall()
    except sqlite3.Error as e:
        print(e)
        await callback_query.answer(
            "An error has occured, please try again later", show_alert=True
        )
        return
    if page < 1 or (page - 1) * USERS_PER_PAGE >= len(users):
        await callback_query.answer(
            "You are in the first page!" if page < 1 else "You are in the last page!",
            show_alert=True,
        )
        return

    user_list = generate_user_list(users, page)
    user_details = "\n".join(user_list)
    pagination_buttons = create_pagination_buttons(page, len(users))
    await callback_query.message.edit_text(
        f"List of users (page {page}):\n\n{user_details}",
        parse_mode="HTML",
        reply_markup=pagination_buttons,
    )
    await callback_query.answer()


@dp.message(F.text == "🗒 information of user")
@admin_required()
async def info_users(message: types.Message, state: FSMContext):
    await message.answer(
        f"Enter the ID or username of the user that you want to get information",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(UserInformations.userid_state)


@dp.message(UserInformations.userid_state)
@admin_required()
async def state_info_users(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    if not message.text.isdigit():
        user_id = get_id_by_nfgame(message.text)
        if not user_id:
            await message.answer(
                "❌ Please send a valid user ID or username",
                reply_markup=back_to_admin_panel,
            )
        else:
            user_id = int(user_id)
    else:
        user_id = int(message.text)
    if not is_user_registered(user_id):
        await message.answer(
            f"No user found from given ID ☹️",
            reply_markup=admin_panel_button,
        )
    else:
        await message.answer(
            get_user_statistics(user_id),
            reply_markup=admin_panel_button,
        )
    await state.clear()


@dp.message(F.text == "🎯 Game archive")
@admin_required()
async def admin_game_archive(message: types.Message, state: FSMContext):
    await message.answer(
        "Please send me the user ID or username to view their game archive 📋.",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(awaiting_user_id.await_id)


@dp.message(awaiting_user_id.await_id)
async def get_user_archive_by_id(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    if not message.text.isdigit():
        user_id = get_id_by_nfgame(message.text)
        if not user_id:
            await message.answer(
                "❌ Please send a valid user ID or username",
                reply_markup=back_to_admin_panel,
            )
    else:
        user_id = int(message.text)
    games = get_user_game_archive(user_id)
    if not games:
        await message.answer(
            "No games found for this user.", reply_markup=admin_panel_button
        )
        await state.clear()
        return

    response = f"📜 Game Archive for User {user_id}:*n\n"
    for idx, (_, start_time, _, _) in enumerate(games, start=1):
        response += f"{idx}. game — {start_time.split(' ')[0]} 📅\n"

    response += "\n📋 *Send the game number to view its details.*"
    await message.answer(response, reply_markup=back_to_admin_panel)
    await state.update_data(selected_user_id=user_id)
    await state.set_state(awaiting_admin_game_number.selected_user)


@dp.message(awaiting_admin_game_number.selected_user)
async def send_selected_user_game_statistics(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    data = await state.get_data()
    user_id = data.get("selected_user_id")
    games = get_user_game_archive(user_id)
    if not message.text.isdigit():
        await message.answer(
            "❌ Please send a valid game number.", reply_markup=back_to_admin_panel
        )

    game_number = int(message.text)
    if game_number < 1 or game_number > len(games):
        await message.answer(
            "❌ Invalid game number. Please try again.",
            reply_markup=back_to_admin_panel,
        )
    record_id, start_time, end_time, winner = games[game_number - 1]
    game_status = (
        f"🕹 *Game Details:*\n"
        f"🆔 Game ID: {record_id}\n"
        f"⏰ Start Time: {start_time}\n"
        f"🏁 End Time: {end_time if end_time else 'Has not finished'}\n"
        f"🏆 Winner: {winner if winner else 'No Winner'}"
    )
    await message.answer(
        game_status, parse_mode="Markdown", reply_markup=back_to_admin_panel
    )


from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


@dp.message(F.text == "🚫 delete the tournament")
@admin_required()
async def delete_tournament_handler(message: types.Message):
    upcoming_tournament = get_upcoming_tournaments()
    if upcoming_tournament:
        tournament = upcoming_tournament[0]
        if "_" in tournament["name"]:
            nop = get_current_players(tournament["name"].split("_")[1])
        else:
            nop = get_current_players(tournament["name"])
        tournament_id = tournament["name"]
        response = (
            f"🌟 Tournament ID: {tournament['id']}\n\n"
            f"🗓 Starts: {tournament['start_time']}\n"
            f"🏁 Ends: {tournament['end_time']}\n\n"
            f"🗓 Registration starts: {tournament['register_start']}\n"
            f"🏁 Registration ends: {tournament['register_end']}\n\n"
            f"👥 Registered Players: {nop}\n"
            f"🏆 Prize: \n\n{tournament['prize']}\n\n"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Yes", callback_data=f"confirm_delete:{tournament_id}"
                    ),
                    InlineKeyboardButton(text="❌ No", callback_data="cancel_delete"),
                ]
            ]
        )
        await message.answer(response, reply_markup=keyboard)
    else:
        await message.reply("There is no upcoming tournament to delete.")


@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete_tournament(callback_query: types.CallbackQuery):
    await asyncio.sleep(1)
    await callback_query.message.answer(
        "Tournament deletion has been canceled.",
        reply_markup=ongoing_tournaments_button,
    )
    await callback_query.message.delete()


@dp.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_tournament(callback_query: types.CallbackQuery):
    tournament_id = callback_query.data.split(":")[1]

    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT user_id FROM tournament_users WHERE tournament_id = ?
            """,
            (tournament_id,),
        )
        registered_users = cursor.fetchall()
    finally:
        conn.close()

    delete_tournament(tournament_id)
    await callback_query.message.delete()

    for user in registered_users:
        try:
            ln = get_user_language(user[0])
            if ln == "uz":
                ms = "⚠️ Siz roʻyxatdan oʻtgan turnir bekor qilindi. Noqulaylik uchun uzr so'raymiz. 😕"
            elif ln == "ru":
                ms = "⚠️ Турнир, на который вы зарегистрировались, был отменен. Приносим извинения за возможные неудобства. 😕"
            else:
                ms = "⚠️ The tournament you registered has been canceled. We apologize for any inconvenience. 😕"
            await bot.send_message(chat_id=user[0], text=ms)
        except Exception as e:
            print(f"Failed to send message to user {user[0]}: {e}")

    await callback_query.message.answer(
        f"Tournament has been deleted. ✅\nYou are in tournaments section 👇",
        reply_markup=tournaments_admin_panel_button,
    )


@dp.message(F.text == "💳 user's balance")
@admin_required()
async def users_balance(message: types.Message, state: FSMContext):
    await message.answer(
        f"Here you can do changes with users' balances 👇",
        reply_markup=users_balance_button,
    )


@dp.message(F.text == "➕ Add Unity Coins to All Users")
@admin_required()
async def add_unity_coins_to_all(message: types.Message, state: FSMContext):
    await message.answer(
        "Please enter the amount of Unity Coins you want to add to all users:",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(waiting_for_coin_amount.unity_coin_amount)


@dp.message(waiting_for_coin_amount.unity_coin_amount)
@admin_required()
async def process_coin_amount(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            f"You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    try:
        coin_amount = int(message.text.strip())
    except ValueError:
        await message.answer(
            "Please enter a valid number of Unity Coins.",
            reply_markup=back_to_admin_panel,
        )
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users_database")
    user_ids = cursor.fetchall()
    conn.close()
    if not user_ids:
        await message.answer("No users found in the database.")
        return
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    for user_id in user_ids:
        cursor.execute(
            "UPDATE users_database SET unity_coin = unity_coin + ? WHERE user_id = ?",
            (coin_amount, user_id[0]),
        )
    conn.commit()
    conn.close()
    await message.answer(
        f"✅ Successfully added {coin_amount} Unity Coins to all users.",
        reply_markup=users_balance_button,
    )
    await state.clear()


@dp.message(F.text == "👀 View User Unity Coins")
@admin_required()
async def view_users_balance(message: types.Message, state: FSMContext):
    await message.answer(
        "Please provide the user ID or username to view the Unity coin balance.",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(waiting_for_user_id_or_username.waiting_amount)


@dp.message(waiting_for_user_id_or_username.waiting_amount)
async def handle_user_input_for_balance(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            f"You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    user_input = message.text.strip()
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, nfgame, unity_coin FROM users_database WHERE user_id = ? OR nfgame = ?",
        (user_input, user_input),
    )
    user = cursor.fetchone()

    if user:
        global username
        user_id, username, unity_coin = user
        await message.answer(
            f"📊 User Information: \n\n"
            f"👤 Username: {username}\n"
            f"💰 Unity Coins: {unity_coin}\n"
            f"🆔 User ID: {user_id}\n\n"
            "Choose an action below:",
            reply_markup=change_users_balance,
        )
        await state.clear()

    else:
        await message.answer("❌ User not found. :(", reply_markup=users_balance_button)
        await state.clear()
        return


@dp.message(F.text == "➕ Add Unity Coins")
@admin_required()
async def add_unity_coins(message: types.Message, state: FSMContext):
    if username:
        await message.answer(
            "Please provide the amount of Unity coins to add.",
            reply_markup=back_to_admin_panel,
        )
        await state.set_state(
            waiting_for_user_id_or_username.waiting_for_add_coin_amount
        )
    else:
        await message.answer(
            "❌ No user selected. Please try again.", reply_markup=back_to_admin_panel
        )


@dp.message(waiting_for_user_id_or_username.waiting_for_add_coin_amount)
async def handle_add_unity_coins(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            f"You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    try:
        add_amount = int(message.text.strip())
        if add_amount <= 0:
            await message.answer(
                "❌ The amount must be greater than 0.",
                reply_markup=back_to_admin_panel,
            )
            return
        conn = sqlite3.connect("users_database.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users_database SET unity_coin = unity_coin + ? WHERE user_id = ? or nfgame = ?",
            (add_amount, username, username),
        )
        conn.commit()
        conn.close()

        await message.answer(
            f"✅ {add_amount} Unity Coins have been added to the user's balance!",
            reply_markup=change_users_balance,
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "❌ Please provide a valid number for Unity coins.",
            reply_markup=back_to_admin_panel,
        )


@dp.message(F.text == "➖ Subtract Unity Coins")
@admin_required()
async def subtract_unity_coins(message: types.Message, state: FSMContext):
    if username:
        await message.answer(
            "Please provide the amount of Unity coins to subtract.",
            reply_markup=back_to_admin_panel,
        )
        await state.set_state(
            waiting_for_user_id_or_username.waiting_for_subtract_coin_amount
        )
    else:
        await message.answer(
            "❌ No user selected. Please try again.", reply_markup=back_to_admin_panel
        )


@dp.message(waiting_for_user_id_or_username.waiting_for_subtract_coin_amount)
async def handle_subtract_unity_coins(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            f"You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    if not message.text.isdigit():
        await message.answer(
            f"Please enter correct number !", reply_markup=back_to_admin_panel
        )
    else:
        subtract_amount = int(message.text.strip())
        if subtract_amount <= 0:
            await message.answer(
                "❌ The amount must be greater than 0.",
                reply_markup=change_users_balance,
            )
            await state.clear()
            return
        conn = sqlite3.connect("users_database.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users_database SET unity_coin = unity_coin - ? WHERE user_id = ? or nfgame = ?",
            (subtract_amount, username, username),
        )
        conn.commit()
        conn.close()

        await message.answer(
            f"✅ {subtract_amount} Unity Coins have been subtracted from the user's balance!",
            reply_markup=change_users_balance,
        )
        await state.clear()


@dp.message(F.text == "/stop_all_incomplete_games")
@admin_required()
async def stop_all_incomplete_games_command(message: types.Message, state: FSMContext):
    users = get_all_user_ids()

    for userid in users:
        try:
            delete_user_from_all_games(userid)
        except:
            continue
    await message.answer(f"All users' incomplete games has been stopped ✅")


@dp.message(F.text == "💰 withdraw change")
@admin_required()
async def show_withdraw_options(message: types.Message):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM withdraw_options LIMIT 1")
    withdraw_options = cursor.fetchone()
    if not withdraw_options:
        await message.answer("❌ No withdrawal options found.")
        conn.close()
        return

    (
        three_month_premium,
        six_month_premium,
        twelve_month_premium,
        hundrad_stars,
        five_hundrad_stars,
        thousand_stars,
    ) = withdraw_options
    conn.close()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"❄️ 3 Months", callback_data="change_3_month"
                ),
                InlineKeyboardButton(
                    text=f"⭐ 100 Stars", callback_data="change_100_stars"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"❄️ 6 Months", callback_data="change_6_month"
                ),
                InlineKeyboardButton(
                    text=f"⭐ 500 Stars", callback_data="change_500_stars"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"❄️ 12 Months", callback_data="change_12_month"
                ),
                InlineKeyboardButton(
                    text=f"⭐ 1,000 Stars", callback_data="change_1000_stars"
                ),
            ],
        ]
    )
    withdraw_message = (
        "💰 *Withdrawal change section.*\n\n"
        f"🚀 *Telegram Premium*\n"
        f"❄️ *3 Months*: {three_month_premium} Unity Coins 💰\n"
        f"❄️ *6 Months*: {six_month_premium} Unity Coins 💰\n"
        f"❄️ *12 Months*: {twelve_month_premium} Unity Coins 💰\n\n"
        f"⭐️ *Telegram Stars* \n"
        f"✨ *100 Stars*: {hundrad_stars} Unity Coins 💰\n"
        f"✨ *500 Stars*: {five_hundrad_stars} Unity Coins 💰\n"
        f"✨ *1,000 Stars*: {thousand_stars} Unity Coins 💰\n\n"
        "Press a button to change the Unity Coins for each option 👇"
    )
    await message.answer(withdraw_message, parse_mode="Markdown", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("change_"))
async def change_withdraw_option(
    callback_query: types.CallbackQuery, state: FSMContext
):
    option = callback_query.data
    await callback_query.message.answer(
        f"💬 Please enter the new Unity Coins amount for {option.replace('change_', '').replace('_', ' ').title()}:",
        reply_markup=back_to_admin_panel,
    )
    await state.set_data({"option": option})
    await state.set_state(changeWithdraw.changee)


@dp.message(changeWithdraw.changee)
async def set_new_coin_amount(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    new_coin_amount = message.text.strip()
    if not new_coin_amount.isdigit():
        await message.answer(
            "❌ Please enter a valid number for the Unity Coins amount."
        )
        return
    new_coin_amount = int(new_coin_amount)
    data = await state.get_data()
    if not data:
        return
    option = data.get("option")
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        conn = sqlite3.connect("users_database.db")
        cursor = conn.cursor()

        if option == "change_3_month":
            cursor.execute(
                "UPDATE withdraw_options SET three_month_premium = ? WHERE rowid = 1",
                (new_coin_amount,),
            )
        elif option == "change_6_month":
            cursor.execute(
                "UPDATE withdraw_options SET six_month_premium = ? WHERE rowid = 1",
                (new_coin_amount,),
            )
        elif option == "change_12_month":
            cursor.execute(
                "UPDATE withdraw_options SET twelve_month_premium = ? WHERE rowid = 1",
                (new_coin_amount,),
            )
        elif option == "change_100_stars":
            cursor.execute(
                "UPDATE withdraw_options SET hundrad_stars = ? WHERE rowid = 1",
                (new_coin_amount,),
            )
        elif option == "change_500_stars":
            cursor.execute(
                "UPDATE withdraw_options SET five_hundrad_stars = ? WHERE rowid = 1",
                (new_coin_amount,),
            )
        elif option == "change_1000_stars":
            cursor.execute(
                "UPDATE withdraw_options SET thousand_stars = ? WHERE rowid = 1",
                (new_coin_amount,),
            )

        conn.commit()
        conn.close()
        await message.answer(
            f"✅ The Unity Coins amount for {option.replace('change_', '').replace('_', ' ').title()} has been updated to {new_coin_amount} coins.",
            reply_markup=admin_panel_button,
        )
    except sqlite3.Error as e:
        await message.answer(f"❌ There was an error while updating the database: {e}")

    finally:
        await state.clear()


@dp.callback_query(lambda c: c.data.startswith("get_"))
async def process_withdraw_user(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    ln = get_user_language(user_id)
    option = callback_query.data
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM withdraw_options LIMIT 1")
    withdraw_options = cursor.fetchone()
    if not withdraw_options:
        await callback_query.answer("❌ No withdrawal options found.")
        conn.close()
        return
    (
        three_month_premium,
        six_month_premium,
        twelve_month_premium,
        hundrad_stars,
        five_hundrad_stars,
        thousand_stars,
    ) = withdraw_options
    conn.close()
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT unity_coin FROM users_database WHERE user_id = ?", (user_id,)
    )
    user_info = cursor.fetchone()

    if not user_info:
        await callback_query.answer("❌ You are not registered in the system.")
        conn.close()
        return

    user_unity_coins = user_info[0]
    cost = 0
    reward_name = ""

    if option == "get_3_month":
        cost = int(three_month_premium)
        reward_name = "🚀 3 Months Telegram Premium"
    elif option == "get_6_month":
        cost = int(six_month_premium)
        reward_name = "🚀 6 Months Telegram Premium"
    elif option == "get_12_month":
        cost = int(twelve_month_premium)
        reward_name = "🚀 12 Months Telegram Premium"
    elif option == "get_100_stars":
        cost = int(hundrad_stars)
        reward_name = "⭐️ 100 Stars"
    elif option == "get_500_stars":
        cost = int(five_hundrad_stars)
        reward_name = "⭐️ 500 Stars"
    elif option == "get_1000_stars":
        cost = int(thousand_stars)
        reward_name = "⭐️ 1,000 Stars"
    if ln == "uz":
        ms = f"❌ Bu mahsulotni olish uchun sizga yana {cost - user_unity_coins} Unity Coin kerak."
        vaqtincha = "Bu bo'limda texnik ishlar olib borilmoqda ... 😕"
        ms1 = f"💬 Siz tanlovingiz - {reward_name}! \nIltimos, mahsulotni jo'natmoqchi bo'lgan Telegram foydalanuvchisini usernameni kiriting:\n\n❗️ Agar username noto'g'ri kiritilgan bo'lsa, mahsulot yetkazilmasligini unitmang."
    elif ln == "ru":
        ms = f"❌ Вам нужно еще {cost - user_unity_coins} Unity Coin, чтобы получить этот предмет."
        vaqtincha = "В этом разделе ведутся технические работы... 😕"
        ms1 = f"💬 Вы выбрали - {reward_name}! \nПожалуйста, укажите имя пользователя Telegram, которому вы хотите отправить предмет:\n\n❗️Обратите внимание, что если имя пользователя введено неверно, ваша награда не будет выдана."
    else:
        ms = f"❌ You need {cost - user_unity_coins} more Unity Coins to get this item."
        vaqtincha = "This section is undergoing technical work... 😕"
        ms1 = f"💬 You selected - {reward_name}! \nPlease provide any Telegram username that you want to get item to:\n\n❗️Note that if the username you entered is incorrect, your reward won't be given."
    if user_unity_coins < cost:
        await callback_query.answer(
            ms,
            show_alert=True,
        )
        return
    await callback_query.answer(
        vaqtincha,
        show_alert=True,
    )
    return
    await callback_query.message.answer(ms1)
    await state.set_data({"reward_name": reward_name, "cost": cost})
    await state.set_state(waiting_for_username_withdraw.username_withdraw)


@dp.message(waiting_for_username_withdraw.username_withdraw)
async def get_username_for_withdraw(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    ln = get_user_language(user_id)
    username = message.text.strip()
    state_data = await state.get_data()
    reward_name = state_data["reward_name"]
    cost = state_data["cost"]
    if ln == "uz":
        confirmation_message = (
            f"💬 Iltimos quidagilarni to'g'ri ekanini tasdiqlang:\n\n"
            f"🎁 Mahsulot: {reward_name}\n"
            f"👤 Oluvchi foydalanuvchi: {username}\n"
            f"💰 Narx: {cost} Unity Coins\n\n"
            "To'g'riligini tasdiqlaysizmi ?"
        )
        tt = "Ha ✅"
        t1 = "Yo'q ❌"
    elif ln == "ru":
        confirmation_message = (
            f"💬 Пожалуйста, подтвердите данные для вывода средств.:\n\n"
            f"🎁 Название товара: {reward_name}\n"
            f"👤 Кому: {username}\n"
            f"💰 стоимость: {cost} Unity Coins\n\n"
            "Вы подтверждаете?"
        )
        tt = "Да ✅"
        t1 = "Нет ❌"
    else:
        confirmation_message = (
            f"💬 Please confirm your withdrawal details:\n\n"
            f"🎁 Item Name: {reward_name}\n"
            f"👤 To Who: {username}\n"
            f"💰 Cost: {cost} Unity Coins\n\n"
            "Do you confirm?"
        )
        tt = "✅ Yes"
        t1 = "❌ No"
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=tt, callback_data="confirm_withdraw"),
            ],
            [
                InlineKeyboardButton(text=t1, callback_data="cancel_withdraw"),
            ],
        ]
    )

    await message.answer(confirmation_message, reply_markup=keyboard)
    await state.set_data({"reward_name": reward_name, "cost": cost})
    await state.update_data(username=username)


@dp.callback_query(lambda c: c.data == "confirm_withdraw")
async def confirm_withdraw_queer(
    callback_query: types.CallbackQuery, state: FSMContext
):
    await bot.delete_message(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
    )
    user_id = callback_query.from_user.id
    state_data = await state.get_data()

    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT unity_coin FROM users_database WHERE user_id = ?", (user_id,)
    )
    user_info = cursor.fetchone()
    balance = user_info[0]
    conn.close()
    reward_name = state_data.get("reward_name")
    username = state_data.get("username")
    cost = state_data.get("cost")
    admin_channel_id = -1002261491678
    admin_message = (
        f"🛒 New Withdrawal Request\n\n"
        f"🎁 Item: {reward_name}\n"
        f"👤 To Who: {username}\n"
        f"💰 Cost: {cost} Unity Coins\n"
        f"🔢 User ID: {user_id}\n"
        f"💸 User's balance: {balance} Unity coins 💰"
    )
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT unity_coin FROM users_database WHERE user_id = ?", (user_id,)
    )
    user_info = cursor.fetchone()
    user_unity_coins = user_info[0]
    new_balance = user_unity_coins - cost
    cursor.execute(
        "UPDATE users_database SET unity_coin = ? WHERE user_id = ?",
        (new_balance, user_id),
    )
    conn.commit()
    conn.close()
    await bot.send_message(
        admin_channel_id,
        admin_message,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Confirm", callback_data=f"admin_confirm_{user_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Cancel", callback_data=f"admin_cancel_{user_id}"
                    )
                ],
            ]
        ),
    )
    ln = get_user_language(user_id)
    if ln == "uz":
        ms = "✅ Soʻrovingiz adminlarimizga muvaffaqiyatli yuborildi.\nU 24 soat ichida koʻrib chiqiladi."
    elif ln == "ru":
        ms = "✅ Ваш запрос на вывод средств был отправлен нашим администраторам.\nОн будет обработан в течение 24 часов."
    else:
        ms = "✅ Your withdrawal request has been submitted to our admins.\nIt will be processed within 24 hours."
    await callback_query.message.answer(ms)
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith("admin_confirm_"))
async def admin_confirm_withdraw(callback_query: types.CallbackQuery):
    await bot.delete_message(
        chat_id=-1002261491678, message_id=callback_query.message.message_id
    )
    user_id = callback_query.data.split("_")[-1]
    ln = get_user_language(user_id)
    if ln == "uz":
        ms = "✅ Coinlarni yechib olish boʻyicha soʻrovingiz tasdiqlandi! Buyurtmangiz siz tanlagan foydalanuvchiga muvaffaqiyatli yetkazib berildi."
    elif ln == "ru":
        ms = "✅ Ваш запрос на вывод средств подтвержден! Товар успешно доставлен выбранному вами пользователю."
    else:
        ms = "✅ Your withdrawal request has been confirmed! The item has been successfully delivered to the user you selected."
    await bot.send_message(user_id, ms)
    await callback_query.answer("✅ Withdrawal confirmed!")


@dp.callback_query(lambda c: c.data.startswith("admin_cancel_"))
async def admin_cancel_withdraw(callback_query: types.CallbackQuery):
    await bot.delete_message(
        chat_id=-1002261491678, message_id=callback_query.message.message_id
    )

    user_id = callback_query.data.split("_")[-1]
    ln = get_user_language(user_id)
    if ln == "uz":
        ms = "❌ Coinlarni yechib olish boʻyicha soʻrovingiz bekor qilindi."
    elif ln == "ru":
        ms = "❌ Ваш запрос на вывод средств был отменен."
    else:
        ms = "❌ Your withdrawal request was canceled."
    await bot.send_message(user_id, ms)
    await callback_query.answer("❌ Withdrawal canceled.")


@dp.callback_query(lambda c: c.data == "cancel_withdraw")
async def cancel_withdraw_queer(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
    )
    await callback_query.message.answer(f"You have canceled your order successfully ✅")
    await state.clear()


@dp.message(F.text == "👀 watch results")
@admin_required()
async def watch_results_f(message: types.Message):
    result = ""
    tournament = get_ongoing_tournaments()
    if not tournament:
        await message.answer(
            f"Tournamnet has already been finished.",
            reply_markup=tournaments_admin_panel_button,
        )
        return
    tournament_id = tournament[0]["name"]
    current_round = int(get_current_round_number(tournament_id))
    if int(current_round) == 0:
        for i in range(1, current_round + 1):
            result += get_round_results(tournament_id, i) + "\n"
        if not result:
            result = "No results yet."
        await message.answer(result)
    else:
        await message.answer(
            f"Tournament has already finished. You can see the results in an archive 📈",
            reply_markup=tournaments_admin_panel_button,
        )


@dp.message(F.text == "👨‍👩‍👦‍👦 refferals")
@admin_required()
async def referrals_section(message: types.Message):
    await message.answer(
        f"You are in referrals section 👇", reply_markup=referrals_section_buttons
    )


@dp.message(F.text == "🔝 Top referrals")
@admin_required()
async def referrals_top_referrals(message: types.Message):
    await message.answer(
        f"{get_top_referrals()}", reply_markup=referrals_section_buttons
    )


@dp.message(F.text == "🔄 change referral amount")
@admin_required()
async def change_referrals_t(message: types.Message, state: FSMContext):
    await message.answer(
        f"Current referral amount is {get_unity_coin_referral()} Unity Coins 💰\nWrite the new amount for referral ✍️:",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(waitforreferralamount.amount)


@dp.message(waitforreferralamount.amount)
async def change_referrals_state(message: types.Message, state: FSMContext):
    new_amount = message.text
    if not new_amount.isdigit():
        await message.answer(
            f"You entered wrong amount ‼️. Please, enter a valid number.",
            reply_markup=back_to_admin_panel,
        )
    elif int(new_amount) < 0:
        await message.answer(
            f"You can't enter negative numbers ‼️. Please, enter a valid intager.",
            reply_markup=back_to_admin_panel,
        )
    else:
        update_unity_coin_referral(int(new_amount))
        await message.answer(
            f"New referral amount is successfully set ✅",
            reply_markup=referrals_section_buttons,
        )


@dp.message(F.text == "⛹️ players")
@admin_required()
async def players_in_tournament(message: types.Message):
    tournament = get_ongoing_tournaments()
    if not tournament:
        await message.answer(
            f"No ongoing tournaments found or has already been finished.",
            reply_markup=tournaments_admin_panel_button,
        )
        return
    tournament_id = tournament[0]["name"]
    players = get_tournament_users_list(tournament_id)
    if not players:
        await message.answer("No players have joined the tournament yet.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for player_id in players:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🚫 Player {get_user_nfgame(player_id)}",
                    callback_data=f"remove_{player_id}",
                )
            ]
        )

    await message.answer(
        "Here is the list of players in the tournament:", reply_markup=keyboard
    )


@dp.message(F.text == "✏️ change amount")
@admin_required()
async def change_amounts_t(message: types.Message, state: FSMContext):
    await message.answer(
        f"Here you can change some values in the game 👇",
        reply_markup=change_amounts_buttons,
    )


@dp.message(F.text == "💸 change game coins")
@admin_required()
async def change_game_coin_t(message: types.Message, state: FSMContext):
    await message.answer(
        f"Current coin for each game is {get_game_coin()} Unity Coins 💰\nWrite the new amount ✍️:",
        reply_markup=back_to_admin_panel,
    )
    await state.set_state(waitforcoinamount.amount)


@dp.message(waitforcoinamount.amount)
async def change_game_coin_state(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    new_amount = message.text
    if not new_amount.isdigit():
        await message.answer(
            f"You entered wrong amount ‼️. Please, enter a valid number.",
            reply_markup=back_to_admin_panel,
        )
    elif int(new_amount) < 0:
        await message.answer(
            f"You can't enter negative numbers ‼️. Please, enter a valid intager.",
            reply_markup=back_to_admin_panel,
        )
    else:
        set_game_coin(int(new_amount))
        await message.answer(
            f"New game coin amount is successfully set ✅",
            reply_markup=admin_panel_button,
        )
        await state.clear()


@dp.message(F.text == "🔗 channels")
@admin_required()
async def channels_show_button(message: Message, state: FSMContext):
    await message.answer(
        f"Here what you can do with channels that people can earn coins for subscribing. ⭐️",
        reply_markup=channels_show_keyboards,
    )


@dp.message(F.text == "➕ Add channel")
@admin_required()
async def ask_for_channel_id(message: Message, state: FSMContext):
    await message.answer(
        "Please send me the channel username (e.g., @channelusername) or ID."
    )
    await state.set_state(AddChannelState.waiting_for_channel_id)


@dp.message(F.text == "🍿 show channels")
@admin_required()
async def show_courses(message: types.Message):
    keyboard = generate_courses_keyboard()
    if not keyboard.inline_keyboard:
        await message.answer(f"📭 No channels found.")
    else:
        await message.answer("📋 Here are the list of channels:", reply_markup=keyboard)


@dp.message(AddChannelState.waiting_for_channel_id)
async def save_channel(message: Message, state: FSMContext):
    channel_id = message.text.strip()

    try:
        if channel_id.isdigit():
            channel_id = "-100" + str(channel_id)
        chat = await bot.get_chat(channel_id)
        invite_link: ChatInviteLink = await bot.create_chat_invite_link(
            chat_id=channel_id,
            creates_join_request=False,
            expire_date=None,
            member_limit=None,
        )
        channel_link = invite_link.invite_link
        conn = sqlite3.connect("users_database.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO channel_earn (channel_id, channel_link) VALUES (?, ?)",
            (channel_id, channel_link),
        )
        conn.commit()
        await message.answer(
            f"✅ Channel successfully added!\n\n🔗 Invite Link: {channel_link}"
        )
        await state.clear()

    except Exception as e:
        e = str(e)
        if "UNIQUE" in e:
            await message.answer(
                f"❌ You have already added this channel!",
                reply_markup=channels_show_keyboards,
            )
        else:
            await message.answer(
                f"❌ Error {e}: Make sure the bot is an admin in the channel and has permission to create invite links!",
                reply_markup=channels_show_keyboards,
            )
        await state.clear()


@dp.message(F.text == "/start_double_trouble")
@admin_required()
async def ask_for_channel_id(message: Message, state: FSMContext):
    text_ru = (
        "🔥 *ДВОЙНАЯ ВЫГОДА: ВРЕМЯ ВЫИГРЫВАТЬ ПО-КРУПНОМУ!* 🔥\n\n"
        "🎉 *Внимание, игроки!* В течение следующих *60 минут* "
        "за каждую победу вы получите *ДВОЙНЫЕ Unity Coins!* "
        "_Это вдвое больше наград, вдвое больше веселья и_ "
        "_вдвое больше причин играть прямо СЕЙЧАС_! 🎮🔥\n\n"
        "⚔ *Твоя стратегия важна.* Твой момент важен. "
        "Твои *выигрыши? Безграничны!* 💰\n\n"
        "⏳ *Но поторопись!* Когда таймер дойдет до нуля, бонус исчезнет. ⏳\n\n"
        "🕒 *[ОСТАЛОСЬ ВРЕМЕНИ: *60 минут*]*\n\n"
        "🎭 *Обыграй.* 🃏 *Перехитри.* 🏆 *Побеждай.*"
    )
    text_uz = (
        "🔥 *2X VAQTI: ULKAN G‘ALABALARINI QO‘LGA KIRIT!* 🔥\n\n"
        "🎉 *Diqqat, o‘yinchilar!* Keyingi *60 daqiqa* ichida har bir g‘alabangiz "
        "uchun *2X Unity Coins* olasiz! _Bu — 2X mukofot, 2X zavq va hoziroq "
        "o‘ynash uchun ikki barobar sabab!_ 🎮🔥\n\n"
        "💰 *Strategiyangiz muhim. Vaqtingiz muhim. Yutuqlaringiz? Cheksiz.*\n\n"
        "⏳ *Lekin shoshiling!* Vaqt tugashi bilan bonus ham yo‘qoladi. ⏳\n\n"
        "🕒 *[QOLGAN VAQT: *60 daqiqa*]*\n\n"
        "🎭 *Hushyor bo‘l.* 🃏 *Ustun kel.* 🏆 *G‘alaba qil!*"
    )
    text_en = (
        "🔥 *DOUBLE TROUBLE: IT’S TIME TO WIN BIG!* 🔥\n\n"
        "🎉 *Attention, players!* For the next *60 minutes*, "
        "every game you win will give you *DOUBLE Unity Coins!* "
        "_That’s twice the rewards, twice the fun, and twice the reason to play NOW!_ 🎮🔥\n\n"
        "💰 *Your strategy matters. Your timing matters. Your winnings? Unlimited.*\n\n"
        "⏳ *But hurry!* Time is running out! Once the clock hits zero, the bonus disappears. ⏳\n\n"
        "🕒 *[TIME REMAINING: *60 minutes*]*\n\n"
        "🎭 *Outwit.* 🃏 *Outsmart.* 🏆 *Win.*"
    )
    text_end_ru = (
        "🔴 *ДВОЙНАЯ ВЫГОДА ЗАВЕРШЕНА!*\n\n"
        "⚡ *Событие официально завершено!* Надеемся, ты успел получить максимум выгоды!\n\n"
        "🎭 *Пропустил?* _Не переживай! Следующий Double Trouble может начаться В ЛЮБОЙ МОМЕНТ... Будь начеку!_\n\n"
        "🔔 Подпишись на канал *Liar’s Fortune*, чтобы выиграть ПО-КРУПНОМУ!!\n\n"
        "🎭 *Обыграй.* 🃏 *Перехитри.* 🏆 *Побеждай.*"
    )
    text_end_uz = (
        "🔴 *2X YAKUNLANDI!*\n\n"
        "⚡ *2X rasmiy yakunlandi!* Umid qilamizki, MAKSIMAL yutuq olgansiz!\n\n"
        "🤖 *O‘tkazib yubordingizmi? Xavotir olmang!* Keyingi Double Trouble istalgan vaqtda boshlanishi mumkin... _E’tiborli bo‘ling!_\n\n"
        "🔔 *KATTA* yutuqlarni qo‘ldan boy bermaslik uchun *Liar’s Fortune* kanaliga obuna bo‘ling!\n\n"
        "🎭 *Hushyor bo‘l.* 🃏 *Ustun kel.* 🏆 *G‘alaba qil!*"
    )
    text_end_en = (
        "🔴 *DOUBLE TROUBLE ENDED!*\n\n"
        "⚡ *The event has officially ended!* Hope you made the most out of it!\n\n"
        "🤖 *Missed it?* _Don’t worry! The next Double Trouble could strike at ANY time... Stay alert!_\n\n"
        "🔔 *Subscribe to* Liar’s Fortune channel, to win *BIG!*\n\n"
        "🎭 *Outwit.* 🃏 *Outsmart.* 🏆 *Win.*"
    )
    keyboard_ru = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Подписаться!", url="https://t.me/liars_fortune_channel"
                )
            ]
        ]
    )
    keyboard_uz = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Kanalga o'tish!", url="https://t.me/liars_fortune_channel"
                )
            ]
        ]
    )
    keyboard_en = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Subscribe!", url="https://t.me/liars_fortune_channel"
                )
            ]
        ]
    )
    set_game_coin(10)
    users = get_all_user_ids()
    for user_id in users:
        try:
            user_lang = get_user_language(user_id)
            if user_lang == "ru":
                msg_text = text_ru
            elif user_lang == "uz":
                msg_text = text_uz
            else:
                msg_text = text_en
            await bot.send_message(user_id, msg_text, parse_mode="Markdown")
        except Exception:
            continue
    await asyncio.sleep(60 * 60)
    set_game_coin(5)
    for user_id in users:
        try:
            user_lang = get_user_language(user_id)
            if user_lang == "ru":
                msg_text = text_end_ru
                kb = keyboard_ru
            elif user_lang == "uz":
                msg_text = text_end_uz
                kb = keyboard_uz
            else:
                msg_text = text_end_en
                kb = keyboard_en
            await bot.send_message(
                user_id, msg_text, reply_markup=kb, parse_mode="Markdown"
            )
        except Exception:
            continue


@dp.message(F.text == "🛒 shop")
@admin_required()
async def admin_shop_settings(message: Message, state: FSMContext):
    await message.answer(
        "Choose one of these options 👇", reply_markup=shop_settings_buttons
    )


@dp.message(F.text == "add tool to user ➕")
@admin_required()
async def add_tool_to_a_user(message: Message, state: FSMContext):
    await message.answer(
        f"Please enter the ID or Username of a user ✍️", reply_markup=back_to_admin_panel
    )
    await state.set_state(ADDtool.idorusername)


@dp.message(ADDtool.idorusername)
async def add_tool_states(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    username = message.text
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM users_database WHERE user_id = ? OR nfgame = ?",
        (username, username),
    )
    user = cursor.fetchone()
    if not (user):
        await message.answer(
            "❌ Please send a valid user ID or username",
            reply_markup=back_to_admin_panel,
        )
    else:
        username = user[0]
        await state.update_data(user_id=username)
        await message.answer(
            "choose a tool from below that you want to give: ",
            reply_markup=choose_tools_to_add,
        )
        await state.set_state(ADDtool.toolchoose)


@dp.message(ADDtool.toolchoose)
async def add_tool_states2(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    tools = ["skip 🪓", "block ⛔️", "change 🔄"]
    if not (message.text in tools):
        await message.answer(
            "please, enter a correct tool", reply_markup=choose_tools_to_add
        )
    else:
        data = await state.get_data()
        user_id = data["user_id"]
        tool_key = message.text
        skipper = 1 if tool_key == "skip 🪓" else 0
        blocker = 1 if tool_key == "block ⛔️" else 0
        changer = 1 if tool_key == "change 🔄" else 0
        conn = sqlite3.connect("users_database.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO supper_tool (user_id, skipper, blocker, changer)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                skipper = skipper + ?,
                blocker = blocker + ?,
                changer = changer + ?
            """,
            (user_id, skipper, blocker, changer, skipper, blocker, changer),
        )
        conn.commit()
        conn.close()
        await message.answer(
            f"You have successfully gave a {tool_key} to a user {get_user_nfgame(user_id)} ✅",
            reply_markup=admin_panel_button,
        )
        await state.clear()


@dp.message(F.text == "change prices ♻️")
@admin_required()
async def change_prices_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Changer 🔄", callback_data="chane_price:changer"
                ),
                InlineKeyboardButton(
                    text="blocker ⛔️", callback_data="chane_price:blocker"
                ),
                InlineKeyboardButton(
                    text="skiper 🪓", callback_data="chane_price:skipper"
                ),
            ],
        ]
    )
    await message.answer(
        "Select which tool's price you want to change:", reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data.startswith("chane_price"))
async def ask_for_new_price(callback_query: types.CallbackQuery, state: FSMContext):
    tool = callback_query.data.split(":")[1]
    tyt = get_tool_prices()
    if tool == "changer":
        tyt = tyt["card_changer"]
    elif tool == "skipper":
        tyt = tyt["skip_pass"]
    else:
        tyt = tyt["block_press"]
    await state.update_data(tool=tool)
    await state.set_state(PriceUpdate.waiting_for_price)
    await callback_query.message.answer(
        f"Enter the new price for {tool}\nOld price was: {tyt}",
        reply_markup=back_to_admin_panel,
    )
    await callback_query.answer()


@dp.message(PriceUpdate.waiting_for_price)
async def update_price(message: types.Message, state: FSMContext):
    if message.text == "back to admin panel 🔙":
        await message.answer(
            "You are in admin panel 👇", reply_markup=admin_panel_button
        )
        await state.clear()
        return
    if not message.text.isdigit():
        await message.answer("Please enter a valid number.")
    else:
        data = await state.get_data()
        tool = data["tool"]
        new_price = int(message.text)
        conn = sqlite3.connect("users_database.db")
        cursor = conn.cursor()
        if tool == "skipper":
            cursor.execute(
                f"UPDATE shop_prices SET skipper = ? WHERE rowid = 1", (new_price,)
            )
        elif tool == "blocker":
            cursor.execute(
                f"UPDATE shop_prices SET blocker = ? WHERE rowid = 1", (new_price,)
            )
        else:
            cursor.execute(
                f"UPDATE shop_prices SET changer = ? WHERE rowid = 1", (new_price,)
            )
        conn.commit()
        conn.close()
        await state.clear()
        await message.answer(
            f"Price updated successfully! ✅", reply_markup=admin_panel_button
        )


@dp.message(F.text == "/send_right_now")
async def update_price(message: types.Message, state: FSMContext):
    message_text = (
        "🧐 *WE NEED YOUR OPINION\\!* 🧐\n\n"
        "🎭 Hey, Liar’s Fortune players\\! We noticed some of you have been quiet lately\\. 🤔\n\n"
        "💡 What’s stopping you from playing\\? Rewards\\? Intense battles\\? Or is something missing\\?\n\n"
        "📋 Take just *1 minute* to fill out our quick survey\\!\n\n"
        "🔗 [Click here to fill out](https://forms.gle/e4a1Tz8TRLoRATwY7)\n\n"
        "🎁 Complete it and receive *50 Unity Coins 💰 \\+ a Super Card\\!* 🍬\n\n"
        "👂 We’re listening – help us make the game even better\\!"
    )
    message_text_uz = (
        "🧐 *SIZNING FIKRINGIZ MUHIM\\!* 🧐\n\n"
        "🎭 Hey, Liar’s Fortune o‘yinchilari\\! Ayrimlar jim bo‘lib qolgandek\\! 🤔\n\n"
        "💡 O‘yin o‘ynashga nima to‘sqinlik qilmoqda\\? Mukofotlar\\? Qizg‘in janglar\\? Yoki nimadir yetishmayaptimi\\?\n\n"
        "📋 Bor\\-yo‘g‘i *1 daqiqa* vaqt ajratib, tezkor so‘rovnomani to‘ldiring\\!\n\n"
        "🔗 [So‘rovnomani to‘ldirish uchun shu yerni bosing](https://forms.gle/e4a1Tz8TRLoRATwY7)\n\n"
        "🎁 To‘ldiring va *50 Unity Coins 💰 \\+ Super Karta* 🍬 qo‘lga kiriting\\!\n\n"
        "👂 Sizni tinglaymiz – o‘yinni yanada yaxshilashga yordam bering\\!"
    )
    message_text_ru = (
        "🧐 *ВАЖНО ВАШЕ МНЕНИЕ\\!* 🧐\n\n"
        "🎭 Привет, игроки Liar’s Fortune\\! Мы заметили, что некоторые из вас стали тише\\. 🤔\n\n"
        "💡 Что мешает вам играть\\? Награды\\? Напряжённые сражения\\? Или чего\\-то не хватает\\?\n\n"
        "📋 Всего *1 минута* – заполните наш короткий опрос\\!\n\n"
        "🔗 [Нажмите здесь, чтобы заполнить опрос](https://forms.gle/e4a1Tz8TRLoRATwY7)\n\n"
        "🎁 Заполните и получите *50 Unity Coins 💰 \\+ Супер карту\\!* 🍬\n\n"
        "👂 Мы вас слушаем – помогите сделать игру ещё лучше\\!"
    )
    users = get_all_user_ids()
    cnt = 0
    for user_id in users:
        try:
            user_lang = get_user_language(user_id)
            if user_lang == "ru":
                msg_text = message_text_ru
            elif user_lang == "uz":
                msg_text = message_text_uz
            else:
                msg_text = message_text

            await bot.send_message(
                user_id,
                msg_text,
                reply_markup=get_main_menu(user_id),
                parse_mode="MarkdownV2",
            )

        except Exception:
            cnt += 1
            continue
    await message.answer(
        f"Message was forwarded anonymously to {len(users) - cnt} users from {len(users)} successfully ✅"
    )
