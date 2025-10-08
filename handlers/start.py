from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.inline import main_menu_kb
from states.survey import SurveyStates

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, t):
    """Обработчик команды /start"""
    await state.clear()
    await message.answer(
        text=t('welcome'),
        reply_markup=main_menu_kb(t)
    )

@router.callback_query(F.data == 'start_survey')
async def start_survey(callback: CallbackQuery, state: FSMContext, t):
    """Начало опроса"""
    from keyboards.inline import progress_bar, back_kb
    
    await callback.message.edit_text(
        text=f"{progress_bar(1)}\n\n{t('start_survey')}",
        reply_markup=back_kb(t)
    )
    await state.set_state(SurveyStates.destination)
    await callback.answer()
