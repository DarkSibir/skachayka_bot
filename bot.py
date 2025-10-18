#!/usr/bin/env python3
import asyncio
import nest_asyncio
import os
import tempfile
import yt_dlp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======== FIX ДЛЯ PyCharm =========
nest_asyncio.apply()

# ======== ТОКЕН =========
TOKEN = "8071411122:AAE7qfXVzvR-LIhlelQ8RHl0PKpLQF2M4mA"

# ======== Максимальний розмір файлу =========
MAX_FILE_SIZE = 1900 * 1024 * 1024  # ~1.9 ГБ

# ======== Хендлер /start =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привіт! Надішли мені посилання на відео з YouTube, TikTok або Instagram, "
        "і я завантажу його для тебе 🎬\n\n"
        "📌 Для Instagram відео з обмеженим доступом, переконайся, що у папці бота є файл cookies.txt"
    )

# ======== Завантаження відео =========
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Якщо повідомлення не містить посилання — нічого не робимо
    if not any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com", "reel/"]):
        return  # <-- просто ігнор

    await update.message.reply_text("⏳ Завантажую відео, зачекай трохи...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
                "format": "best[height<=720][ext=mp4]/best",  # обмеження 720p для стабільності
                "quiet": True,
                "noplaylist": True,
                "socket_timeout": 300,           # таймаут 5 хвилин
                "retries": 5,                    # кількість повторів
                "noprogress": True,
                "nocheckcertificate": True,
                "http_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                "cookiefile": "cookies.txt",     # Instagram cookies
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

            # Перевірка розміру файлу
            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                await update.message.reply_text(
                    "⚠️ Відео занадто велике для відправки Telegram (>1.9GB)"
                )
                return

            # Відправка відео
            with open(file_path, "rb") as f:
                await update.message.reply_video(
                    video=f, caption=f"✅ {info.get('title', 'Відео')}"
                )

    except Exception as e:
        msg = str(e)
        if "inappropriate" in msg or "unavailable" in msg:
            await update.message.reply_text(
                "⚠️ Це відео недоступне для завантаження навіть з cookies (можливо обмеження платформи)."
            )
        else:
            await update.message.reply_text(f"❌ Помилка при завантаженні: {e}")

# ======== Головна функція =========
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    print("✅ Бот запущено... (натисни Ctrl+C для зупинки)")
    await app.run_polling()

# ======== Запуск =========
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
