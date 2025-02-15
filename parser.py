from keep_alive import keep_alive
keep_alive()

import requests
from bs4 import BeautifulSoup
import telebot

# Твой токен от BotFather
TOKEN = "7896429991:AAE83suCEXzElC6kOc1KHmlvadslJvNJ6Jo"
bot = telebot.TeleBot(TOKEN)

# ID твоего Telegram-канала
CHANNEL_ID = "@UA_in_DE_news"

# URL сайта для парсинга
URL = "https://www.bbc.com/ukrainian"

# Функция для получения текста статьи
def get_article_text(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        return "", ""

    soup = BeautifulSoup(response.text, "html.parser")

    # Находим заголовок статьи (он должен быть в <h1>)
    title_tag = soup.find("h1")
    title = title_tag.text.strip() if title_tag else "Без заголовка"

    # Ищем все абзацы <p> внутри <div>
    article_body = soup.find_all("div")  # Можно уточнить класс div, если нужно
    paragraphs = []
    
    for div in article_body:
        paragraphs.extend(div.find_all("p"))  # Собираем все <p> внутри <div>

    if len(paragraphs) < 3:
        return title, ""  # Если нет 3 абзацев, текст не берём

    # Берём первые 2 абзаца и последний
    selected_paragraphs = paragraphs[:2] + [paragraphs[-1]]
    article_text = "\n".join(p.text.strip() for p in selected_paragraphs)

    return title, article_text

# Функция парсинга новостей
def get_news():
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("h3")  # Заголовки статей

    news_list = []
    for article in articles[:1]:  # Берём 1 свежую новость
        link_tag = article.find("a")  # Ищем ссылку внутри h3

        if not link_tag or "href" not in link_tag.attrs:
            continue  # Если нет ссылки, пропускаем

        link = link_tag["href"]
        if link.startswith("/"):
            link = "https://www.bbc.com" + link

        title, article_text = get_article_text(link)
        if not article_text:
            continue  # Если нет текста, не отправляем

        message = f"📰 *{title}*\n\n{article_text}\n\n🔗 {link}"
        news_list.append(message)
    
    return news_list

# Функция отправки новостей в Telegram
def send_news():
    news = get_news()
    if not news:
        return

    for item in news:
        bot.send_message(CHANNEL_ID, item, parse_mode="Markdown")

# Запуск
send_news()
