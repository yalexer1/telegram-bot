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
# КОНФИГУРАЦИЯ (ЗДЕСЬ ТЫ МЕНЯЕШЬ НАСТРОЙКИ)
# ============================================

# Данные для входа в Telegram (НЕ МЕНЯЙ, если всё работает)
API_ID = 37779119
API_HASH = '77062d4eaad215d7664fe96300df6ed2'
SESSION_NAME = 'my_account'

# ТВОЙ Telegram ID (владелец бота)
OWNER_ID = 7137923579

# ID кастомного премиум эмодзи 👨‍💻 (если хочешь другое - замени)
CUSTOM_EMOJI_ID = 5190917050406574667

# ============================================
# НАСТРОЙКА КАНАЛОВ И ЧАТОВ
# ============================================
# Формат: (ID_КАНАЛА, ID_ЧАТА_КУДА_ОТВЕЧАТЬ)
# Добавляй новые пары в конец списка
CHANNELS = [
    (-1003620659522, -1003651106140),  # Первый канал → первый чат
    (-1003084855353, -1002559865477),  # Второй канал → второй чат
    # ДОБАВЛЯЙ НОВЫЕ ПАРЫ СЮДА:
    # (-1001234567890, -1009876543210),  # Третий канал → третий чат
]

# ============================================
# СЛУЧАЙНЫЕ ОТВЕТЫ (ЕСЛИ НЕТ ТЕКСТА В КАВЫЧКАХ)
# ============================================
DEFAULT_RESPONSES = ['xd', 'lmao', 'ван', '1']
# МОЖЕШЬ ДОБАВЛЯТЬ СВОИ:
# DEFAULT_RESPONSES = ['xd', 'lmao', 'ван', '1', 'nice', 'cool', '👍', '🔥']

# ============================================
# НАСТРОЙКИ ВЕБ-СЕРВЕРА (НЕ ТРОГАЙ)
# ============================================
app = Flask(__name__)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
processed = set()
channel_to_chat = dict(CHANNELS)

# ============================================
# ФУНКЦИЯ ДЛЯ ПОИСКА ТЕКСТА В КАВЫЧКАХ
# ============================================
def extract_quoted(text):
    """Ищет текст в кавычках. Поддерживает: « », " ", ' ', „ “, 「 」"""
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
    """Возвращает текст для ответа: либо текст в кавычках, либо случайный ответ"""
    q = extract_quoted(text)
    return q if q else random.choice(DEFAULT_RESPONSES)

# ============================================
# КОМАНДА /checker (С ПРЕМИУМ ЭМОДЗИ)
# ============================================
@client.on(events.NewMessage)
async def checker(event):
    """Отвечает на команду /checker премиум эмодзи и текстом (Launch)"""
    if event.sender_id == OWNER_ID and event.message.message == "/checker":
        try:
            # Отправляем кастомное премиум эмодзи с текстом
            await client.send_message(
                event.chat_id,
                " (Launch)",  # Пробел + текст, эмодзи встанет на место пробела
                reply_to=event.message.id,
                formatting_entities=[MessageEntityCustomEmoji(
                    offset=0,          # Эмодзи на позиции 0 (первый символ)
                    length=1,          # Длина эмодзи - 1 символ
                    custom_emoji_id=CUSTOM_EMOJI_ID
                )]
            )
            print("✅ Команда /checker выполнена (премиум эмодзи)")
        except Exception as e:
            print(f"❌ Ошибка с премиум эмодзи: {e}")
            # Если не получилось - отправляем обычное эмодзи
            await event.reply("👨‍💻 (Launch)")

# ============================================
# КОМАНДА /channels (ПОКАЗАТЬ ВСЕ КАНАЛЫ)
# ============================================
@client.on(events.NewMessage)
async def list_channels(event):
    """Показывает список всех отслеживаемых каналов и чатов"""
    if event.sender_id == OWNER_ID and event.message.message == "/channels":
        message = "📡 **Отслеживаемые каналы:**\n\n"
        for i, (channel_id, chat_id) in enumerate(CHANNELS, 1):
            message += f"{i}. Канал: `{channel_id}`\n   → Чат: `{chat_id}`\n\n"
        await event.reply(message)
        print("✅ Команда /channels выполнена")

# ============================================
# ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ИЗ КАНАЛОВ
# ============================================
@client.on(events.NewMessage)
async def handler(event):
    """Срабатывает на каждое новое сообщение в Telegram"""
    msg = event.message
    
    # Проверяем, пришло ли сообщение из отслеживаемого канала
    if msg.sender_id not in channel_to_chat:
        return
    
    # Определяем, в какой чат нужно отвечать
    target_chat = channel_to_chat[msg.sender_id]
    
    # Уникальный ключ для сообщения (чтобы не отвечать дважды на одно)
    msg_key = f"{msg.sender_id}_{msg.id}"
    if msg_key in processed:
        return
    
    # Добавляем в обработанные
    processed.add(msg_key)
    
    # Запускаем обработку в фоне
    asyncio.create_task(process_message(msg, target_chat))

async def process_message(msg, target_chat):
    """Функция обработки сообщения и отправки ответа"""
    try:
        # Пропускаем платные посты (Telegram Premium)
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
            # Вычисляем задержку для мониторинга
            delay = time.time() - msg.date.timestamp()
            print(f"✅ Ответил на {msg.id} (канал {msg.sender_id} → чат {target_chat}) за {delay:.2f} сек")
            
        except FloodWaitError as e:
            # Если Telegram просит подождать (ограничения)
            print(f"⏳ Ждем {e.seconds} сек из-за флуда")
            await asyncio.sleep(e.seconds)
            await client.send_message(target_chat, comment, reply_to=msg.id)
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")

# ============================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER (НЕ ТРОГАЙ)
# ============================================
@app.route('/')
def index():
    """Главная страница для проверки работы"""
    return "Bot is running", 200

@app.route('/health')
def health():
    """Страница здоровья для пинга (чтобы бот не засыпал)"""
    return "OK", 200

# ============================================
# ЗАПУСК БОТА
# ============================================
async def run_telethon():
    """Запускает Telethon клиента"""
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
    
    # Получаем порт из переменных окружения (Render дает порт)
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