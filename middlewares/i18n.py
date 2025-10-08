import json
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

class I18nMiddleware(BaseMiddleware):
    """Middleware для мультиязычности"""
    
    def __init__(self):
        self.translations = {
            'ru': self._load_locale('ru'),
            'en': self._load_locale('en')
        }
        super().__init__()
    
    def _load_locale(self, lang: str) -> dict:
        """Загрузка файла локали"""
        try:
            with open(f'locales/{lang}.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get('event_from_user')
        
        # Определение языка (русский по умолчанию)
        lang = 'ru'
        if user and user.language_code:
            if user.language_code.startswith('en'):
                lang = 'en'
        
        # Функция перевода
        def t(key: str, **kwargs) -> str:
            text = self.translations.get(lang, {}).get(key, key)
            return text.format(**kwargs) if kwargs else text
        
        data['t'] = t
        data['lang'] = lang
        
        return await handler(event, data)
