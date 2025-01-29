import sqlite3
import uuid
import asyncio
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import *
from keyboards.keyboard import *
from middlewares.registered import admin_required
from keyboards.inline import get_join_tournament_button, user_tournaments_keyboard
from db import *
from states.state import AddTournaments, EditRegistrationDates, EditStartAndEndTimes, EditMaxPlayers
from datetime import datetime, timezone, timedelta
from game.game_state import notify_groups


@dp.message(F.text == "🏆 tournaments")
@admin_required()
async def tournaments_admin_panel(message: types.Message):
    await message.answer(
        f"You are in tournaments section. \nPlease choose on of these options 👇",
        reply_markup=tournaments_admin_panel_button,
    )


@dp.message(F.text == "🚫 delete this tournament")
@admin_required()
async def deleteeee_tourinit(message: types.Message, state: FSMContext):
    ongoing_tournament = get_ongoing_tournaments()
    if ongoing_tournament:
        tournament = ongoing_tournament[0]
        nop = get_current_players(tournament["name"])
        tournament_id = tournament["name"]
        response = (
            f"🌟 Tournament ID: {tournament['id']}\n\n"
            f"🗓 Started: {tournament['start_time']}\n"
            f"🏁 Ends: {tournament['end_time']}\n\n"
            f"👥 Registered Players: {nop}/{tournament['maximum_players']}\n"
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


@dp.message(F.text == "back to tournaments panel 🔙")
@admin_required()
async def back_to_tournaments_section(message: types.Message, state: FSMContext):
    await message.answer(
        f"You are in tournaments section. \nPlease choose on of these options.",
        reply_markup=tournaments_admin_panel_button,
    )
    await state.clear()


@dp.message(F.text == "⚡️ Ongoing")
@admin_required()
async def ongoing_tournaments_sekshn(message: types.Message):
    ongoing_tournaments = get_ongoing_tournaments()
    if not ongoing_tournaments:
        await message.answer(
            f"There are no ongoing tournaments 🤷‍♂️",
            reply_markup=tournaments_admin_panel_button,
        )
        return

    response = "⚡️ *Ongoing Tournaments:*\n\n"
    for tournament in ongoing_tournaments:
        response += (
            f"🌟 *{tournament['id']}*\n\n"
            f"🗓 Started: {tournament['start_time']}\n"
            f"🏁 Ends: {tournament['end_time']}\n\n"
            f"👥 Registered Players: {tournament['current_players']}/{tournament['maximum_players']}\n\n"
            f"🏆 Prize: \n{tournament['prize']}\n\n"
        )

    await message.answer(
        response,
        reply_markup=ongoing_tournaments_button,
        parse_mode="Markdown",
    )


@dp.message(F.text == "⏳ Upcoming")
@admin_required()
async def upcoming_tournaments_sekshn(message: types.Message):
    turnir = get_upcoming_tournaments()

    if not turnir:
        await message.answer(
            f"There are no upcoming tournaments 🤷‍♂️",
            reply_markup=tournaments_admin_panel_button,
        )
        return

    response = "🌟 *Upcoming Tournaments:*\n\n"
    for tournament in turnir:
        if "_" in tournament["name"]:
            nop = get_current_players(tournament["name"].split("_")[1])
        else:
            nop = get_current_players(tournament["name"])
        response += (
            f"🌟 Tournament ID: *{tournament['id']}*\n"
            f"🗓 Starts: {tournament['start_time']}\n"
            f"🏁 Ends: {tournament['end_time']}\n\n"
            f"🗓 Registration starts: {tournament['register_start']}\n"
            f"🏁 Registration ends: {tournament['register_end']}\n\n"
            f"👥 Registered Players: {nop}/{tournament['maximum_players']}\n\n"
            f"🏆 Prizes: \n\n{tournament['prize']}\n\n"
        )
    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=upcoming_tournaments_button,
    )


@dp.message(F.text == "🗂 Archive")
@admin_required()
async def archive_tournaments_sekcsh(message: types.Message):
    tournaments = get_tournament_archive()
    if not tournaments:
        await message.answer(
            "No tournaments in the archive.",
            reply_markup=tournaments_admin_panel_button,
        )
        return

    response = "📑 *Tournament Archive:*\n\n"
    for tournament in tournaments:
        response += f"🏆 ID: {tournament['id']}\n🌟 Started: {tournament["start_time"]}\n📅 Ended: {tournament["end_time"]}\n🥇 Winner: {tournament['winner']}\n\n"
    await message.answer(response, parse_mode="Markdown")


@dp.message(F.text == "➕ create a new Tournament")
@admin_required()
async def create_a_new_truine(message: types.Message, state: FSMContext):
    turnir = get_upcoming_tournaments()
    if turnir:
        await message.answer(
            f"⚠️ There is upcoming tournament and you can not create a new one unless you delete it.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    await message.answer(
        f"You are creating a new tournament ❗️\nPlease enter the maximum number of players: ",
        reply_markup=back_to_tournaments_button,
    )
    await state.set_state(AddTournaments.number_of_players)


@dp.message(AddTournaments.number_of_players)
async def set_number_of_players(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    if not message.text.isdigit():
        await message.answer(
            "Please enter a valid number.", reply_markup=back_to_tournaments_button
        )
        return
    await state.update_data(number_of_players=int(message.text))
    await message.answer(
        "Please enter the registration start date (YYYY-MM-DD HH:MM):",
        reply_markup=back_to_tournaments_button,
    )
    await state.set_state(AddTournaments.registr_start_date)


@dp.message(AddTournaments.registr_start_date)
async def set_registration_start_date(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        await state.update_data(registration_start=start_date)
        await message.answer(
            "Please enter the registration end date (YYYY-MM-DD HH:MM):",
            reply_markup=back_to_tournaments_button,
        )
        await state.set_state(AddTournaments.registr_end_date)
    except ValueError:
        await message.answer(
            "Invalid date format. Please use YYYY-MM-DD HH:MM.",
            reply_markup=back_to_tournaments_button,
        )


@dp.message(AddTournaments.registr_end_date)
async def set_registration_end_date(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        data = await state.get_data()
        if end_date <= data["registration_start"]:
            await message.answer(
                "End date must be after the start date. Try again.",
                reply_markup=back_to_tournaments_button,
            )
            return
        await state.update_data(registration_end=end_date)
        await message.answer(
            "Please enter the tournament start date (YYYY-MM-DD HH:MM):",
            reply_markup=back_to_tournaments_button,
        )
        await state.set_state(AddTournaments.turnir_start_date)
    except ValueError:
        await message.answer(
            "Invalid date format. Please use YYYY-MM-DD HH:MM.",
            reply_markup=back_to_tournaments_button,
        )


@dp.message(AddTournaments.turnir_start_date)
async def set_tournament_start_date(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        data = await state.get_data()
        if start_date <= data["registration_end"]:
            await message.answer(
                "Tournament start date must be after registration end date. Try again.",
                reply_markup=back_to_tournaments_button,
            )
            return
        await state.update_data(tournament_start=start_date)
        await message.answer(
            "Please enter the tournament end date (YYYY-MM-DD HH:MM):",
            reply_markup=back_to_tournaments_button,
        )
        await state.set_state(AddTournaments.turnir_end_date)
    except ValueError:
        await message.answer(
            "Invalid date format. Please use YYYY-MM-DD HH:MM.",
            reply_markup=back_to_tournaments_button,
        )


@dp.message(AddTournaments.turnir_end_date)
async def set_tournament_end_date(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        data = await state.get_data()
        if end_date <= data["tournament_start"]:
            await message.answer(
                "Tournament end date must be after the start date. Try again.",
                reply_markup=back_to_tournaments_button,
            )
            return
        await state.update_data(tournament_end=end_date)
        await message.answer(
            "Please enter the tournament prize:",
            reply_markup=back_to_tournaments_button,
        )
        await state.set_state(AddTournaments.turnir_prize)
    except ValueError:
        await message.answer(
            "Invalid date format. Please use YYYY-MM-DD HH:MM.",
            reply_markup=back_to_tournaments_button,
        )


@dp.message(AddTournaments.turnir_prize)
async def set_tournament_prize(message: types.Message, state: FSMContext):
    await state.update_data(prize=message.text)
    data = await state.get_data()
    unique_id = f"{uuid.uuid4().hex}"
    await state.update_data(tournament_link=unique_id)
    save_tournament_to_db(data, unique_id)

    await message.answer(
        f"✅ Tournament created successfully:\n\n"
        f"🎮 Players: {data['number_of_players']}\n\n"
        f"🗓 Registration: {data['registration_start']} to {data['registration_end']}\n"
        f"🕹 Start: {data['tournament_start']} | End: {data['tournament_end']}\n\n"
        f"🏆 Prize: \n{data['prize']}\n\n"
        f"🔗 tournament id: {unique_id}",
        reply_markup=admin_panel_button,
    )
    await state.clear()


def save_tournament_to_db(data, tournamnet_link):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO tournaments_table (
                maximum_players, 
                tournament_register_start_time, 
                tournament_register_end_time, 
                tournament_start_time, 
                tournament_end_time, 
                tournament_prize, 
                tournament_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["number_of_players"],
                data["registration_start"],
                data["registration_end"],
                data["tournament_start"],
                data["tournament_end"],
                data["prize"],
                tournamnet_link,
            ),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()


@dp.message(F.text == "🤩 tournaments")
@admin_required()
async def show_tournaments_menu(message: types.Message):
    await message.answer("Choose an option:", reply_markup=user_tournaments_keyboard)


@dp.message(F.text == "✏️ edit registration")
@admin_required()
async def edit_registration_dates_single(message: types.Message, state: FSMContext):
    tournaments = get_upcoming_tournaments()
    if not tournaments:
        await message.answer(
            "No upcoming tournaments available to edit.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    tournament = tournaments[0]
    tournament_id = tournament["name"]
    await state.update_data(tournament_id=tournament_id)
    await message.answer(
        f"You are editing the REGISTRATION date of current tournament\n\n📅 Current registration start time: {tournament['register_start']}.\n\n"
        "Please enter the new REGISTRATION *start date* in the format `YYYY-MM-DD HH:MM`:",
        parse_mode="Markdown",
        reply_markup=back_to_tournaments_button,
    )
    await state.set_state(EditRegistrationDates.new_start_date)


@dp.message(EditRegistrationDates.new_start_date)
async def set_new_start_date_single(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    new_start_date = message.text.strip()
    try:
        datetime.strptime(new_start_date, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "Invalid date format. Please use `YYYY-MM-DD HH:MM`. Try again.",
            reply_markup=back_to_tournaments_button,
        )
        return
    await state.update_data(new_start_date=new_start_date)
    tournaments = get_upcoming_tournaments()
    tournament = tournaments[0]
    await message.answer(
        f"📅 Current registration end time: {tournament['register_end']}.\n\nNow, enter the new REGISTRATION *end date* in the format `YYYY-MM-DD HH:MM`:",
        parse_mode="Markdown",
        reply_markup=back_to_tournaments_button,
    )
    await state.set_state(EditRegistrationDates.new_end_date)


@dp.message(EditRegistrationDates.new_end_date)
async def set_new_end_date_single(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    new_end_date = message.text.strip()
    try:
        datetime.strptime(new_end_date, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "Invalid date format. Please use `YYYY-MM-DD HH:MM`. Try again.",
            reply_markup=back_to_tournaments_button,
        )
        return
    data = await state.get_data()
    tournament_id = data["tournament_id"]
    new_start_date = data["new_start_date"]

    update_registration_dates(tournament_id, new_start_date, new_end_date)

    await message.answer(
        f"✅ Registration dates have been updated!\n\n"
        f"🗓 Start: {new_start_date}\n"
        f"🗓 End: {new_end_date}",
        reply_markup=tournaments_admin_panel_button,
    )
    await state.clear()


def update_registration_dates(tournament_id: str, start_date: str, end_date: str):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE tournaments_table
            SET tournament_register_start_time = ?, tournament_register_end_time = ?
            WHERE tournament_id = ?
            """,
            (start_date, end_date, tournament_id),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()


@dp.message(F.text == "📝 edit starting")
@admin_required()
async def edit_start_and_end_times(message: types.Message, state: FSMContext):
    tournaments = get_upcoming_tournaments()
    if not tournaments:
        await message.answer(
            "No upcoming tournaments available to edit.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    await state.clear()
    tournament = tournaments[0]
    await state.update_data(tournament_id=tournament["name"])
    await message.answer(
        f"Editing the START time  for tournament.\n\n"
        f"📅 Current Start time: {tournament['start_time']}\n\n"
        "Please enter the new *start date* in the format `YYYY-MM-DD HH:MM`:",
        parse_mode="Markdown",
        reply_markup=back_to_tournaments_button,
    )
    await state.set_state(EditStartAndEndTimes.new_start_date)


@dp.message(EditStartAndEndTimes.new_start_date)
async def set_new_start_date(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    new_start_date = message.text.strip()
    try:
        datetime.strptime(new_start_date, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "Invalid date format. Please use `YYYY-MM-DD HH:MM`. Try again.",
            reply_markup=back_to_tournaments_button,
        )
        return
    await state.update_data(new_start_date=new_start_date)
    tournaments = get_upcoming_tournaments()
    tournament = tournaments[0]
    await message.answer(
        f"📅 Current End time: {tournament['end_time']}.\n\nNow, enter the new *end date* in the format `YYYY-MM-DD HH:MM`:",
        parse_mode="Markdown",
        reply_markup=back_to_tournaments_button,
    )
    await state.set_state(EditStartAndEndTimes.new_end_date)


@dp.message(EditStartAndEndTimes.new_end_date)
async def set_new_end_date(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🔙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    new_end_date = message.text.strip()
    try:
        datetime.strptime(new_end_date, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "Invalid date format. Please use `YYYY-MM-DD HH:MM`. Try again.",
            reply_markup=back_to_tournaments_button,
        )
        return

    data = await state.get_data()
    tournament_id = data["tournament_id"]
    new_start_date = data["new_start_date"]
    update_start_and_end_dates(tournament_id, new_start_date, new_end_date)
    await message.answer(
        f"✅ Start and end times for the tournament have been updated!\n\n"
        f"🗓 Start: {new_start_date}\n"
        f"🗓 End: {new_end_date}",
        reply_markup=tournaments_admin_panel_button,
    )
    await state.clear()


def update_start_and_end_dates(tournament_id: str, start_date: str, end_date: str):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE tournaments_table
            SET tournament_start_time = ?, tournament_end_time = ?
            WHERE tournament_id = ?
            """,
            (start_date, end_date, tournament_id),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()


@dp.message(F.text == "✅ start the tournament")
@admin_required()
async def start_tournir_keyborar(message: types.Message, state: FSMContext):
    turnir = get_ongoing_tournaments()[0]
    tournament_id = turnir["name"]
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tournament_id, tournament_start_time FROM tournaments_table WHERE tournament_id = ?",
        (tournament_id,),
    )
    tournament = cursor.fetchone()
    if not tournament:
        await message.answer(
            f"Tournament with ID {tournament_id} not found.",
            reply_markup=tournaments_admin_panel_button,
        )
        return
    tournament_name, start_time = tournament
    uzbekistan_time = datetime.now(timezone.utc) + timedelta(hours=5)
    try:
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    if uzbekistan_time < start_time:
        await message.answer(
            "Tournament cannot start before the scheduled time.",
            reply_markup=tournaments_admin_panel_button,
        )
        return

    cursor.execute(
        "SELECT user_id FROM tournament_users WHERE tournament_id = ?", (tournament_id,)
    )
    participants = [row[0] for row in cursor.fetchall()]
    conn.close()
    if len(participants) < 2:
        await message.answer(
            "Not enough participants to start the tournament.",
            reply_markup=tournaments_admin_panel_button,
        )
        return
    await notify_participants(participants, len(participants))
    round_number = 1
    groups = create_groups(participants)
    for nk in range(len(groups)):
        for jk in groups[nk]:
            save_tournament_round_info(tournament_id,round_number,jk, nk+1)
    await notify_groups(groups, round_number)



async def notify_participants(participants, num_participants):
    for user_id in participants:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🏆 The tournament is starting now❗️\n"
                f"👥 Number of participants: {num_participants}\n"
                "📋 Get ready for the first round!",
            )
        except Exception as e:
            print(f"Failed to notify user {user_id}: {e}")


def set_all_users_alive(tournament_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tournament_users SET user_status = 'alive' WHERE tournament_id = ?",
        (tournament_id,),
    )
    conn.commit()
    conn.close()


def get_user_status(user_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_status FROM tournament_users WHERE user_id = ?", (user_id,)
    )
    status = cursor.fetchone()
    conn.close()
    if status:
        return status[0]
    return None


def get_game_id_from_mes(user_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
                SELECT game_id FROM user_game_messages WHERE user_id = ?
                """,
            (user_id,),
        )
        rows = cursor.fetchall()
        if rows:
            return rows[-1][0]
        else:
            return None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

@dp.message(F.text == "✍️ edit maximum players")
@admin_required()
async def edit_maximum_players(message: types.Message, state: FSMContext):
    tournaments = get_upcoming_tournaments()
    if not tournaments:
        await message.answer(
            "No upcoming tournaments available to edit.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    await state.clear()
    tournament = tournaments[0]
    await state.update_data(tournament_id=tournament["name"])
    await message.answer(
        f"Editing the MAXIMUM players for tournament\n"
        f"👥 Current Maximum Players: {tournament['maximum_players']}\n\n"
        "Please enter the new *maximum players* count:",
        parse_mode="Markdown",
        reply_markup=back_to_tournaments_button,
    )
    await state.set_state(EditMaxPlayers.new_max_players)


@dp.message(EditMaxPlayers.new_max_players)
async def set_new_max_players(message: types.Message, state: FSMContext):
    if message.text == "back to tournaments panel 🖙":
        await message.answer(
            f"You are in tournaments section.",
            reply_markup=tournaments_admin_panel_button,
        )
        await state.clear()
        return
    try:
        new_max_players = int(message.text.strip())
        if new_max_players <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid input. Please enter a positive number.",
            reply_markup=back_to_tournaments_button,
        )
        return
    
    data = await state.get_data()
    tournament_id = data["tournament_id"]
    nop = get_current_players(tournament_id)
    if new_max_players < nop:
        await message.answer("The new maximum number of players MUST not be less than registrated players ❌", reply_markup=tournaments_admin_panel_button)
        await state.clear()
        return
    update_maximum_players(tournament_id, new_max_players)
    await message.answer(
        f"✅ Maximum players updated successfully!\n\n"
        f"👥 New Maximum Players: {new_max_players}",
        reply_markup=tournaments_admin_panel_button,
    )
    await state.clear()


def update_maximum_players(tournament_id: str, max_players: int):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE tournaments_table
            SET maximum_players = ?
            WHERE tournament_id = ?
            """,
            (max_players, tournament_id),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()
