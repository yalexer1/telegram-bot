import asyncio
import random
import re
import time
import os
from flask import Flask
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageEntityCustomEmoji

# ============================================
# КОНФИГУРАЦИЯ
# ============================================
API_ID = 37779119
API_HASH = '77062d4eaad215d7664fe96300df6ed2'
SESSION_NAME = 'my_account'

OWNER_ID = 7137923579
CUSTOM_EMOJI_ID = 5190917050406574667

# КАНАЛЫ И ЧАТЫ
CHANNELS = [
    (-1003620659522, -1003651106140),  # Первый канал → первый чат
    (-1003084855353, -1002559865477),  # Второй канал → второй чат
]

# СЛУЧАЙНЫЕ ОТВЕТЫ
DEFAULT_RESPONSES = ['xd', 'lmao', 'ван', '1']

# ============================================
# НАСТРОЙКА
# ============================================
app = Flask(__name__)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
processed = set()
channel_to_chat = dict(CHANNELS)

# ============================================
# ФУНКЦИИ
# ============================================
def extract_quoted(text):
    """Извлекает текст в кавычках"""
    if not text:
        return None
    for quote_pair in [('«', '»'), ('"', '"'), ("'", "'"), ('„', '“'), ('「', '」')]:
        start = text.find(quote_pair[0])
        if start != -1:
            end = text.find(quote_pair[1], start + 1)
            if end != -1:
                return text[start + 1:end].strip()
    return None

def get_comment(text):
    """Возвращает текст для ответа"""
    q = extract_quoted(text)
    return q if q else random.choice(DEFAULT_RESPONSES)

# ============================================
# КОМАНДЫ
# ============================================
@client.on(events.NewMessage)
async def checker(event):
    """Команда /checker - проверка работы"""
    if event.sender_id == OWNER_ID and event.message.message == "/checker":
        try:
            await client.send_message(
                event.chat_id,
                " (Launch)",
                reply_to=event.message.id,
                formatting_entities=[MessageEntityCustomEmoji(
                    offset=0,
                    length=1,
                    custom_emoji_id=CUSTOM_EMOJI_ID
                )]
            )
            print("✅ Команда /checker выполнена")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await event.reply("👨‍💻 (Launch)")

@client.on(events.NewMessage)
async def list_channels(event):
    """Команда /channels - показать все каналы"""
    if event.sender_id == OWNER_ID and event.message.message == "/channels":
        message = "📡 **Отслеживаемые каналы:**\n\n"
        for i, (channel_id, chat_id) in enumerate(CHANNELS, 1):
            message += f"{i}. Канал: `{channel_id}`\n   → Чат: `{chat_id}`\n\n"
        await event.reply(message)
        print("✅ Команда /channels выполнена")

# ============================================
# ОСНОВНОЙ ОБРАБОТЧИК
# ============================================
@client.on(events.NewMessage)
async def handler(event):
    """Обработчик новых сообщений из каналов"""
    msg = event.message
    
    # Проверяем, пришло ли сообщение из отслеживаемого канала
    if msg.sender_id not in channel_to_chat:
        return
    
    # Получаем ID чата для этого канала
    target_chat = channel_to_chat[msg.sender_id]
    
    # Уникальный ключ для сообщения (канал + ID сообщения)
    msg_key = f"{msg.sender_id}_{msg.id}"
    if msg_key in processed:
        return
    
    processed.add(msg_key)
    
    # Запускаем обработку в фоне
    asyncio.create_task(process_message(msg, target_chat))

async def process_message(msg, target_chat):
    """Обработка сообщения и отправка ответа"""
    try:
        # Пропускаем платные посты
        try:
            if getattr(msg, 'paid', False) or (msg.media and getattr(msg.media, 'paid', False)):
                print(f"⭐ Пропускаем платный пост из канала {msg.sender_id} (ID: {msg.id})")
                return
        except:
            pass
        
        # Получаем текст для ответа
        comment = get_comment(msg.text or "")
        
        # Отправляем ответ
        try:
            await client.send_message(
                target_chat,
                comment,
                reply_to=msg.id
            )
            delay = time.time() - msg.date.timestamp()
            print(f"✅ Ответил на {msg.id} (канал {msg.sender_id} → чат {target_chat}) за {delay:.2f} сек")
            
        except FloodWaitError as e:
            print(f"⏳ Ждем {e.seconds} сек из-за флуда")
            await asyncio.sleep(e.seconds)
            await client.send_message(target_chat, comment, reply_to=msg.id)
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")

# ============================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ============================================
@app.route('/')
def index():
    """Главная страница для проверки"""
    return "Bot is running", 200

@app.route('/health')
def health():
    """Страница здоровья для пинга"""
    return "OK", 200

# ============================================
# ЗАПУСК
# ============================================
async def run_telethon():
    """Запуск Telethon клиента"""
    await client.start()
    me = await client.get_me()
    print("=" * 50)
    print(f"✅ Бот запущен как {me.first_name} (@{me.username})")
    print(f"📡 Отслеживаем {len(CHANNELS)} каналов:")
    for channel_id, chat_id in CHANNELS:
        print(f"   - Канал {channel_id} → Чат {chat_id}")
    print("🚀 Бот работает и ожидает сообщения...")
    print("=" * 50)
    await client.run_until_disconnected()

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 ЗАПУСК TELEGRAM БОТА")
    print("=" * 50)
    
    # Получаем порт из переменных окружения
    port = int(os.environ.get('PORT', 5000))
    
    # Запускаем Flask в отдельном потоке
    import threading
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port))
    flask_thread.daemon = True
    flask_thread.start()
    print(f"🌐 Веб-сервер запущен на порту {port}")
    
    # Запускаем Telethon в основном потоке
    print("📡 Запускаем Telethon...")
    asyncio.run(run_telethon())