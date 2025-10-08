import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from aiogram.types import User
from config.settings import settings
import asyncio
from functools import partial

async def send_to_sheets(data: dict, user: User):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_send_to_sheets_sync, data, user))

def _send_to_sheets_sync(data: dict, user: User):
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(settings.sheets.credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.sheets.spreadsheet_id).sheet1
        row = [datetime.now().strftime("%d.%m.%Y %H:%M"), user.id, user.username or "Нет",
               user.first_name or "Нет", data.get('destination', '-'), data.get('departure_city', '-'),
               data.get('departure_date', '-'), data.get('duration', '-'), data.get('adults', 0),
               data.get('children', 0), data.get('budget', '-'), data.get('additional_info', 'Нет')]
        sheet.append_row(row)
        print("✅ Отправлено в Sheets")
    except Exception as e:
        print(f"❌ Sheets error: {e}")
