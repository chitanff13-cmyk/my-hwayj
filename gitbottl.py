import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import ImportChatInviteRequest

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

PRIVATE_INVITE_LINK = 'https://t.me/+g8cboJzd-dE2NmM0'
INVITE_HASH = 'g8cboJzd-dE2NmM0'

WAIT_TIME_SECONDS = 5
# ===================================================

video_messages = []
channel_entity = None

bot = TelegramClient('bot_session', API_ID, API_HASH)
user_client = TelegramClient('uploader_session', API_ID, API_HASH)

async def load_channel_videos():
    global video_messages, channel_entity
    video_messages.clear()
    
    try:
        channel_entity = await user_client.get_entity(PRIVATE_INVITE_LINK)
    except Exception:
        try:
            updates = await user_client(ImportChatInviteRequest(INVITE_HASH))
            channel_entity = updates.chats[0]
            print("تم الانضمام للقناة الخاصة بنجاح!")
        except Exception as join_err:
            print(f"تنبيه الانضمام: {join_err}")
            channel_entity = await user_client.get_entity(PRIVATE_INVITE_LINK)

    try:
        async for message in user_client.iter_messages(channel_entity):
            if message.media:
                video_messages.append(message.id)
        video_messages.reverse()
        print(f"تم تحميل {len(video_messages)} فيديو من القناة بنجاح.")
    except Exception as e:
        print(f"خطأ أثناء قراءة القناة: {e}")

# عند إضافة فيديو جديد في القناة
@user_client.on(events.NewMessage)
async def on_new_channel_video(event):
    if channel_entity and event.chat_id == channel_entity.id:
        if event.message.media and event.message.id not in video_messages:
            video_messages.append(event.message.id)
            print(f"تمت إضافة فيديو جديد تلقائياً! العدد الكلي: {len(video_messages)}")

# التعامل مع أمر /start في الخاص فقط
@bot.on(events.NewMessage(pattern=r'^/start$', incoming=True))
async def start_handler(event):
    if not event.is_private:
        return

    total_videos = len(video_messages)
    if total_videos == 0:
        await event.respond("❌ لا توجد فيديوهات متاحة حالياً في القناة.")
        return

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
        f"اختر الفيديو المطلوب من الأزرار أدناه أو أرسل **رقم الفيديو** مباشرة."
    )
    await event.respond(welcome_msg, buttons=buttons)

# دالة معالجة وإرسال الفيديو بدون مشاكل الصلاحيات
async def send_requested_video(event, user_id, msg_id, video_num, status_msg):
    try:
        await asyncio.sleep(WAIT_TIME_SECONDS)
        
        # جلب الرسالة عبر حساب المستخدم الأدمن
        message = await user_client.get_messages(channel_entity, ids=msg_id)

        if not message or not message.media:
            await status_msg.edit("✕ لم يتم العثور على الفيديو!")
            return

        # إرسال الفيديو مباشرة من البوت عبر إعادة استخدام كائن الميديا مع حماية المحتوى
        await bot.send_file(
            user_id,
            file=message.media,
            caption=f"🎥 **فيديو رقم {video_num}**\n\n🔒 هذا المحتوى محمي وخاص بك فقط.",
            protect_content=True,
            has_spoiler=True
        )
        await status_msg.delete()

    except Exception as e:
        print(f"خطأ أثناء إرسال البوت، سيتم استخدام التوجيه المباشر بواسطة user_client: {e}")
        try:
            # طريقة احتياطية موثوقة: الإرسال عبر user_client مباشرة للمستخدم
            await user_client.send_file(
                user_id,
                file=message.media,
                caption=f"🎥 **فيديو رقم {video_num}**\n\n🔒 هذا المحتوى محمي وخاص بك فقط.",
                protect_content=True,
                has_spoiler=True
            )
            await status_msg.delete()
        except Exception as err2:
            print(f"فشل إرسال الميديا: {err2}")
            await status_msg.edit("✕ حدث خطأ أثناء إرسال الفيديو. تأكد من أن المستخدم بدأ محادثة مع البوت وحساب الأدمن.")

# التعامل مع الضغط على الأزرار
@bot.on(events.CallbackQuery(pattern=r'^vid_(\d+)_(\d+)$'))
async def callback_video_handler(event):
    msg_id = int(event.pattern_match.group(1))
    video_num = int(event.pattern_match.group(2))
    user_id = event.sender_id

    await event.answer("جاري التجهيز...")
    status_msg = await event.respond(f"⏳ جاري تجهيز الفيديو رقم **{video_num}**... يرجى الانتظار {WAIT_TIME_SECONDS} ثوانٍ.")
    await send_requested_video(event, user_id, msg_id, video_num, status_msg)

# التعامل مع كتابة رقم الفيديو نصياً
@bot.on(events.NewMessage(incoming=True))
async def video_request_handler(event):
    if not event.is_private:
        return

    text = event.text.strip() if event.text else ""
    
    if text.startswith('/') or not text.isdigit():
        return

    video_num = int(text)
    if video_num < 1 or video_num > len(video_messages):
        await event.respond(f"❌ رقم الفيديو غير موجود. المتاح حالياً من 1 إلى {len(video_messages)}.")
        return

    msg_id = video_messages[video_num - 1]
    user_id = event.sender_id

    status_msg = await event.respond(f"⏳ جاري تجهيز الفيديو رقم **{video_num}**... يرجى الانتظار {WAIT_TIME_SECONDS} ثوانٍ.")
    await send_requested_video(event, user_id, msg_id, video_num, status_msg)

async def main():
    await user_client.start()
    await bot.start(bot_token=BOT_TOKEN)
    await load_channel_videos()
    print("🤖 البوت شغال وجاهز لاستقبال الأوامر!")
    await asyncio.gather(
        bot.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
