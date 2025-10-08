from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb(t) -> InlineKeyboardMarkup:
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('find_tour'), callback_data='start_survey')]
    ])

def back_kb(t) -> InlineKeyboardMarkup:
    """Кнопка назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('back'), callback_data='back')]
    ])

def skip_kb(t) -> InlineKeyboardMarkup:
    """Кнопка пропустить"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('skip'), callback_data='skip')],
        [InlineKeyboardButton(text=t('back'), callback_data='back')]
    ])

def progress_bar(current: int, total: int = 7) -> str:
    """Цветной прогресс-бар с эмодзи"""
    emoji_list = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫']
    filled = emoji_list[current - 1] if current <= len(emoji_list) else '🟢'
    bar = ''.join([filled if i < current else '⚪' for i in range(1, total + 1)])
    return f"{bar} {current}/{total}"
