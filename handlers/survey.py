from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Request
from states.survey import SurveyStates
from keyboards.inline import back_kb, skip_kb, progress_bar, main_menu_kb
from config.settings import settings
from services.google_sheets import save_to_sheets
from services.notification import notify_admin

router = Router()

@router.message(SurveyStates.destination)
async def process_destination(message: Message, state: FSMContext, t):
    """Обработка направления"""
    await state.update_data(destination=message.text.strip())
    
    await message.answer(
        text=f"{progress_bar(2)}\n\n{t('destination_saved', destination=message.text)}",
        reply_markup=back_kb(t)
    )
    await state.set_state(SurveyStates.departure_date)

@router.message(SurveyStates.departure_date)
async def process_date(message: Message, state: FSMContext, t):
    """Обработка даты вылета"""
    try:
        date_obj = datetime.strptime(message.text.strip(), '%d.%m.%Y')
        
        if date_obj < datetime.now():
            await message.answer(t('date_past'), reply_markup=back_kb(t))
            return
        
        await state.update_data(departure_date=message.text.strip())
        
        await message.answer(
            text=f"{progress_bar(3)}\n\n{t('date_saved', date=message.text)}",
            reply_markup=back_kb(t)
        )
        await state.set_state(SurveyStates.nights)
        
    except ValueError:
        await message.answer(t('date_invalid'), reply_markup=back_kb(t))

@router.message(SurveyStates.nights)
async def process_nights(message: Message, state: FSMContext, t):
    """Обработка количества ночей"""
    try:
        nights = int(message.text.strip())
        
        if not (3 <= nights <= 21):
            await message.answer(t('nights_invalid'), reply_markup=back_kb(t))
            return
        
        await state.update_data(nights=nights)
        
        await message.answer(
            text=f"{progress_bar(4)}\n\n{t('nights_saved', nights=nights)}",
            reply_markup=back_kb(t)
        )
        await state.set_state(SurveyStates.adults)
        
    except ValueError:
        await message.answer(t('nights_invalid'), reply_markup=back_kb(t))

@router.message(SurveyStates.adults)
async def process_adults(message: Message, state: FSMContext, t):
    """Обработка взрослых"""
    try:
        adults = int(message.text.strip())
        
        if not (1 <= adults <= settings.MAX_TRAVELERS):
            await message.answer(t('adults_invalid'), reply_markup=back_kb(t))
            return
        
        await state.update_data(adults=adults)
        
        await message.answer(
            text=f"{progress_bar(5)}\n\n{t('adults_saved', adults=adults)}",
            reply_markup=back_kb(t)
        )
        await state.set_state(SurveyStates.children)
        
    except ValueError:
        await message.answer(t('adults_invalid'), reply_markup=back_kb(t))

@router.message(SurveyStates.children)
async def process_children(message: Message, state: FSMContext, t):
    """Обработка детей"""
    try:
        children = int(message.text.strip())
        
        if not (0 <= children <= 10):
            await message.answer(t('children_invalid'), reply_markup=back_kb(t))
            return
        
        await state.update_data(children=children)
        
        await message.answer(
            text=f"{progress_bar(6)}\n\n{t('children_saved', children=children)}",
            reply_markup=back_kb(t)
        )
        await state.set_state(SurveyStates.budget)
        
    except ValueError:
        await message.answer(t('children_invalid'), reply_markup=back_kb(t))

@router.message(SurveyStates.budget)
async def process_budget(message: Message, state: FSMContext, t, session: AsyncSession):
    """Обработка бюджета"""
    try:
        budget = int(message.text.strip().replace(' ', '').replace('₽', ''))
        
        if budget < settings.MIN_BUDGET:
            await message.answer(
                t('budget_invalid', min_budget=settings.MIN_BUDGET),
                reply_markup=back_kb(t)
            )
            return
        
        await state.update_data(budget=budget)
        
        await message.answer(
            text=f"{progress_bar(7)}\n\n{t('budget_saved', budget=budget)}",
            reply_markup=skip_kb(t)
        )
        await state.set_state(SurveyStates.comment)
        
    except ValueError:
        await message.answer(
            t('budget_invalid', min_budget=settings.MIN_BUDGET),
            reply_markup=back_kb(t)
        )

@router.message(SurveyStates.comment)
@router.callback_query(F.data == 'skip', SurveyStates.comment)
async def process_comment(event: Message | CallbackQuery, state: FSMContext, t, session: AsyncSession):
    """Обработка комментария и завершение опроса"""
    
    # Получение комментария
    if isinstance(event, Message):
        comment = event.text.strip()
        user = event.from_user
        message = event
    else:
        comment = "Нет комментариев"
        user = event.from_user
        message = event.message
        await event.answer()
    
    await state.update_data(comment=comment)
    
    # Получение всех данных
    data = await state.get_data()
    
    # Сохранение в БД
    new_request = Request(
        user_id=user.id,
        username=user.username,
        destination=data['destination'],
        departure_date=data['departure_date'],
        nights=data['nights'],
        adults=data['adults'],
        children=data['children'],
        budget=data['budget'],
        comment=comment
    )
    
    session.add(new_request)
    await session.commit()
    await session.refresh(new_request)
    
    # Сохранение в Google Sheets (асинхронно в фоне)
    try:
        await save_to_sheets(new_request)
    except Exception as e:
        print(f"Ошибка сохранения в Google Sheets: {e}")
    
    # Уведомление админа
    try:
        await notify_admin(new_request, message.bot)
    except Exception as e:
        print(f"Ошибка отправки уведомления админу: {e}")
    
    # Отправка подтверждения пользователю
    await message.answer(
        text=t('survey_complete',
               request_id=new_request.id,
               destination=data['destination'],
               date=data['departure_date'],
               nights=data['nights'],
               adults=data['adults'],
               children=data['children'],
               budget=data['budget'],
               comment=comment),
        reply_markup=main_menu_kb(t)
    )
    
    await state.clear()

@router.callback_query(F.data == 'back')
async def handle_back(callback: CallbackQuery, state: FSMContext, t):
    """Обработка кнопки 'Назад'"""
    current_state = await state.get_state()
    
    # Маппинг состояний для возврата
    state_map = {
        SurveyStates.destination: None,
        SurveyStates.departure_date: SurveyStates.destination,
        SurveyStates.nights: SurveyStates.departure_date,
        SurveyStates.adults: SurveyStates.nights,
        SurveyStates.children: SurveyStates.adults,
        SurveyStates.budget: SurveyStates.children,
        SurveyStates.comment: SurveyStates.budget
    }
    
    # Получение предыдущего состояния
    prev_state = None
    for s, prev in state_map.items():
        if current_state == s.state:
            prev_state = prev
            break
    
    if prev_state is None:
        # Возврат в главное меню
        await callback.message.edit_text(
            text=t('welcome'),
            reply_markup=main_menu_kb(t)
        )
        await state.clear()
    else:
        await state.set_state(prev_state)
        
        # Показ сообщения для предыдущего шага
        data = await state.get_data()
        
        if prev_state == SurveyStates.destination:
            text = f"{progress_bar(1)}\n\n{t('start_survey')}"
        elif prev_state == SurveyStates.departure_date:
            text = f"{progress_bar(2)}\n\n{t('destination_saved', destination=data.get('destination', ''))}"
        elif prev_state == SurveyStates.nights:
            text = f"{progress_bar(3)}\n\n{t('date_saved', date=data.get('departure_date', ''))}"
        elif prev_state == SurveyStates.adults:
            text = f"{progress_bar(4)}\n\n{t('nights_saved', nights=data.get('nights', 0))}"
        elif prev_state == SurveyStates.children:
            text = f"{progress_bar(5)}\n\n{t('adults_saved', adults=data.get('adults', 0))}"
        elif prev_state == SurveyStates.budget:
            text = f"{progress_bar(6)}\n\n{t('children_saved', children=data.get('children', 0))}"
        
        await callback.message.edit_text(text=text, reply_markup=back_kb(t))
    
    await callback.answer()
