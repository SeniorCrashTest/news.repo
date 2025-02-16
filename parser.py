import requests
from bs4 import BeautifulSoup
import telebot
import os
from dotenv import load_dotenv
from news_parser_gsheets import save_news_to_sheet, get_approved_news, get_news

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = telebot.TeleBot(TOKEN)

# Функция парсинга и сохранения новостей
def fetch_and_save_news():
    news = get_news()  # Получаем новости
    if news:
        save_news_to_sheet(news)  # Сохраняем их в Google Sheets
        print("Новости сохранены в Google Sheets.")

# Функция отправки одобренных новостей
def send_approved_news():
    news = get_approved_news()  # Получаем одобренные новости
    if not news:
        print("Нет одобренных новостей.")
        return

    for title, link in news:
        message = f"*{title}*\n\n🔗 [Читать статью]({link})"
        bot.send_message(CHANNEL_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
    print("Одобренные новости отправлены.")

# Запуск
fetch_and_save_news()  # Сначала парсим и сохраняем новости
send_approved_news()    # Потом отправляем только одобренные
