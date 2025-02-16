import gspread
from google.oauth2.service_account import Credentials

# Подключаемся к Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "groovy-cider-451019-e4-0604311cc0f8.json"  # Замени на имя своего файла

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Открываем таблицу по названию
spreadsheet = client.open("Контент")  # Замени на имя своей таблицы
sheet = spreadsheet.sheet1  # Первый лист

# Записываем тестовые данные
sheet.append_row(["Тест заголовка", "Тест ссылки"])

print("✅ Данные успешно добавлены в таблицу!")
