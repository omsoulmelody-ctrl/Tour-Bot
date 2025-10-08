import gspread
from google.oauth2.service_account import Credentials
from config.settings import settings
import asyncio
from functools import partial
import os
import json

def _sync_save_to_sheets(request):
    """Синхронное сохранение в Google Sheets"""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # ============ ВАЖНАЯ ЧАСТЬ ============
        # Проверяем, есть ли переменная GOOGLE_CREDENTIALS_JSON
        credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        
        if credentials_json:
            # На Railway: парсим JSON из переменной
            credentials_dict = json.loads(credentials_json)
            creds = Credentials.from_service_account_info(
                credentials_dict,
                scopes=scopes
            )
        else:
            # Локально: читаем из файла
            creds = Credentials.from_service_account_file(
                settings.CREDENTIALS_FILE,
                scopes=scopes
            )
        # ======================================
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.SPREADSHEET_ID).sheet1
        
        row = [
            request.id,
            request.user_id,
            request.username or 'N/A',
            request.destination,
            request.departure_date,
            request.nights,
            request.adults,
            request.children,
            request.budget,
            request.comment or 'Нет',
            request.created_at.strftime('%d.%m.%Y %H:%M')
        ]
        
        sheet.append_row(row)
        
    except Exception as e:
        print(f"Ошибка записи в Google Sheets: {e}")
        raise

async def save_to_sheets(request):
    """Асинхронное сохранение в Google Sheets"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_sync_save_to_sheets, request))
