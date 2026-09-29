import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events, Button

# 1. خادم الويب الخاص بـ Render لمنع توقف الخدمة
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

# إنشاء الأزرار بشكل احترافي عند طلب /start
@bot.on(events.NewMessage(pattern=r'^/start$', incoming=True))
async def start_handler(event):
    if not event.is_private:
        return

    # إنشاء شبكة أزرار شفافة (كل سطر محدد بـ 5 أزرار)
    buttons = []
    row = []
    for i in range(1, 16):  # أزرار من 1 إلى 15
        row.append(Button.inline(f"🎬 فيديو {i}", data=f"vid_{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    msg = (
        "✨ **أهلاً بك في البوت الرسمي**\n\n"
        "إليك قائمة الفيديوهات المتاحة، اضغط على الزر المطلوب للاستلام المباشر:"
    )
    await event.respond(msg, buttons=buttons)

# التعامل الحصري مع الأزرار وإلغاء الكتابة النصية
@bot.on(events.CallbackQuery(pattern=r'^vid_(\d+)$'))
async def callback_video_handler(event):
    video_num = int(event.pattern_match.group(1))
    user_id = event.sender_id

    await event.answer("جاري المعالجة...")
    status = await event.respond(f"⏳ **جاري تحضير الفيديو رقم {video_num}...**")

    downloaded_file = None
    try:
        # جلب الرسالة عبر حساب الأدمن من القناة
        msg = await user_client.get_messages(PRIVATE_CHANNEL, ids=video_num)

        if not msg or not msg.media:
            await status.edit(f"❌ **عذراً، الفيديو رقم {video_num} غير متوفر حالياً.**")
            return

        await status.edit(f"🚀 **جاري رفع الفيديو رقم {video_num}...**")

        # التحميل على سيرفر Render
        downloaded_file = await user_client.download_media(msg)

        # إرسال الفيديو للزبون مع حظر التحفيظ والتوجيه
        await bot.send_file(
            user_id,
            file=downloaded_file,
            caption=f"🎥 **فيديو رقم {video_num}**\n\n🔒 *محتوى خاص ومحمي من النقل.*",
            protect_content=True
        )
        await status.delete()

    except Exception as e:
        print(f"Error handling video {video_num}: {e}")
        await status.edit("❌ **حدث خطأ أثناء جلب الفيديو. يرجى المحاولة لاحقاً.**")

    finally:
        # مسح الملف من السيرفر فور الإرسال
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass

async def main():
    await user_client.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ البوت جاهز ويعمل بآلية الأزرار الشفافة الاحترافية!")
    await asyncio.gather(
        bot.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())
