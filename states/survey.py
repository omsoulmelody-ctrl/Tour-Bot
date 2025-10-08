from aiogram.fsm.state import State, StatesGroup

class SurveyStates(StatesGroup):
    """Состояния опроса пользователя"""
    destination = State()
    departure_date = State()
    nights = State()
    adults = State()
    children = State()
    budget = State()
    comment = State()
