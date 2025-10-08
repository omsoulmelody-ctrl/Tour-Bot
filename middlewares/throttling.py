import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from config.settings import settings

class ThrottlingMiddleware(BaseMiddleware):
    """Middleware для защиты от спама"""
    
    def __init__(self, throttle_time: float = settings.THROTTLE_TIME):
        self.throttle_time = throttle_time
        self.user_timings: Dict[int, float] = {}
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        
        # Проверка последнего запроса
        last_time = self.user_timings.get(user_id, 0)
        
        if current_time - last_time < self.throttle_time:
            t = data.get('t')
            wait_time = round(self.throttle_time - (current_time - last_time), 1)
            await event.answer(t('throttle', time=wait_time))
            return
        
        # Обновление времени последнего запроса
        self.user_timings[user_id] = current_time
        
        return await handler(event, data)
