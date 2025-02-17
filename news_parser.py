import requests
from bs4 import BeautifulSoup
import telebot
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = telebot.TeleBot(TOKEN)

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

# Функция отправки новостей в Telegram
def send_news_to_telegram():
    news = get_news()  # Получаем новости
    if not news:
        print("Нет новостей для отправки.")
        return

    for title, link in news:
        message = f"*{title}*\n\n🔗 [Читать статью]({link})"
        bot.send_message(CHANNEL_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
    print("Новости отправлены в Telegram.")

# Запуск
send_news_to_telegram()
