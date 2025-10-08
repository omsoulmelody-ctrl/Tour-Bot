import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
    ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', 0))
    
    # ============ ВАЖНАЯ ЧАСТЬ ============
    # Railway автоматически создаёт переменную DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Railway использует старый формат postgres://
        # Нужно заменить на postgresql+asyncpg://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+asyncpg://', 1)
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    else:
        # Локально используем SQLite
        database_url = 'sqlite+aiosqlite:///tourbot.db'
    
    DATABASE_URL = database_url
    # ======================================
    
    CREDENTIALS_FILE = "credentials.json"
    MIN_BUDGET = 10000
    MIN_TRAVELERS = 1
    MAX_TRAVELERS = 20
    THROTTLE_TIME = 1.0

settings = Settings()
