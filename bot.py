#!/usr/bin/env python3
import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import nest_asyncio  # для PyCharm
nest_asyncio.apply()  # дозволяє вкладати event loop всередині PyCharm

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ===== CONFIG =====
TELEGRAM_TOKEN = "8071411122:AAE7qfXVzvR-LIhlelQ8RHl0PKpLQF2M4mA"
YTDLP_CMD = "yt-dlp.exe" if Path("yt-dlp.exe").exists() else "yt-dlp"
MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
# ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привітальне повідомлення"""
    await update.message.reply_text(
        "👋 Привіт!\n"
        "Надішли мені посилання з YouTube / TikTok / Instagram — я завантажу відео.\n"
        "⚠️ Максимальний розмір файлу: 2 GB."
    )

def is_url(text: str) -> bool:
    """Перевірка, чи є текст URL"""
    return text.startswith(("http://", "https://"))

async def download_with_yt_dlp(url: str, out_dir: str) -> Path:
    """Асинхронне завантаження відео через yt-dlp"""
    out_template = str(Path(out_dir) / "%(title)s.%(ext)s")
    cmd = [
        YTDLP_CMD,
        url,
        "-f", "bv*+ba/best",
        "-o", out_template,
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--remux-video", "mp4",
        "--ffmpeg-location", "ffmpeg",
        "--extractor-args", "tiktok:player_url=https://www.tiktok.com",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"yt-dlp помилка:\n{stderr.decode(errors='ignore').strip() or stdout.decode(errors='ignore')}"
        )

    files = list(Path(out_dir).glob("*"))
    if not files:
        raise FileNotFoundError("Не знайдено завантажених файлів.")
    return max(files, key=lambda p: p.stat().st_size)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка повідомлень користувача"""
    msg = update.message
    text = (msg.text or "").strip()
    if not text or not is_url(text):
        await msg.reply_text("Надішли правильне посилання (http/https).")
        return

    reply = await msg.reply_text("⏳ Завантажую відео...")
    tmpdir = tempfile.mkdtemp(prefix="tg_dload_")

    try:
        try:
            file_path = await download_with_yt_dlp(text, tmpdir)
        except Exception as e:
            await reply.edit_text(f"❌ Помилка під час завантаження:\n{e}")
            return

        size = file_path.stat().st_size
        if size > MAX_FILE_BYTES:
            await reply.edit_text(
                f"⚠️ Відео занадто велике ({size / 1024 / 1024:.1f} MB > 2 GB).\n"
                "Telegram не може надіслати такий файл."
            )
            return

        await reply.edit_text("📤 Надсилаю відео...")
        try:
            with open(file_path, "rb") as f:
                await msg.reply_video(f, filename=file_path.name, supports_streaming=True)
        except Exception:
            with open(file_path, "rb") as f:
                await msg.reply_document(f, filename=file_path.name)

        await reply.delete()

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

async def main():
    """Основна функція запуску бота"""
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN не задано!")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущено! Очікую повідомлень...")
    await app.run_polling()

# ===== запуск бота =====
if __name__ == "__main__":
    asyncio.run(main())