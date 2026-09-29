import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events, Button

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
VIDEOS_PER_PAGE = 9  # عدد الفيديوهات في كل صفحة (3 أسطر × 3 أزرار)
# ===================================================

bot = TelegramClient('bot_session', API_ID, API_HASH)
user_client = TelegramClient('uploader_session', API_ID, API_HASH)

# دالة جلب الفيديوهات الحقيقية فقط من القناة بترتيبها
async def get_channel_videos():
    video_messages = []
    async for message in user_client.iter_messages(PRIVATE_CHANNEL, reverse=True):
        if message.video or message.document or (message.media and getattr(message.media, 'document', None)):
            if message.file and message.file.mime_type and message.file.mime_type.startswith('video/'):
                video_messages.append(message.id)
    return video_messages

# بناء الواجهة بالأزرار والصفحات
def build_page_keyboard(video_ids, page=1):
    total_videos = len(video_ids)
    total_pages = (total_videos + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE if total_videos > 0 else 1

    start_idx = (page - 1) * VIDEOS_PER_PAGE
    end_idx = min(start_idx + VIDEOS_PER_PAGE, total_videos)

    buttons = []
    row = []

    for index in range(start_idx, end_idx):
        msg_id = video_ids[index]
        display_num = index + 1
        row.append(Button.inline(f"🎬 فيديو {display_num}", data=f"getmsg_{msg_id}_{display_num}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # أزرار التنقل بين الصفحات
    nav_row = []
    if page > 1:
        nav_row.append(Button.inline("◀ السابق", data=f"page_{page - 1}"))
    
    nav_row.append(Button.inline(f"📄 {page}/{total_pages}", data="ignore"))

    if page < total_pages:
        nav_row.append(Button.inline("التالي ▶", data=f"page_{page + 1}"))

    buttons.append(nav_row)
    return buttons, total_videos, total_pages

# عند إرسال /start
@bot.on(events.NewMessage(pattern=r'^/start$', incoming=True))
async def start_handler(event):
    if not event.is_private:
        return

    status = await event.respond("⏳ **جاري فحص القناة وتنظيم قائمة الفيديوهات...**")

    try:
        video_ids = await get_channel_videos()

        if not video_ids:
            await status.edit("❌ **لا توجد أي فيديوهات متوفرة في القناة حالياً.**")
            return

        buttons, total_videos, total_pages = build_page_keyboard(video_ids, page=1)

        msg = (
            f"✨ **أهلاً بك في البوت الرسمي**\n\n"
            f"📊 **إجمالي الفيديوهات المتاحة:** `{total_videos}` فيديو\n"
            f"إختر الفيديو الذي تريده من القائمة أدناه:"
        )
        await status.edit(msg, buttons=buttons)

    except Exception as e:
        print(f"Error starting bot: {e}")
        await status.edit("❌ **حدث خطأ أثناء الاتصال بالقناة.**")

# التنقل بين الصفحات
@bot.on(events.CallbackQuery(pattern=r'^page_(\d+)$'))
async def page_handler(event):
    page = int(event.pattern_match.group(1))
    await event.answer()

    try:
        video_ids = await get_channel_videos()
        buttons, total_videos, total_pages = build_page_keyboard(video_ids, page=page)

        msg = (
            f"✨ **أهلاً بك في البوت الرسمي**\n\n"
            f"📊 **إجمالي الفيديوهات المتاحة:** `{total_videos}` فيديو\n"
            f"إختر الفيديو الذي تريده من القائمة أدناه:"
        )
        await event.edit(msg, buttons=buttons)
    except Exception as e:
        print(f"Error navigating page: {e}")

# عند الضغط على زر فيديو معين
@bot.on(events.CallbackQuery(pattern=r'^getmsg_(\d+)_(\d+)$'))
async def callback_video_handler(event):
    msg_id = int(event.pattern_match.group(1))
    display_index = int(event.pattern_match.group(2))
    user_id = event.sender_id

    await event.answer("جاري التحميل...")
    status = await event.respond(f"⏳ **جاري تحضير فيديو رقم {display_index}...**")

    downloaded_file = None
    try:
        msg = await user_client.get_messages(PRIVATE_CHANNEL, ids=msg_id)

        if not msg or not msg.media:
            await status.edit(f"❌ **عذراً، الفيديو رقم {display_index} لم يعد متوفراً.**")
            return

        await status.edit(f"🚀 **جاري رفع فيديو رقم {display_index}...**")

        downloaded_file = await user_client.download_media(msg)

        # إرسال الفيديو وحظر الحفظ/التوجيه
        await bot.send_file(
            user_id,
            file=downloaded_file,
            caption=f"🎥 **فيديو رقم {display_index}**\n\n🔒 *محتوى خاص ومحمي من النقل.*",
            protect_content=True
        )
        await status.delete()

    except Exception as e:
        print(f"Error sending video {display_index}: {e}")
        await status.edit("❌ **حدث خطأ أثناء جلب الفيديو. حاول مجدداً.**")

    finally:
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass

async def main():
    await user_client.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ البوت جاهز ومحدث بنظام الصفحات والـ 99+ فيديو بكفاءة!")
    await asyncio.gather(
        bot.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())
