import os
from dotenv import load_dotenv
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
import requests
import re
import yt_dlp
from googleapiclient.discovery import build

# Загрузка переменных окружения из файла .env
load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
WEATHER_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')

# Настройка логирования
logging.basicConfig(level = logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token = API_TOKEN)
dp = Dispatcher()

# Инициализация YouTube API клиента
youtube = build('youtube', 'v3', developerKey = YOUTUBE_API_KEY)


# Пример хендлера с использованием CommandStart
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Отправьте мне текстовый запрос и получишь ссылку на YouTube-видео (/look), "
                         "или отправьте мне ссылку на YouTube-видео и я пришлю информацию о нем (/start).")


# Пример хендлера с использованием Command
@dp.message(Command(commands = ["help"]))
async def help_command(message: Message):
    await message.answer("Этот бот умеет выполнять команды:\n/start\n/help\n/weather\n/look [описание]")


# Прописываем хендлер для команды /weather
@dp.message(Command(commands = ["weather"]))
async def weather_command(message: Message):
    city = "minsk"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    data = response.json()

    if data["cod"] == 200:
        temperature = data["main"]["temp"]
        description = data["weather"][0]["description"]
        await message.answer(f"Погода в {city.capitalize()}:\nТемпература: {temperature}°C\nОписание: {description}")
    else:
        await message.answer("Не удалось получить прогноз погоды. Пожалуйста, попробуйте позже.")


# Прописываем хендлер для обработки ссылок на YouTube
@dp.message(lambda message: re.match(r'https?://(www\.)?youtube\.com/watch\?v=.+', message.text))
async def youtube_info(message: Message):
    url = message.text
    if not re.match(r"^https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+$", url):
        await message.reply("Некорректная ссылка на YouTube. Пожалуйста, отправьте корректную ссылку.")
        return

    try:
        ydl_opts = {}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download = False)
            title = info_dict.get('title', None)
            author = info_dict.get('uploader', None)
            description = info_dict.get('description', None)
            await message.reply(f"**Название:** {title}\n**Автор:** {author}\n**Описание:** {description}")
    except Exception as e:
        logging.error(f"Произошла ошибка при обработке ссылки: {e}")
        await message.reply(f"Произошла ошибка при обработке ссылки. Ошибка: {str(e)}")


# Прописываем хендлер для команды /look
@dp.message(Command(commands = ["look"]))
async def look_command(message: Message):
    query = message.text[len("/look "):].strip()
    if not query:
        await message.reply("Пожалуйста, предоставьте текстовое описание для поиска.")
        logging.info("Запрос пустой.")
        return

    logging.info(f"Поисковый запрос: {query}")

    try:
        search_response = youtube.search().list(
            q = query,
            part = "snippet",
            maxResults = 1
        ).execute()

        logging.info(f"Ответ API: {search_response}")

        if 'items' in search_response and search_response['items']:
            video_id = search_response['items'][0]['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            video_title = search_response['items'][0]['snippet']['title']
            logging.info(f"Видео найдено: {video_title}, {video_url}")
            await message.reply(f"**Название:** {video_title}\n**Ссылка:** {video_url}")
        else:
            logging.info("Видео по вашему запросу не найдено.")
            await message.reply("Видео по вашему запросу не найдено.")
    except Exception as e:
        logging.error(f"Произошла ошибка при выполнении поиска: {e}")
        await message.reply(f"Произошла ошибка при выполнении поиска. Ошибка: {str(e)}")


async def main():
    dp.message.register(start, CommandStart())
    dp.message.register(help_command, Command(commands = ["help"]))
    dp.message.register(weather_command, Command(commands = ["weather"]))
    dp.message.register(youtube_info,
                        lambda message: re.match(r'https?://(www\.)?youtube\.com/watch\?v=.+', message.text))
    dp.message.register(look_command, Command(commands = ["look"]))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
