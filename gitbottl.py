import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events

# 1. خادم الويب لمنع Render من إيقاف الخدمة
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ==================== الإعدادات ====================
API_ID = 31726034
API_HASH = '9d0b6b8cfdda846f5dbf8543fd6f7e9e'
BOT_TOKEN = '8716514427:AAHSvYDqyThe-pTSVis8qavNc05H-Pi5EE0'

PRIVATE_CHANNEL = 'https://t.me/+g8cboJzd-dE2NmM0'
# ===================================================

bot = TelegramClient('bot_session', API_ID, API_HASH)
user_client = TelegramClient('uploader_session', API_ID, API_HASH)

@bot.on(events.NewMessage(pattern=r'^/start$', incoming=True))
async def start_handler(event):
    if not event.is_private:
        return
    await event.respond("مرحباً بك! 👋\n\nأرسل **رقم الفيديو** الذي تريد استلامه (مثال: `1` أو `2`).")

@bot.on(events.NewMessage(incoming=True))
async def video_handler(event):
    if not event.is_private or event.text.startswith('/'):
        return

    text = event.text.strip()
    if not text.isdigit():
        return

    video_num = int(text)
    user_id = event.sender_id
    status = await event.respond(f"⏳ جاري جلب الفيديو رقم **{video_num}**...")

    downloaded_file = None
    try:
        msg = await user_client.get_messages(PRIVATE_CHANNEL, ids=video_num)

        if not msg or not msg.media:
            await status.edit(f"❌ لم يتم العثور على فيديو برقم {video_num}.")
            return

        await status.edit("⏳ جاري تحضير الملف وإرساله...")
        downloaded_file = await user_client.download_media(msg)

        await bot.send_file(
            user_id,
            file=downloaded_file,
            caption=f"🎥 **فيديو رقم {video_num}**",
            protect_content=True
        )
        await status.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status.edit("❌ حدث خطأ أثناء جلب الفيديو.")

    finally:
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass

async def main():
    await user_client.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ البوت يعمل بنجاح ومستعد!")
    await asyncio.gather(
        bot.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())
