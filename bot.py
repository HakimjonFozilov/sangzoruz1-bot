import telegram
from telegram.ext import Application, CallbackContext, Job
import asyncio
import feedparser
from googleapiclient.discovery import build
import random
import os
import json
from datetime import datetime

# Telegram Bot API token
TOKEN = "7631733521:AAG0c_cGTOes_8d2Az_QAWWHOnRWrOLO8tg"
# YouTube Data API token
YOUTUBE_API_KEY = "AIzaSyB7DzrHQvLgpcZeyKeZbXV1YSOuKnQrSK0"
# Target Telegram channel
CHANNEL_ID = "@Sangzoruz1"

# Fayl nomi: qaysi yangiliklar allaqachon yuborilganini saqlaydi
POSTED_NEWS_FILE = "posted_news.json"

# YouTube API init
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# RSS manbalar
rss_urls = [
    "https://sangzor.uz/rss.xml",
]

# JSON faylдан yuborilgan yangiliklar ro'yxatini o'qish
def load_posted_news():
    if os.path.exists(POSTED_NEWS_FILE):
        with open(POSTED_NEWS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# Yangilikni ro'yxatga qo'shish
def save_posted_news(data):
    with open(POSTED_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# RSS parsing
def parse_rss(url):
    try:
        return feedparser.parse(url).entries
    except Exception as e:
        print(f"RSS xatosi: {e}")
        return []

# Barcha yangiliklarni olish
def get_local_news():
    news = []
    for url in rss_urls:
        news.extend(parse_rss(url))
    return news

# YouTube'dan o'zbekcha trend videolar olish
def get_uzbek_youtube_trending():
    try:
        queries = [
            "o'zbekcha vlog", "o'zbekcha intervyu", "o'zbekcha musiqiy klip",
            "o'zbekcha podkast", "o'zbekcha yumor", "o'zbekcha texnologiya",
            "o'zbekcha avtomobil", "o'zbekcha sport", "o'zbekcha yangiliklar"
        ]
        query = random.choice(queries)
        request = youtube.search().list(
            part="snippet",
            maxResults=5,
            q=query,
            type="video",
            regionCode="UZ",
            relevanceLanguage="uz"
        )
        response = request.execute()
        videos = response.get("items", [])
        return [random.choice(videos)] if videos else []
    except Exception as e:
        print(f"YouTube API xatosi: {e}")
        return []

# Telegram kanalga post yuborish
async def post_to_telegram(bot, message, media_url=None, media_type=None):
    try:
        message = message.encode('utf-8', 'ignore').decode('utf-8')
        if media_url and media_type == "photo":
            await bot.send_photo(chat_id=CHANNEL_ID, photo=media_url, caption=message, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")
    except Exception as e:
        print(f"Telegram post xatosi: {e}")

# Asosiy vazifa: yangilik va video yuborish
async def main(context: CallbackContext):
    bot = context.bot
    try:
        posted_news = load_posted_news()
        local_news = get_local_news()

        if local_news:
            fresh_news = [n for n in local_news if n.get("link") not in posted_news]
            selected_news = random.sample(fresh_news, k=min(3, len(fresh_news)))

            for entry in selected_news:
                image_url = None
                if "media_content" in entry and entry.media_content:
                    image_url = entry.media_content[0]["url"]
                elif "links" in entry:
                    for link_data in entry.links:
                        if link_data.get("type", "").startswith("image"):
                            image_url = link_data.get("href")
                            break

                summary = entry.get("summary") or entry.get("description") or "Тафсилотлар мавжуд эмас"
                link = entry.get("link", "")
                title = entry.get("title", "Сарлавҳа мавжуд эмас")

                message = f"<b>{title}</b>\n\n{summary[:400]}...\n\nBatafsil o'qish: {link}\n\n@SANGZORUZ1"

                await post_to_telegram(bot, message, media_url=image_url, media_type="photo" if image_url else None)

                posted_news[link] = datetime.now().isoformat()
                save_posted_news(posted_news)

                await asyncio.sleep(3)

        # YouTube videoni olish va yuborish
        trending_videos = get_uzbek_youtube_trending()
        for video in trending_videos:
            title = video["snippet"]["title"]
            thumbnail = video["snippet"]["thumbnails"]["high"]["url"]
            video_id = video["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            message = f"🎥 <b>{title}</b>\n\n{video_url}\n\n@SANGZORUZ1"

            await post_to_telegram(bot, message, media_url=thumbnail, media_type="photo")
            await asyncio.sleep(3)

    except Exception as e:
        print(f"Asosiy vazifada xatolik: {e}")

# Botni ishga tushurish
def run_bot():
    app = Application.builder().token(TOKEN).build()
    job_queue = app.job_queue
    job_queue.run_repeating(main, interval=900, first=5)  # 15 daqiqa
    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == '__main__':
    run_bot()
