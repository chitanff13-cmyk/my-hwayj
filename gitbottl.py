import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events, Button

# 1. تعريف السيرفر واستجابته لطلبات GET و HEAD لمنع توقف Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

# 2. تعريف دالة تشغيل السيرفر
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# 3. استدعاء التشغيل في خلفية مستقلة
threading.Thread(target=run_web_server, daemon=True).start()

# ==================== الإعدادات ====================
API_ID = 31726034
API_HASH = '9d0b6b8cfdda846f5dbf8543fd6f7e9e'
BOT_TOKEN = '8716514427:AAHSvYDqyThe-pTSVis8qavNc05H-Pi5EE0' # احصل عليه من @BotFather

# أيدي القناة التي تحتوي على الفيديوهات
SOURCE_CHANNEL = -1004273448312  # استبدله بأيدي قناتك إذا كان مختلفاً

# عدد ثواني الانتظار قبل إرسال الفيديو للزبون
WAIT_TIME_SECONDS = 5
# ===================================================

# قائمة لتخزين معرّفات الفيديوهات (IDs) الموجودة بالقناة
video_messages = []

# عميل البوت للاستجابة للزبائن
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# عميل الحساب الشخصي (الأدمن) لسحب الملفات من القناة
user_client = TelegramClient('uploader_session', API_ID, API_HASH)

# دالة لجلب وترتيب الفيديوهات من القناة عند تشغيل البوت
async def load_channel_videos():
    global video_messages
    video_messages.clear()
    async for message in user_client.iter_messages(SOURCE_CHANNEL):
        if message.video or message.document or message.media:
            video_messages.append(message.id)
    # ترتيب الفيديوهات من الأقدم إلى الأحدث
    video_messages.reverse()

# استماع للقناة الخاصة: عند نشر أي فيديو جديد يزيد العداد والأزرار تلقائياً
@user_client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def on_new_channel_video(event):
    if event.message.video or event.message.document or event.message.media:
        if event.message.id not in video_messages:
            video_messages.append(event.message.id)

# الاستجابة لأمر /start وإرسال عدد الفيديوهات مع أزرار الخيارات
@bot.on(events.NewMessage(pattern=r'^/start$'))
async def start_handler(event):
    total_videos = len(video_messages)
    if total_videos == 0:
        await event.respond("❌ لا توجد فيديوهات متاحة في القناة حالياً.")
        return

    # إنشاء أزرار شفافة (كل سطر يحوي 5 أزرار)
    buttons = []
    row = []
    for index, msg_id in enumerate(video_messages, start=1):
        row.append(Button.inline(f"فيديو {index} 🎬", data=f"vid_{msg_id}_{index}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    welcome_msg = (
        f"مرحباً بك! 👋\n\n"
        f"🎥 **عدد الفيديوهات المتاحة حالياً:** `{total_videos}` فيديو.\n"
        f"اضغط على أيقونة الفيديو أدناه أو أرسل **رقم الفيديو** فقط (مثال: `1` أو `15`)."
    )
    await event.respond(welcome_msg, buttons=buttons)

# معالجة الضغط على الأزرار الشفافة
@bot.on(events.CallbackQuery(pattern=r'^vid_(\d+)_(\d+)$'))
async def callback_video_handler(event):
    msg_id = int(event.pattern_match.group(1))
    video_num = int(event.pattern_match.group(2))
    user_id = event.sender_id

    await event.answer("جاري التجهيز...")
    status_msg = await event.respond(f"⏳ جاري تجهيز الفيديو رقم **{video_num}**... يرجى الانتظار {WAIT_TIME_SECONDS} ثوانٍ.")

    try:
        await asyncio.sleep(WAIT_TIME_SECONDS)
        message = await user_client.get_messages(SOURCE_CHANNEL, ids=msg_id)

        if not message or not message.media:
            await status_msg.edit("✕ لم يتم العثور على فيديو بهذا الرقم!")
            return

        await bot.send_file(
            user_id,
            file=message.media,
            caption=f"🎥 **فيديو رقم {video_num}**\n\n🔒 هذا المحتوى محمي وخاص بك فقط.",
            protect_content=True,
            has_spoiler=True
        )
        await status_msg.delete()

    except Exception as e:
        print(f"خطأ أثناء جلب الفيديو: {e}")
        await status_msg.edit("✕ حدث خطأ أثناء إرسال الفيديو. تأكد من الرقم وصلاحيات الأدمن.")

# معالجة الطلب عند كتابة رقم الفيديو كتابةً
@bot.on(events.NewMessage)
async def video_request_handler(event):
    text = event.text.strip()
    
    if text == "/start":
        return

    if not text.isdigit():
        await event.respond("⚠️ يرجى إرسال رقم الفيديو فقط (مثال: 5) أو اختيار زر من القائمة.")
        return

    video_num = int(text)
    if video_num < 1 or video_num > len(video_messages):
        await event.respond(f"❌ رقم الفيديو غير موجود. المتاح حالياً من 1 إلى {len(video_messages)}.")
        return

    msg_id = video_messages[video_num - 1]
    user_id = event.sender_id

    status_msg = await event.respond(f"⏳ جاري تجهيز الفيديو رقم **{video_num}**... يرجى الانتظار {WAIT_TIME_SECONDS} ثوانٍ.")

    try:
        await asyncio.sleep(WAIT_TIME_SECONDS)
        message = await user_client.get_messages(SOURCE_CHANNEL, ids=msg_id)

        if not message or not message.media:
            await status_msg.edit("✕ لم يتم العثور على فيديو بهذا الرقم!")
            return

        await bot.send_file(
            user_id,
            file=message.media,
            caption=f"🎥 **فيديو رقم {video_num}**\n\n🔒 هذا المحتوى محمي وخاص بك فقط.",
            protect_content=True,
            has_spoiler=True
        )
        await status_msg.delete()

    except Exception as e:
        print(f"خطأ أثناء جلب الفيديو: {e}")
        await status_msg.edit("✕ حدث خطأ أثناء إرسال الفيديو. تأكد من الرقم وصلاحيات الأدمن.")

async def main():
    await user_client.start()
    await load_channel_videos()
    print("🤖 بوت التوزيع الحصري شغال وجاهز لاستقبال الطلبات!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
