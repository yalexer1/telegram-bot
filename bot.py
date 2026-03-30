import asyncio
import random
import re
import time
import os
from flask import Flask
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageEntityCustomEmoji

API_ID = 37779119
API_HASH = '77062d4eaad215d7664fe96300df6ed2'
SESSION_NAME = 'my_account'

OWNER_ID = 7137923579
CUSTOM_EMOJI_ID = 5190917050406574667

CHANNELS = [
    (-1003620659522, -1003651106140),
    (-1003084855353, -1002559865477),
]

DEFAULT_RESPONSES = ['xd', 'lmao', 'ван', '1']

app = Flask(__name__)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
processed = set()

def extract_quoted(text):
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
    q = extract_quoted(text)
    return q if q else random.choice(DEFAULT_RESPONSES)

@client.on(events.NewMessage)
async def checker(event):
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
            print("✅ /checker OK")
        except Exception as e:
            print(f"❌ /checker error: {e}")
            await event.reply("👨‍💻 (Launch)")

@client.on(events.NewMessage)
async def list_channels(event):
    if event.sender_id == OWNER_ID and event.message.message == "/channels":
        msg = "📡 **Каналы:**\n\n"
        for i, (ch, ct) in enumerate(CHANNELS, 1):
            msg += f"{i}. {ch} → {ct}\n"
        await event.reply(msg)

@client.on(events.NewMessage)
async def handler(event):
    msg = event.message
    
    channel_ids = [ch[0] for ch in CHANNELS]
    
    if msg.sender_id not in channel_ids:
        return
    
    if msg.id in processed:
        return
    
    if msg.forward:
        return
    
    if msg.reply_to_msg_id:
        return
    
    processed.add(msg.id)
    
    try:
        if msg.paid or (msg.media and getattr(msg.media, 'paid', False)):
            print(f"⭐ Skip paid {msg.id}")
            return
    except:
        pass
    
    for channel_id, chat_id in CHANNELS:
        if msg.sender_id == channel_id:
            target_chat = chat_id
            break
    
    comment = get_comment(msg.text or "")
    
    try:
        await client.send_message(target_chat, comment, reply_to=msg.id)
        delay = time.time() - msg.date.timestamp()
        print(f"✅ Replied to {msg.id} in {delay:.2f}s")
    except FloodWaitError as e:
        print(f"⏳ Flood {e.seconds}s")
        await asyncio.sleep(e.seconds)
        await client.send_message(target_chat, comment, reply_to=msg.id)
    except Exception as e:
        print(f"❌ Send error: {e}")

@app.route('/')
def index():
    return "Bot is running", 200

@app.route('/health')
def health():
    return "OK", 200

async def run_telethon():
    await client.start()
    me = await client.get_me()
    print("=" * 50)
    print(f"✅ Bot started as {me.first_name}")
    print(f"📡 Tracking {len(CHANNELS)} channels")
    for ch, ct in CHANNELS:
        print(f"   - {ch} → {ct}")
    print("🚀 Running...")
    print("=" * 50)
    await client.run_until_disconnected()

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 STARTING BOT")
    print("=" * 50)
    
    port = int(os.environ.get('PORT', 5000))
    
    import threading
    t = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port))
    t.daemon = True
    t.start()
    print(f"🌐 Web server on port {port}")
    
    print("📡 Starting Telethon...")
    asyncio.run(run_telethon())