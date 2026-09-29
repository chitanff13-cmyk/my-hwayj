import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events, Button

# 1. سيرفر الويب الخاص بـ Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ==================== الإعدادات ====================
API_ID = 31726034
API_HASH = '9d0b6b8cfdda846f5dbf8543fd6f7e9e'
BOT_TOKEN = '8716514427:AAHSvYDqyThe-pTSVis8qavNc05H-Pi5EE0'

# ضع هنا الآيدي الرقمي للقناة الخاصة (4273448312-100) أو معرف القناة
CHANNEL_ID = -8675469992  # ⚠️ استبدل هذا الرقم بآيدي قناتك الخاصة

WAIT_TIME_SECONDS = 3
# ===================================================

bot = TelegramClient('bot_session', API_ID, API_HASH)
user_client = TelegramClient('uploader_session', API_ID, API_HASH)

# التعامل مع أمر /start مباشرة وبدون تعليق
@bot.on(events.NewMessage(pattern=r'^/start$', incoming=True))
async def start_handler(event):
    if not event.is_private:
        return

    welcome_msg = (
        f"مرحباً بك! 👋\n\n"
        f"أرسل **رقم الفيديو** الذي تريد مشاهدته مباشرة (مثال: `1` أو `2` أو `5`)."
    )
    await event.respond(welcome_msg)

# التعامل مع طلب الفيديو عن طريق الرقم النصي مباشرة
@bot.on(events.NewMessage(incoming=True))
async def video_request_handler(event):
    if not event.is_private:
        return

    text = event.text.strip() if event.text else ""
    
    if text.startswith('/') or not text.isdigit():
        return

    video_num = int(text)
    user_id = event.sender_id

    status_msg = await event.respond(f"⏳ جاري البحث وجلب الفيديو رقم **{video_num}**...")

    downloaded_file = None
    try:
        # جلب الرسالة برقمها المباشر من القناة بواسطة user_client
        # افتراض أن رقم الفيديو يطابق ID الرسالة أو ترتيبها
        message = await user_client.get_messages(CHANNEL_ID, ids=video_num)

        if not message or not message.media:
            await status_msg.edit(f"❌ لم يتم العثور على فيديو برقم `{video_num}` في القناة.")
            return

        await status_msg.edit(f"⏳ جاري رفع الفيديو رقم **{video_num}**... يرجى الانتظار {WAIT_TIME_SECONDS} ثوانٍ.")
        await asyncio.sleep(WAIT_TIME_SECONDS)

        # تحميل الفيديو مؤقتاً بواسطة user_client
        downloaded_file = await user_client.download_media(message)

        # إرسال الفيديو من خلال البوت كملف محمي
        await bot.send_file(
            user_id,
            file=downloaded_file,
            caption=f"🎥 **فيديو رقم {video_num}**\n\n🔒 هذا المحتوى محمي وخاص بك فقط.",
            protect_content=True,
            has_spoiler=True
        )
        await status_msg.delete()

    except Exception as e:
        print(f"خطأ أثناء الإرسال: {e}")
        await status_msg.edit("❌ حدث خطأ أثناء جلب الفيديو. تأكد من صحة رقم الفيديو أو صلاحيات الأدمن.")

    finally:
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass

async def main():
    print("جاري تشغيل حساب المستخدم وبوت التلجرام...")
    await user_client.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 البوت شغال وجاهز تماماً الآن!")
    await asyncio.gather(
        bot.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
