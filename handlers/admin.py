import csv
import io
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Request
from config.settings import settings

router = Router()

# Фильтр для проверки админа
def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id == settings.ADMIN_CHAT_ID

# Декоратор для админских команд
class AdminFilter:
    async def __call__(self, message: Message) -> bool:
        return is_admin(message.from_user.id)

admin_filter = AdminFilter()


# ============ АДМИН КОМАНДЫ ============

@router.message(Command("admin"), AdminFilter())
async def cmd_admin(message: Message, t):
    """Главное меню админ-панели"""
    
    text = (
        f"🔐 <b>Админ-панель TourBot</b>\n\n"
        f"Доступные команды:\n\n"
        f"📊 /stats - Статистика заявок\n"
        f"📋 /requests - Последние 10 заявок\n"
        f"📥 /export - Экспорт всех заявок в CSV\n"
        f"📅 /today - Заявки за сегодня\n"
        f"🔍 /search [ID] - Поиск заявки по ID\n"
        f"🗑 /delete [ID] - Удалить заявку\n"
        f"📢 /broadcast - Рассылка сообщения всем пользователям\n"
        f"💡 /help_admin - Справка по командам"
    )
    
    await message.answer(text, parse_mode='HTML')


@router.message(Command("stats"), AdminFilter())
async def cmd_stats(message: Message, session: AsyncSession, t):
    """Статистика заявок"""
    
    # Общее количество заявок
    total_result = await session.execute(select(func.count(Request.id)))
    total_requests = total_result.scalar()
    
    # Заявки за сегодня
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await session.execute(
        select(func.count(Request.id)).where(Request.created_at >= today_start)
    )
    today_requests = today_result.scalar()
    
    # Заявки за неделю
    week_start = datetime.now() - timedelta(days=7)
    week_result = await session.execute(
        select(func.count(Request.id)).where(Request.created_at >= week_start)
    )
    week_requests = week_result.scalar()
    
    # Заявки за месяц
    month_start = datetime.now() - timedelta(days=30)
    month_result = await session.execute(
        select(func.count(Request.id)).where(Request.created_at >= month_start)
    )
    month_requests = month_result.scalar()
    
    # Общий бюджет всех заявок
    budget_result = await session.execute(select(func.sum(Request.budget)))
    total_budget = budget_result.scalar() or 0
    
    # Средний бюджет
    avg_budget = total_budget / total_requests if total_requests > 0 else 0
    
    # Уникальные пользователи
    unique_users_result = await session.execute(select(func.count(func.distinct(Request.user_id))))
    unique_users = unique_users_result.scalar()
    
    # ТОП-5 направлений
    top_destinations_result = await session.execute(
        select(Request.destination, func.count(Request.id).label('count'))
        .group_by(Request.destination)
        .order_by(func.count(Request.id).desc())
        .limit(5)
    )
    top_destinations = top_destinations_result.all()
    
    text = (
        f"📊 <b>Статистика TourBot</b>\n\n"
        f"📈 <b>Общая информация:</b>\n"
        f"├ Всего заявок: {total_requests}\n"
        f"├ Уникальных пользователей: {unique_users}\n"
        f"├ Общий бюджет: {total_budget:,}₽\n"
        f"└ Средний бюджет: {avg_budget:,.0f}₽\n\n"
        f"📅 <b>По периодам:</b>\n"
        f"├ За сегодня: {today_requests}\n"
        f"├ За неделю: {week_requests}\n"
        f"└ За месяц: {month_requests}\n\n"
        f"🌍 <b>ТОП-5 направлений:</b>\n"
    )
    
    for idx, (destination, count) in enumerate(top_destinations, 1):
        text += f"{idx}. {destination}: {count} заявок\n"
    
    await message.answer(text, parse_mode='HTML')


@router.message(Command("requests"), AdminFilter())
async def cmd_requests(message: Message, session: AsyncSession, t):
    """Последние 10 заявок"""
    
    result = await session.execute(
        select(Request).order_by(Request.created_at.desc()).limit(10)
    )
    requests = result.scalars().all()
    
    if not requests:
        await message.answer("📭 Заявок пока нет", parse_mode='HTML')
        return
    
    text = "📋 <b>Последние 10 заявок:</b>\n\n"
    
    for req in requests:
        text += (
            f"🆔 <b>#{req.id}</b> | 👤 @{req.username or 'N/A'}\n"
            f"🌍 {req.destination} | 📅 {req.departure_date}\n"
            f"🌙 {req.nights} ночей | 👥 {req.adults}+{req.children}\n"
            f"💰 {req.budget:,}₽ | ⏰ {req.created_at.strftime('%d.%m %H:%M')}\n"
            f"{'─' * 40}\n"
        )
    
    await message.answer(text, parse_mode='HTML')


@router.message(Command("export"), AdminFilter())
async def cmd_export(message: Message, session: AsyncSession, t):
    """Экспорт всех заявок в CSV"""
    
    result = await session.execute(select(Request).order_by(Request.created_at.desc()))
    requests = result.scalars().all()
    
    if not requests:
        await message.answer("📭 Нет заявок для экспорта", parse_mode='HTML')
        return
    
    # Создание CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Заголовки
    writer.writerow([
        'ID', 'User ID', 'Username', 'Направление', 'Дата вылета',
        'Ночей', 'Взрослых', 'Детей', 'Бюджет', 'Комментарий', 'Создана'
    ])
    
    # Данные
    for req in requests:
        writer.writerow([
            req.id,
            req.user_id,
            req.username or 'N/A',
            req.destination,
            req.departure_date,
            req.nights,
            req.adults,
            req.children,
            req.budget,
            req.comment or 'Нет',
            req.created_at.strftime('%d.%m.%Y %H:%M')
        ])
    
    # Конвертация в байты для отправки
    csv_bytes = output.getvalue().encode('utf-8-sig')  # BOM для корректного открытия в Excel
    output.close()
    
    # Отправка файла
    file = BufferedInputFile(csv_bytes, filename=f"requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    await message.answer_document(
        document=file,
        caption=f"📥 Экспорт завершен\n\nВсего заявок: {len(requests)}"
    )


@router.message(Command("today"), AdminFilter())
async def cmd_today(message: Message, session: AsyncSession, t):
    """Заявки за сегодня"""
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await session.execute(
        select(Request)
        .where(Request.created_at >= today_start)
        .order_by(Request.created_at.desc())
    )
    requests = result.scalars().all()
    
    if not requests:
        await message.answer("📭 Сегодня заявок пока нет", parse_mode='HTML')
        return
    
    text = f"📅 <b>Заявки за сегодня ({len(requests)} шт.):</b>\n\n"
    
    for req in requests:
        text += (
            f"🆔 <b>#{req.id}</b> | 👤 @{req.username or 'N/A'}\n"
            f"🌍 {req.destination} | 💰 {req.budget:,}₽\n"
            f"⏰ {req.created_at.strftime('%H:%M')}\n"
            f"{'─' * 40}\n"
        )
    
    await message.answer(text, parse_mode='HTML')


@router.message(Command("search"), AdminFilter())
async def cmd_search(message: Message, session: AsyncSession, t):
    """Поиск заявки по ID"""
    
    # Извлечение ID из команды
    try:
        request_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /search [ID]\n\nПример: /search 123", parse_mode='HTML')
        return
    
    result = await session.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    
    if not req:
        await message.answer(f"❌ Заявка #{request_id} не найдена", parse_mode='HTML')
        return
    
    text = (
        f"🔍 <b>Заявка #{req.id}</b>\n\n"
        f"👤 <b>Пользователь:</b>\n"
        f"├ ID: {req.user_id}\n"
        f"└ Username: @{req.username or 'N/A'}\n\n"
        f"📋 <b>Детали:</b>\n"
        f"├ 🌍 Направление: {req.destination}\n"
        f"├ 📅 Дата вылета: {req.departure_date}\n"
        f"├ 🌙 Ночей: {req.nights}\n"
        f"├ 👥 Взрослых: {req.adults}\n"
        f"├ 👶 Детей: {req.children}\n"
        f"├ 💰 Бюджет: {req.budget:,}₽\n"
        f"├ 💬 Комментарий: {req.comment or 'Нет'}\n"
        f"└ ⏰ Создана: {req.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await message.answer(text, parse_mode='HTML')


@router.message(Command("delete"), AdminFilter())
async def cmd_delete(message: Message, session: AsyncSession, t):
    """Удаление заявки по ID"""
    
    # Извлечение ID из команды
    try:
        request_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /delete [ID]\n\nПример: /delete 123", parse_mode='HTML')
        return
    
    result = await session.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    
    if not req:
        await message.answer(f"❌ Заявка #{request_id} не найдена", parse_mode='HTML')
        return
    
    await session.delete(req)
    await session.commit()
    
    await message.answer(
        f"🗑 <b>Заявка #{request_id} удалена</b>\n\n"
        f"Направление: {req.destination}\n"
        f"Пользователь: @{req.username or 'N/A'}",
        parse_mode='HTML'
    )


@router.message(Command("broadcast"), AdminFilter())
async def cmd_broadcast(message: Message, session: AsyncSession, state: FSMContext, t):
    """Начало рассылки"""
    
    await message.answer(
        "📢 <b>Режим рассылки</b>\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n\n"
        "Для отмены отправьте /cancel",
        parse_mode='HTML'
    )
    
    await state.set_state("broadcast_waiting")


@router.message(F.state == "broadcast_waiting", AdminFilter())
async def process_broadcast(message: Message, session: AsyncSession, state: FSMContext, t):
    """Обработка и отправка рассылки"""
    
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Рассылка отменена", parse_mode='HTML')
        return
    
    # Получение уникальных user_id
    result = await session.execute(select(func.distinct(Request.user_id)))
    user_ids = [row[0] for row in result.all()]
    
    if not user_ids:
        await message.answer("📭 Нет пользователей для рассылки", parse_mode='HTML')
        await state.clear()
        return
    
    # Отправка рассылки
    success_count = 0
    failed_count = 0
    
    status_msg = await message.answer(
        f"📤 Рассылка началась...\n\n"
        f"Всего пользователей: {len(user_ids)}",
        parse_mode='HTML'
    )
    
    for user_id in user_ids:
        try:
            await message.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success_count += 1
        except Exception as e:
            failed_count += 1
            # Логирование ошибок (пользователь заблокировал бота и т.д.)
            print(f"Ошибка отправки пользователю {user_id}: {e}")
    
    # Обновление статуса
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📊 Статистика:\n"
        f"├ Успешно: {success_count}\n"
        f"├ Ошибок: {failed_count}\n"
        f"└ Всего: {len(user_ids)}",
        parse_mode='HTML'
    )
    
    await state.clear()


@router.message(Command("help_admin"), AdminFilter())
async def cmd_help_admin(message: Message, t):
    """Справка по админ-командам"""
    
    text = (
        f"💡 <b>Справка по командам админ-панели</b>\n\n"
        f"<b>📊 /stats</b>\n"
        f"Показывает подробную статистику:\n"
        f"• Общее количество заявок\n"
        f"• Заявки по периодам (день/неделя/месяц)\n"
        f"• Общий и средний бюджет\n"
        f"• ТОП направлений\n\n"
        f"<b>📋 /requests</b>\n"
        f"Выводит последние 10 заявок с кратким описанием\n\n"
        f"<b>📥 /export</b>\n"
        f"Экспортирует ВСЕ заявки в CSV-файл (можно открыть в Excel)\n\n"
        f"<b>📅 /today</b>\n"
        f"Показывает все заявки за текущий день\n\n"
        f"<b>🔍 /search [ID]</b>\n"
        f"Поиск и просмотр детальной информации о конкретной заявке\n"
        f"Пример: <code>/search 42</code>\n\n"
        f"<b>🗑 /delete [ID]</b>\n"
        f"Удаляет заявку по ID (необратимо!)\n"
        f"Пример: <code>/delete 42</code>\n\n"
        f"<b>📢 /broadcast</b>\n"
        f"Запускает режим рассылки сообщения всем пользователям бота\n"
        f"После команды отправьте любое сообщение (текст/фото/видео)\n\n"
        f"<b>Дополнительно:</b>\n"
        f"• Все команды работают только для админа (ID: {settings.ADMIN_CHAT_ID})\n"
        f"• CSV файлы сохраняются с BOM (корректно открываются в Excel с кириллицей)\n"
        f"• При рассылке игнорируются пользователи, заблокировавшие бота"
    )
    
    await message.answer(text, parse_mode='HTML')


# Обработка неизвестных команд от не-админов
@router.message(Command("admin"))
@router.message(Command("stats"))
@router.message(Command("requests"))
@router.message(Command("export"))
async def cmd_not_admin(message: Message, t):
    """Ответ для не-админов"""
    await message.answer("🔒 У вас нет доступа к админ-панели", parse_mode='HTML')
