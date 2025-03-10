from aiogram.fsm.state import State, StatesGroup


class registration(StatesGroup):
    pref_name = State()


class registration_game(StatesGroup):
    pref1_name = State()


class new_game(StatesGroup):
    number_of_players = State()
    
class NewGameState(StatesGroup):
    waiting_for_nfgame = State()

class MessagetoAdmin(StatesGroup):
    msgt = State()
    
class messagetouser(StatesGroup):
    messag = State()
    
class Adminid(StatesGroup):
    admin_id = State()
    
class msgtoall(StatesGroup):
    sendallanonym = State()
    english = State()
    russian = State()
    uzbek = State()
class msgtoindividual(StatesGroup):
    userid = State()
    sendtoone = State()
    
class UserInformations(StatesGroup):
    userid_state = State()
    
class awaiting_game_number(StatesGroup):
    waiting = State()
    
class awaiting_admin_game_number(StatesGroup):
    selected_user = State()
    
class awaiting_user_id(StatesGroup):
    await_id = State()
    
class AddTournaments(StatesGroup):
    number_of_players = State()
    registr_start_date = State()
    registr_end_date = State()
    turnir_start_date = State()
    turnir_end_date = State()
    turnir_prize = State()
    
class EditRegistrationDates(StatesGroup):
    select_tournament = State()
    new_start_date = State()
    new_end_date = State()
    
class EditStartAndEndTimes(StatesGroup):
    new_start_date = State()
    new_end_date = State()
    
class waiting_for_coin_amount(StatesGroup):
    unity_coin_amount = State()
    
class waiting_for_user_id_or_username(StatesGroup):
    waiting_amount = State()
    waiting_for_add_coin_amount = State()
    waiting_for_subtract_coin_amount = State()
    user_id = State()
    
class EditMaxPlayers(StatesGroup):
    new_max_players = State()
    
class changeWithdraw(StatesGroup):
    changee = State()
    option = State()
    
class waiting_for_username_withdraw(StatesGroup):
    username_withdraw = State()
    
class waitforreferralamount(StatesGroup):
    amount = State()
    
class waitforcoinamount(StatesGroup):
    amount = State()
    
class AddChannelState(StatesGroup):
    waiting_for_channel_id = State()
    
class ADDtool(StatesGroup):
    idorusername = State()
    toolchoose = State()
    
class PriceUpdate(StatesGroup):
    waiting_for_price = State()
    
