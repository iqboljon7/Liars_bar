import sqlite3
import asyncio
import random
import re
from config import bot, dp
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from keyboards.keyboard import get_main_menu


def connect_db():
    return sqlite3.connect("users_database.db")


def register_user(user_id, username, first_name, last_name, preferred_name):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO users_database (user_id, username, first_name, last_name, nfgame, registration_date)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (user_id, username, first_name, last_name, preferred_name),
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error registering user: {e}")


def is_user_registered(user_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users_database WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
        return user
    except sqlite3.Error as e:
        print(f"Error checking if user is registered: {e}")
        return None


def add_admin(user_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def get_game_inviter_id(game_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT inviter_id FROM invitations WHERE game_id = ?", (game_id,)
            )
            inviter_id = cursor.fetchone()
        return inviter_id[0] if inviter_id else None
    except sqlite3.Error as e:
        print(f"Error retrieving inviter ID: {e}")
        return None


def insert_invitation(inviter_id, invitee_id, game_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO invitations (inviter_id, invitee_id, game_id)
                VALUES (?, ?, ?)
                """,
                (inviter_id, invitee_id, game_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting invitation: {e}")


def get_player_count(game_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM invitations WHERE game_id = ?", (game_id,)
            )
            player_count = cursor.fetchone()[0]
        return player_count
    except sqlite3.Error as e:
        print(f"Error getting player count: {e}")
        return 0


def is_user_in_game(game_id, user_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT invitee_id FROM invitations WHERE game_id = ? AND invitee_id = ?",
                (game_id, user_id),
            )
            result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        print(f"Error checking if user is in game: {e}")
        return False


def get_user_nfgame(user_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nfgame FROM users_database WHERE user_id = ?", (user_id,)
            )
            result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Error retrieving user 'nfgame': {e}")
        return None


def has_incomplete_games(user_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT game_id FROM invitations WHERE inviter_id = ? AND invitee_id IS NULL",
                (user_id,),
            )
            creator_game = cursor.fetchone()

            cursor.execute(
                "SELECT game_id FROM invitations WHERE invitee_id = ?", (user_id,)
            )
            participant_game = cursor.fetchone()

        return bool(creator_game or participant_game)
    except sqlite3.Error as e:
        print(f"Error checking incomplete games: {e}")
        return False


def delete_user_from_all_games(user_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM invitations WHERE inviter_id = ? AND invitee_id IS NULL",
                (user_id,),
            )
            cursor.execute("DELETE FROM invitations WHERE invitee_id = ?", (user_id,))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting user from games: {e}")


def get_all_players_in_game(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT inviter_id, invitee_id
            FROM invitations
            WHERE game_id = ?
            """,
            (game_id,),
        )
        result = cursor.fetchall()
        players = {row[0] for row in result} | {row[1] for row in result}
        players = list(players)
        for i in players:
            if not i:
                players.remove(i)
        return players


def delete_game(game_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM invitations WHERE game_id = ?", (game_id,))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting game: {e}")


def get_games_by_user(user_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT game_id, inviter_id FROM invitations WHERE invitee_id = ? OR inviter_id = ?",
                (
                    user_id,
                    user_id,
                ),
            )
            games = cursor.fetchall()
        return [{"game_id": game[0], "creator_id": game[1]} for game in games]
    except sqlite3.Error as e:
        print(f"Error getting games for user {user_id}: {e}")
        return []


def get_game_id_by_user(user_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT game_id FROM invitations WHERE inviter_id = ?", (user_id,)
        )
        game_id = cursor.fetchone()
        if game_id:
            return game_id[0]
        cursor.execute(
            "SELECT game_id FROM invitations WHERE invitee_id = ?", (user_id,)
        )
        game_id = cursor.fetchone()
        if game_id:
            return game_id[0]
    return None


def get_id_by_nfgame(nfgame):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users_database WHERE nfgame = ?", (nfgame,))
        result = cursor.fetchone()
        if result:
            return result[0]
    return None


def get_needed_players(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT needed_players
            FROM invitations
            WHERE game_id = ? AND inviter_id IS NOT NULL
            LIMIT 1
            """,
            (game_id,),
        )
        result = cursor.fetchone()
        return result[0] if result else 0


def get_game_creator_id(game_id):
    """Fetch the creator's user ID for a specific game."""
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT inviter_id 
            FROM invitations 
            WHERE game_id = ?
            LIMIT 1
        """,
            (game_id,),
        )
        result = cursor.fetchone()
        return result[0] if result else None


async def send_message_to_all_players(game_id, message: str):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT invitee_id FROM invitations WHERE game_id = ? AND invitee_id IS NOT NULL",
            (game_id,),
        )
        players = cursor.fetchall()
        cr_id = get_game_creator_id(game_id)
        if not cr_id in players:
            players.append((cr_id,))
        for player in players:
            player_id = player[0]
            if not player_id:
                continue
            try:
                msg = await bot.send_message(player_id, message)
                await save_message(player_id, game_id, msg.message_id)
            except Exception as e:
                print(f"Failed to send message to player {player_id}: {e}")


def set_game_started(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE invitations SET is_started = 1 WHERE game_id = ?", (game_id,)
        )
        conn.commit()


def is_game_started(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_started FROM invitations WHERE game_id = ?", (game_id,)
        )
        result = cursor.fetchone()
        return result[0] == 1 if result else False


def mark_game_as_started(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE invitations SET is_started = 1 WHERE game_id = ?", (game_id,)
        )
        conn.commit()


def is_name_valid(name):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users_database WHERE nfgame = ?", (name,))
    if cursor.fetchone()[0] > 0:
        return 2
    if len(name) > 20 or len(name) < 1:
        return 0
    if re.match(r"^[a-zA-Z0-9_]+$", name[1:]) and name[0] == "@":
        return 1
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        return 0
    return 1


def get_all_players_nfgame(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.nfgame 
            FROM users_database u
            INNER JOIN invitations i ON u.user_id = i.invitee_id
            WHERE i.game_id = ?
        """,
            (game_id,),
        )
        s = []
        for row in cursor.fetchall():
            s.append(row[0])
        cr_name = get_user_nfgame(get_game_creator_id(game_id))
        if not cr_name in s:
            s.append(cr_name)
        return s


def ensure_column_exists():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(invitations);")
        columns = cursor.fetchall()
        if not any(column[1] == "current_turn_user_id" for column in columns):
            cursor.execute(
                "ALTER TABLE invitations ADD COLUMN current_turn_user_id INTEGER;"
            )
            conn.commit()


def set_current_turn(game_id, user_id):
    ensure_column_exists()
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE invitations SET current_turn_user_id = ? WHERE game_id = ?",
            (user_id, game_id),
        )
        conn.commit()


def insert_number_of_cards(game_id, number_of_cards):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(invitations)")
        columns = [col[1] for col in cursor.fetchall()]
        if "number_of_cards" not in columns:
            cursor.execute("ALTER TABLE invitations ADD COLUMN number_of_cards INTEGER")
        cursor.execute(
            """
            UPDATE invitations
            SET number_of_cards = ?
            WHERE game_id = ?
            """,
            (number_of_cards, game_id),
        )

        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO invitations (game_id, number_of_cards)
                VALUES (?, ?)
                """,
                (game_id, number_of_cards),
            )

        conn.commit()


def set_current_table(game_id, current_table):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(game_state)")
        columns = [row[1] for row in cursor.fetchall()]
        if "current_table" not in columns:
            cursor.execute(
                """
                ALTER TABLE game_state
                ADD COLUMN current_table TEXT
                """
            )
            conn.commit()

        cursor.execute(
            """
            INSERT OR IGNORE INTO game_state (game_id)
            VALUES (?)
            """,
            (game_id,),
        )

        cursor.execute(
            """
            UPDATE game_state
            SET current_table = ?
            WHERE game_id = ?
            """,
            (current_table, game_id),
        )
        conn.commit()

    return current_table


def get_current_table(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(game_state)")
        columns = [row[1] for row in cursor.fetchall()]
        if "current_table" not in columns:
            raise ValueError(
                "The 'current_table' column does not exist in the game_state table."
            )
        cursor.execute(
            """
            SELECT current_table
            FROM game_state
            WHERE game_id = ?
            """,
            (game_id,),
        )
        result = cursor.fetchone()
        if result is None:
            print(f"No entry found for game_id: {game_id}.")
        elif result[0] is None:
            print(f"'current_table' is not set for game_id: {game_id}.")
        return result[0] if result else None


async def periodically_edit_message(
    chat_id,
    message_id,
    s_message_id,
    lent,
    cur_table,
    interval,
):
    try:
        seconds = ["2️⃣", "1️⃣"]
        for i in range(2):
            new_text = seconds[i]
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=new_text
            )
            await asyncio.sleep(interval)

        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        await bot.delete_message(chat_id=chat_id, message_id=s_message_id)
        if lent == 2:
            number = 19
        elif lent == 3:
            number = 23
        else:
            number = 27
        game_id = get_game_id_by_user(chat_id)
        insert_number_of_cards(game_id, number)
        massiv = get_all_players_nfgame(game_id)
        mark_game_as_started(game_id)
        s = ""
        rang = ["🔴", "🟠", "🟡", "🟢", "⚪️"]
        for row in range(len(massiv)):
            s += rang[row] + " " + massiv[row] + "\n"
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"Game has started. 🚀🚀🚀\n"
                f"There are {number} cards in the game.\n"
                f"{number//4} hearts — ♥️\n"
                f"{number//4} diamonds — ♦️\n"
                f"{number//4} spades — ♠️\n"
                f"{number//4} clubs — ♣️\n"
                f"2 universals — 🎴\n"
                f"1 Joker — 🃏\n\n"
                f"Players in the game: \n{s}\n"
                f"Current table for cards: {cur_table}\n\n"
            ),
        )
    except Exception as e:
        await bot.send_message(
            chat_id,
            f"Something went wrong. Plase try again.",
            reply_markup=get_main_menu(chat_id),
        )
        print(f"An error occurred: {e}")


def get_number_of_cards(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT number_of_cards 
            FROM invitations 
            WHERE game_id = ?
            """,
            (game_id,),
        )
        result = cursor.fetchone()
        return result[0] if result else 0


def generate_random_cards(deck):
    random_cards = random.sample(deck, 5)
    for card in random_cards:
        deck.remove(card)
    return random_cards


def delete_all_players_cards(game_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM game_state
            WHERE game_id = ?
        """,
            (game_id,),
        )
        conn.commit()
    print(f"Cleared all cards for game {game_id}")


def create_cards(game_id):
    nm = get_number_of_cards(game_id)
    cards = ["❤️", "♦️", "♠️", "♣️"]
    deck = cards * (nm // 4)
    deck.append("🃏")
    deck.append("🎴")
    deck.append("🎴")
    return deck


def save_player_cards(game_id):
    players = get_all_players_in_game(game_id)
    if not players:
        print("No players found for this game.")
        return
    players = [
        player for player in players if player and not is_player_dead(game_id, player)
    ]

    deck = create_cards(game_id)
    if len(deck) < len(players) * 5:
        print("Not enough cards remaining in the deck for all players.")
        return
    player_cards = {player: generate_random_cards(deck) for player in players}
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(game_state)")
        columns = [row[1] for row in cursor.fetchall()]
        if "player_id" not in columns:
            cursor.execute("ALTER TABLE game_state ADD COLUMN player_id TEXT")
        if "cards" not in columns:
            cursor.execute("ALTER TABLE game_state ADD COLUMN cards TEXT")

        for player, cards in player_cards.items():
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM game_state
                WHERE game_id = ? AND player_id = ?
                """,
                (game_id, player),
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                cursor.execute(
                    """
                    UPDATE game_state
                    SET cards = ?
                    WHERE game_id = ? AND player_id = ?
                    """,
                    (",".join(cards), game_id, player),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO game_state (game_id, player_id, cards)
                    VALUES (?, ?, ?)
                    """,
                    (game_id, player, ",".join(cards)),
                )
        conn.commit()

    print(f"Cards saved for game {game_id}: {player_cards}")


def set_real_bullet_for_player(game_id, player_id):
    cards = ["blank"] * 5 + ["real"]
    random.shuffle(cards)
    real_bullet = cards.index("real")

    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(game_state)")
            columns = [row[1] for row in cursor.fetchall()]

            if "player_id" not in columns:
                cursor.execute(
                    """
                    ALTER TABLE game_state
                    ADD COLUMN player_id TEXT
                    """
                )
                conn.commit()
                print("Added 'player_id' column to game_state table.")

            if "real_bullet" not in columns:
                cursor.execute(
                    """
                    ALTER TABLE game_state
                    ADD COLUMN real_bullet INTEGER
                    """
                )
                conn.commit()
                print("Added 'real_bullet' column to game_state table.")

            if "blanks_count" not in columns:
                cursor.execute(
                    """
                    ALTER TABLE game_state
                    ADD COLUMN blanks_count INTEGER DEFAULT 0
                    """
                )
                conn.commit()
                print("Added 'blanks_count' column to game_state table.")

            # Check if a record exists for this player and game
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM game_state
                WHERE game_id = ? AND player_id = ?
                """,
                (game_id, player_id),
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                # Update existing record
                cursor.execute(
                    """
                    UPDATE game_state
                    SET real_bullet = ?, blanks_count = 0
                    WHERE game_id = ? AND player_id = ?
                    """,
                    (real_bullet, game_id, player_id),
                )
            else:
                # Insert new record
                cursor.execute(
                    """
                    INSERT INTO game_state (game_id, player_id, real_bullet, blanks_count)
                    VALUES (?, ?, ?, 0)
                    """,
                    (game_id, player_id, real_bullet),
                )
            conn.commit()
            print(
                f"Set 'real_bullet' for player {player_id} in game {game_id} to {real_bullet}."
            )
            return real_bullet

        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            return None


def ensure_life_status_column():
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(game_state)")
        columns = [row[1] for row in cursor.fetchall()]
        if "life_status" not in columns:
            cursor.execute(
                """
                ALTER TABLE game_state
                ADD COLUMN life_status TEXT DEFAULT 'alive'
                """
            )
            conn.commit()
            print("Added 'life_status' column to 'game_state'.")


def is_player_dead(game_id, player_id):
    ensure_life_status_column()
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT life_status
            FROM game_state
            WHERE game_id = ? AND player_id = ?
            """,
            (game_id, player_id),
        )
        result = cursor.fetchone()
        if result and result[0] == "dead":
            return True
    return False


async def shoot_self(game_id, player_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT real_bullet, blanks_count
            FROM game_state
            WHERE game_id = ? AND player_id = ?
            """,
            (game_id, player_id),
        )
        result = cursor.fetchone()
        if result is None:
            return None

        real_bullet_position, blanks_count = result
        if int(blanks_count) == int(real_bullet_position):
            cursor.execute(
                """
                UPDATE game_state
                SET life_status = 'dead'
                WHERE game_id = ? AND player_id = ?
                """,
                (game_id, player_id),
            )
            conn.commit()
            return True
        else:
            blanks_count += 1
            cursor.execute(
                """
                UPDATE game_state
                SET blanks_count = ?
                WHERE game_id = ? AND player_id = ?
                """,
                (blanks_count, game_id, player_id),
            )
            conn.commit()
            elimination_chance = blanks_count
            return elimination_chance


def get_player_status(game_id, player_id):
    with sqlite3.connect("users_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT life_status
            FROM game_state
            WHERE game_id = ? AND player_id = ?
            """,
            (game_id, player_id),
        )
        result = cursor.fetchone()
        if result:
            return result[0]
    return "alive"


def get_total_users():
    try:
        with sqlite3.connect("users_database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users_database")
            total_users = cursor.fetchone()[0]
            return total_users
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return 0


async def save_message(user_id, game_id, message_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users_game_states (user_id, game_id_user, messages_ingame)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                game_id_user = excluded.game_id_user,
                messages_ingame = COALESCE(
                    (SELECT messages_ingame FROM users_game_states WHERE user_id = excluded.user_id) || ',' || excluded.messages_ingame,
                    excluded.messages_ingame
                )
            """,
            (user_id, game_id, message_id),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")


async def delete_all_game_messages(game_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, messages_ingame FROM users_game_states WHERE game_id_user = ?",
        (game_id,),
    )
    rows = cursor.fetchall()

    for row in rows:
        user_id = row[0]
        message_ids = row[1].split(",")
        for message_id in message_ids:
            try:
                await bot.delete_message(chat_id=user_id, message_id=int(message_id))
            except Exception as e:
                print(f"Error deleting message {message_id} for user {user_id}: {e}")
    conn.commit()


async def delete_user_messages(game_id, user_id):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT messages_ingame FROM users_game_states WHERE game_id_user = ? AND user_id = ?",
        (game_id, user_id),
    )
    row = cursor.fetchone()
    if row:
        message_ids = row[0].split(",")
        for message_id in message_ids:
            try:
                await bot.delete_message(chat_id=user_id, message_id=int(message_id))
            except Exception as e:
                print(f"Error deleting message {message_id} for user {user_id}: {e}")
        conn.commit()
    else:
        print(f"No messages found for user {user_id} in game {game_id}")


def get_all_user_ids():
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT user_id FROM users_database")
        user_ids = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")
        user_ids = []
    finally:
        conn.close()
    return user_ids


def get_user_statistics(user_id: int) -> str:
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT username, first_name, last_name, registration_date, nfgame 
            FROM users_database WHERE user_id = ?
            """,
            (user_id,),
        )
        user_data = cursor.fetchone()
        if not user_data:
            return "❌ No user found with the given ID."
        username, first_name, last_name, registration_date, nfgame = user_data
        stats_message = (
            f"📊 **User Statistics** 📊\n"
            f"👤 **Username**: @{username if username else 'N/A'}\n"
            f"📛 **First Name**: {first_name if first_name else 'N/A'}\n"
            f"📜 **Last Name**: {last_name if last_name else 'N/A'}\n"
            f"🗓️ **Registration Date**: {registration_date if registration_date else 'N/A'}\n"
            f"🎮 **Username in bot**: {nfgame if nfgame else 'N/A'}\n"
        )
    except sqlite3.Error as e:
        stats_message = f"❌ Database error occurred: {e}"
    finally:
        conn.close()

    return stats_message


from datetime import datetime

def create_game_record_if_not_exists(game_id: str, user_id: int):
    conn = sqlite3.connect("users_database.db")
    cursor = conn.cursor()
    try:
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO game_archive (game_id, user_id, game_start_time)
            VALUES (?, ?, ?)
            """,
            (game_id, user_id, start_time),
        )
        conn.commit()
        print(f"Game record created for {user_id}, game_id: {game_id}")
    except sqlite3.Error as e:
        print(f"❌ Database error occurred while creating game record: {e}")
    finally:
        conn.close()


def update_game_details(game_id: str, user_id: int, winner: str):
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect("users_database.db")
        cursor = conn.cursor()
        
        if not winner:
            winner = "Game had not been finished"
        
        cursor.execute(
            """
            UPDATE game_archive 
            SET game_end_time = ?, game_winner = ?
            WHERE game_id = ? AND user_id = ?
            """,
            (end_time, winner, game_id, user_id),
        )
        
        conn.commit()
        
        # Check if any row was affected
        if cursor.rowcount == 0:
            return f"❌ Failed to update game details for ID '{game_id}'."
        
        print(f"Game details updated for {user_id}, game_id: {game_id}")
        return "Game details updated successfully."

    except sqlite3.Error as e:
        return f"❌ Database error occurred: {e}"
    finally:
        conn.close()

