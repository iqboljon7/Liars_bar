import sqlite3
from config import dp, F, bot
from aiogram import types
from aiogram.fsm.context import FSMContext
from keyboards.keyboard import change_name, main_menu, cancel_button
from states.state import NewGameState, MessagetoAdmin, messagetouser
from db import (
    get_user_nfgame,
    is_name_valid,
    is_game_started,
    get_game_id_by_user,
    get_total_users,
)


@dp.message(F.text == "/send")
async def send_message_to(message: types.Message, state:FSMContext):
    if message.from_user.id == 6807731973:
        await message.answer(f"Write the ID of user and then the message in SEPARATE line. ")
        await state.set_state(messagetouser.messag)
    else:
        await message.answer(f"You entered unfamiliar information.")
@dp.message(messagetouser.messag)
async def state_send_msg(message: types.Message, state: FSMContext):
    user_id_va = message.text.split("\n")[0]
    await bot.send_message(chat_id=int(user_id_va), text=message.text.split("\n")[1])
    await message.answer("Your message has been sent successfully ✅")
    await state.clear()

@dp.message(F.text == "settings ⚙️")
async def settings(message: types.Message):
    await message.answer(f"Choose one of these options: ⬇️", reply_markup=change_name)


@dp.message(F.text == "❓ help")
async def help_butn(message: types.Message, state: FSMContext):
    await message.answer(
        "If you have any questions or suggestions, feel free to write here. An admin will respond as soon as possible. ⬇️",
        reply_markup=cancel_button,
    )

    await state.set_state(MessagetoAdmin.msgt)


@dp.message(MessagetoAdmin.msgt)
async def help_button_state(message: types.Message, state: FSMContext):
    if message.text != "back to main menu 🔙":
        await bot.send_message(
            chat_id=6807731973,
            text=f"User — {message.from_user.first_name} (<a href='tg://openmessage?user_id={message.from_user.id}'>{message.from_user.id}</a>) sent you message: \n{message.text}",
            parse_mode="HTML",
        )
        await message.answer(
            "Your message has been sent successfully ✅",
            reply_markup=main_menu,
        )

        await state.clear()
    else:
        await state.clear()
        await message.answer(
            f"You are in main menu 👇",
            reply_markup=main_menu,
        )


@dp.message(F.text == "change name 🖌")
async def changeee(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Your current name is: {get_user_nfgame(message.from_user.id)}\nIf you'd like to change it, please type your new name:",
        reply_markup=cancel_button,
    )
    await state.set_state(NewGameState.waiting_for_nfgame)


@dp.message(NewGameState.waiting_for_nfgame)
async def set_new_nfgame(message: types.Message, state: FSMContext):
    new_nfgame = message.text
    if is_game_started(get_game_id_by_user(message.from_user.id)):
        await message.answer(
            f"You are currently participating in a game and cannot change your name until the game ends.",
            reply_markup=main_menu,
        )
        await state.clear()
        return
    if new_nfgame == "back to main menu 🔙":
        await state.clear()
        await message.answer(f"You are in main menu ⬇️", reply_markup=main_menu)
        return
    h = is_name_valid(new_nfgame)
    if h == 1:
        await message.answer(
            f"The length of the name must not exceed 30 characters."
        )
    else:
        user_id = message.from_user.id
        with sqlite3.connect("users_database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users_database SET nfgame = ? WHERE user_id = ?",
                (new_nfgame, user_id),
            )
            conn.commit()
        await message.answer(
            f"Your name has been successfully changed to: {new_nfgame} ✅",
            reply_markup=main_menu,
        )

        await state.clear()


@dp.message(F.text == "cancel 🚫")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"You have canceled changing the name.", reply_markup=main_menu
    )


@dp.message(F.text == "statistics 📊")
async def statistics_a(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Here are the bot's statistics 📈:\n\nTotal users in the bot 👥: {get_total_users()}\nBot has been active since 01.03.2024 📅",
        reply_markup=main_menu,
    )

@dp.message(F.text == "how to play 📝")
async def how_to_play(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📔 Simple Game Rules with Card Suits 📔\n\n"
        "🔴 Players:\n"
        "You need 2 to 4 players.\n"
        "Each player starts with 5 cards.\n\n"
        "🔴 How to Play:\n"
        "At the start of the game, one card is placed on the table. This is the Table Card.\n\n"
        "The suit of this card (like Hearts ❤️, Diamonds ♦️, Clubs ♣️, or Spades ♠️) is what matters.\n"
        "On your turn, you can play 1, 2, or 3 cards from your hand.\n\n"
        "Your all cards must match the same suit as the Table Card.\n"
        "If you don’t have matching cards, you can use a Universal Card 🎴, which matches any suit.\n"
        "After you play, the next player has two choices:\n\n"
        "1️⃣ Continue: They accept your move and take their turn.\n"
        "2️⃣ Press LIAR: They check your cards to see if they match the suit.\n\n"
        "🔴 What Happens if Someone Presses LIAR?\n"
        "If your cards don’t match the suit, you’re a Liar and must “shoot yourself.”\n"
        "If your cards do match, the person who pressed LIAR shoots themselves instead!\n\n"
        "🔴 Special Cards:\n"
        "🎴 Universal Card: Matches any suit—it’s always correct.\n"
        "🃏 Joker Card:\n"
        "If you play this card alone and someone opens it, everyone except you “shoots themselves”!\n\n"
        "🔵 Other Rules:\n"
        "If you run out of cards, you skip your turn until you get new ones.\n"
        "Every time LIAR is pressed, all cards are reshuffled and dealt again.\n"
        "The gun has 6 bullets, but only 1 is real—no one knows which!\n\n"
        "🔴 Winning the Game:\n"
        "The game ends when only one player is left standing."
    )
