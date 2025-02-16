import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# Настройки Google Sheets
SHEET_NAME = "Контент"  # Имя таблицы
WORKSHEET_NAME = "Лист1"  # Имя листа

# Настройка API доступа к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("groovy-cider-451019-e4-0604311cc0f8.json", scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

# URL сайта для парсинга
URL = "https://www.bbc.com/ukrainian"

# Функция для получения списка новостей
def get_news():
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("h2")  # Заголовки статей
    
    news_list = []
    for article in articles[:5]:  # Ограничимся 5 статьями
        link_tag = article.find("a")
        if not link_tag or "href" not in link_tag.attrs:
            continue
        
        link = link_tag["href"]
        if link.startswith("/"):
            link = "https://www.bbc.com" + link
        
        title = article.get_text(strip=True)
        news_list.append((title, link))
    
    return news_list

# Функция записи новостей в таблицу
def save_news_to_sheet(news):
    """Сохраняет новости в Google Sheets"""
    existing_titles = sheet.col_values(1)  # Заголовки из таблицы
    
    for title, link in news:
        if title not in existing_titles:
            sheet.append_row([title, link, "Ожидание"])
    print("Новости записаны в таблицу.")

# Функция получения одобренных новостей
def get_approved_news():
    """Возвращает одобренные новости из Google Sheets"""
    rows = sheet.get_all_values()
    approved_news = [(row[0], row[1]) for row in rows[1:] if len(row) > 2 and row[2].strip().lower() == "ок"]
    return approved_news

# Функция проверки таблицы и отправки новостей
def check_and_send_news():
    rows = sheet.get_all_values()
    for i, row in enumerate(rows[1:], start=2):  # Пропускаем заголовки
        title, link, status = row
        if status.strip().lower() == "ок":
            print(f"Новость одобрена: {title}")
            # Здесь можно добавить отправку в Telegram
            sheet.update_cell(i, 3, "Отправлено")
    print("Проверка завершена.")

if __name__ == "__main__":
    news = get_news()
    save_news_to_sheet(news)  # Парсим и записываем новости
    time.sleep(5)  # Ждём перед проверкой
    check_and_send_news()  # Проверяем статус и отправляем
