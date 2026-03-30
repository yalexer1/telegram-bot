import asyncio
import random
import re
import time
import os
import threading
from flask import Flask, request
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# ============================================
# КОНФИГУРАЦИЯ БОТА
# ============================================
# ВНИМАНИЕ! Эти данные уже настроены для вашего бота
# Если нужно изменить чаты - меняйте здесь

API_ID = 37779119
API_HASH = '77062d4eaad215d7664fe96300df6ed2'
SESSION_NAME = 'my_account'

# ID канала, из которого приходят посты
CHANNEL_ID = -1003620659522
# ID чата, куда нужно отвечать
CHAT_ID = -1003651106140
# Ваш Telegram ID (владелец)
OWNER_ID = 7137923579

# Случайные ответы, если нет текста в кавычках
DEFAULT_RESPONSES = ['xd', 'lmao', 'ван', '1']

# ============================================
# НАСТРОЙКА ВЕБ-СЕРВЕРА (НУЖНО ДЛЯ RENDER)
# ============================================

# Создаем Flask приложение
app = Flask(__name__)

# Создаем Telethon клиента
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Множество для хранения ID обработанных сообщений
# Нужно, чтобы бот не отвечал на одно сообщение дважды
processed = set()

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def extract_quoted(text):
    """
    Функция ищет текст в кавычках.
    Поддерживает разные виды кавычек: « », " ", ' ', „ “, 「 」.
    
    Пример:
        text = 'Он сказал: "Привет мир!"'
        результат = "Привет мир!"
    """
    if not text:
        return None
    
    # Проверяем все возможные виды кавычек
    for quote_pair in [('«', '»'), ('"', '"'), ("'", "'"), ('„', '“'), ('「', '」')]:
        # Ищем открывающую кавычку
        start = text.find(quote_pair[0])
        if start != -1:
            # Ищем закрывающую кавычку после открывающей
            end = text.find(quote_pair[1], start + 1)
            if end != -1:
                # Возвращаем текст между кавычками
                return text[start + 1:end].strip()
    
    return None

def get_comment(text):
    """
    Функция определяет, чем ответить на пост.
    Если есть текст в кавычках - отвечает им.
    Если нет - выбирает случайный ответ из DEFAULT_RESPONSES.
    """
    q = extract_quoted(text)
    return q if q else random.choice(DEFAULT_RESPONSES)

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@client.on(events.NewMessage)
async def checker(event):
    """
    Обработчик команды /checker.
    Когда владелец (OWNER_ID) пишет /checker, бот отвечает.
    """
    # Проверяем, что сообщение от владельца и это команда /checker
    if event.sender_id == OWNER_ID and event.message.message == "/checker":
        try:
            # Отправляем ответ с эмодзи и текстом
            await event.reply("👨‍💻 (Launch)")
            print("✅ Команда /checker выполнена")
        except Exception as e:
            print(f"❌ Ошибка при отправке ответа: {e}")
            # Если не получилось с эмодзи, отправляем простой текст
            await event.reply("(Launch)")

@client.on(events.NewMessage(chats=CHAT_ID))
async def handler(event):
    """
    Основной обработчик новых сообщений в чате.
    Срабатывает на каждое новое сообщение в CHAT_ID.
    """
    msg = event.message
    
    # Если это сообщение уже обработано - пропускаем
    if msg.id in processed:
        return
    
    # Добавляем ID в обработанные, чтобы не обработать дважды
    processed.add(msg.id)
    
    # Запускаем обработку в фоне (чтобы не блокировать другие сообщения)
    asyncio.create_task(process_message(msg))

async def process_message(msg):
    """
    Функция обработки сообщения.
    Здесь происходит основная логика: проверка отправителя и отправка ответа.
    """
    try:
        # Проверяем, что сообщение пришло ИЗ КАНАЛА
        # Если отправитель не канал - ничего не делаем
        if msg.sender_id != CHANNEL_ID:
            return
        
        # Проверяем, не является ли пост платным
        try:
            # Telegram Premium посты имеют атрибут paid
            if getattr(msg, 'paid', False):
                print(f"⭐ Пропускаем платный пост {msg.id}")
                return
            # Проверяем медиа (фото/видео) на платность
            if msg.media and getattr(msg.media, 'paid', False):
                print(f"⭐ Пропускаем платный пост с медиа {msg.id}")
                return
        except:
            # Если проверка не удалась (нет атрибута) - пропускаем
            pass
        
        # Получаем текст для ответа
        comment = get_comment(msg.text or "")
        
        # Отправляем ответ в чат
        try:
            await client.send_message(
                CHAT_ID,           # куда отправляем
                comment,           # текст ответа
                reply_to=msg.id    # отвечаем на конкретное сообщение
            )
            # Вычисляем задержку для мониторинга
            delay = time.time() - msg.date.timestamp()
            print(f"✅ Ответил на сообщение {msg.id} за {delay:.2f} секунд")
            
        except FloodWaitError as e:
            # Если Telegram говорит "подожди" (лимиты)
            print(f"⏳ Нужно подождать {e.seconds} секунд из-за флуда")
            await asyncio.sleep(e.seconds)
            # Повторяем отправку после ожидания
            await client.send_message(CHAT_ID, comment, reply_to=msg.id)
        except Exception as e:
            print(f"❌ Ошибка при отправке сообщения: {e}")
            
    except Exception as e:
        print(f"❌ Ошибка в обработчике сообщения: {e}")

# ============================================
# ЗАПУСК TELETHON В ОТДЕЛЬНОМ ПОТОКЕ
# ============================================

def run_telethon():
    """
    Функция запуска Telethon клиента в отдельном потоке.
    Это нужно, чтобы бот работал параллельно с веб-сервером.
    """
    # Создаем новый цикл событий для потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def main():
        # Запускаем клиента
        await client.start()
        # Получаем информацию об аккаунте
        me = await client.get_me()
        print(f"✅ Бот запущен как {me.first_name} (@{me.username})")
        print("🚀 Бот работает и ожидает сообщения...")
        print("=" * 50)
        # Запускаем бесконечный цикл обработки событий
        await client.run_until_disconnected()
    
    # Запускаем асинхронную функцию
    loop.run_until_complete(main())

# ============================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ============================================

@app.route('/')
def index():
    """
    Главная страница. Render проверяет, что сервер работает.
    Возвращает простой текст.
    """
    return "Bot is running", 200

@app.route('/health')
def health():
    """
    Страница проверки здоровья.
    Используется для пинга (чтобы бот не засыпал).
    """
    return "OK", 200

# ============================================
# ЗАПУСК ВСЕГО ПРИЛОЖЕНИЯ
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 ЗАПУСК TELEGRAM БОТА")
    print("=" * 50)
    
    # Запускаем Telethon в фоновом потоке
    print("📡 Запускаем Telethon клиент...")
    bot_thread = threading.Thread(target=run_telethon, daemon=True)
    bot_thread.start()
    
    # Небольшая пауза, чтобы клиент успел запуститься
    time.sleep(2)
    
    print("🌐 Запускаем веб-сервер для Render...")
    # Получаем порт из переменных окружения (Render сам дает порт)
    port = int(os.environ.get('PORT', 5000))
    # Запускаем Flask сервер
    app.run(host='0.0.0.0', port=port)