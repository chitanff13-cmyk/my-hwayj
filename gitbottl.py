import os
import asyncio
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events, Button

# 1. خادم الويب الخاص بـ Render
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
ADMIN_ID = 8675469992  # آيدي حسابك الأدمن
VIDEOS_PER_PAGE = 9

# ==================== قسم نصوص الرسائل (عدّلها كما تحب) ====================
WELCOME_MSG = (
    "🔒 **مرحبا بيك عينيا  MAHALI DZ الخاص بنا**\n\n"
    "عذراً، هذا البوت مدفوع ولا يمكن استخدامه إلا عبر كود تفعيل.\n"
    "يرجى إرسال **كود التفعيل** الخاص بك هنا للبدء 👇"
)

MAIN_MENU_MSG = (
    "✨ **أهلاً بك مجدداً في  MAHALI DZ**\n\n"
    "📊 **إجمالي الفيديوهات الحصرية المتاحة:** `{total_videos}` فيديو\n"
    "اختر الفيديو المطلوب من الأزرار أدناه للاستلام المباشر:"
)

VIDEO_CAPTION = "🎥 **فيديو رقم {display_index}**\n\n🔒 *محتوى خاص ومحمي من الحفظ والنقل.*"
# =========================================================================

USERS_FILE = 'active_users.json'
CODES_FILE = 'vip_codes.json'

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

active_users = load_json(USERS_FILE)
valid_codes = load_json(CODES_FILE)

bot = TelegramClient('bot_session', API_ID, API_HASH)
user_client = TelegramClient('uploader_session', API_ID, API_HASH)

async def get_channel_videos():
    video_messages = []
    async for message in user_client.iter_messages(PRIVATE_CHANNEL, reverse=True):
        if message.video or message.document or (message.media and getattr(message.media, 'document', None)):
            if message.file and message.file.mime_type and message.file.mime_type.startswith('video/'):
                video_messages.append(message.id)
    return video_messages

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

    nav_row = []
    if page > 1:
        nav_row.append(Button.inline("◀ السابق", data=f"page_{page - 1}"))
    nav_row.append(Button.inline(f"📄 {page}/{total_pages}", data="ignore"))
    if page < total_pages:
        nav_row.append(Button.inline("التالي ▶", data=f"page_{page + 1}"))

    buttons.append(nav_row)
    return buttons, total_videos, total_pages

@bot.on(events.NewMessage(pattern=r'^/start$', incoming=True))
async def start_handler(event):
    if not event.is_private:
        return

    user_id = str(event.sender_id)

    if user_id not in active_users and event.sender_id != ADMIN_ID:
        await event.respond(WELCOME_MSG)
        return

    status = await event.respond("⏳ **جاري فحص القناة وتنظيم قائمة الفيديوهات...**")
    try:
        video_ids = await get_channel_videos()
        if not video_ids:
            await status.edit("❌ **لا توجد أي فيديوهات متوفرة في القناة حالياً.**")
            return

        buttons, total_videos, total_pages = build_page_keyboard(video_ids, page=1)
        msg = MAIN_MENU_MSG.format(total_videos=total_videos)
        await status.edit(msg, buttons=buttons)
    except Exception as e:
        print(f"Error starting: {e}")
        await status.edit("❌ **حدث خطأ أثناء تحميل الفيديوهات.**")

@bot.on(events.NewMessage(incoming=True))
async def handle_all_messages(event):
    if not event.is_private or event.text.startswith('/start'):
        return

    text = event.text.strip()
    user_id = str(event.sender_id)

    # إضافة كود جديد للزبائن من قبل الأدمن
    if event.sender_id == ADMIN_ID and text.lower().replace('/', '').startswith('addcode'):
        parts = text.split()
        if len(parts) >= 2:
            code = parts[1].strip()
            valid_codes[code] = 1
            save_json(CODES_FILE, valid_codes)
            await event.respond(f"✅ **تم إنشاء كود التفعيل بنجاح:**\n`{code}`")
        else:
            await event.respond("❌ **يرجى كتابة الكود بعد الأمر، مثال:**\n`/addcode client123`")
        return

    # للزبائن: التحقق من كود التفعيل
    if user_id in active_users or event.sender_id == ADMIN_ID:
        return

    if text in valid_codes and valid_codes[text] > 0:
        active_users[user_id] = True
        valid_codes[text] -= 1
        if valid_codes[text] <= 0:
            del valid_codes[text]

        save_json(USERS_FILE, active_users)
        save_json(CODES_FILE, valid_codes)

        await event.respond("✅ **تم تفعيل اشتراكك بنجاح! أرسل الآن /start للبدء.**")
    else:
        await event.respond("❌ **كود التفعيل غير صحيح أو تم استخدامه من قبل.**")

@bot.on(events.CallbackQuery(pattern=r'^page_(\d+)$'))
async def page_handler(event):
    user_id = str(event.sender_id)
    if user_id not in active_users and event.sender_id != ADMIN_ID:
        await event.answer("❌ غير مسموح لك بالوصول.", alert=True)
        return

    page = int(event.pattern_match.group(1))
    await event.answer()

    try:
        video_ids = await get_channel_videos()
        buttons, total_videos, total_pages = build_page_keyboard(video_ids, page=page)
        msg = MAIN_MENU_MSG.format(total_videos=total_videos)
        await event.edit(msg, buttons=buttons)
    except Exception as e:
        print(f"Error page navigation: {e}")

@bot.on(events.CallbackQuery(pattern=r'^getmsg_(\d+)_(\d+)$'))
async def callback_video_handler(event):
    user_id = str(event.sender_id)
    if user_id not in active_users and event.sender_id != ADMIN_ID:
        await event.answer("❌ غير مسموح لك بالوصول.", alert=True)
        return

    msg_id = int(event.pattern_match.group(1))
    display_index = int(event.pattern_match.group(2))

    await event.answer("جاري التحميل...")
    status = await event.respond(f"⏳ **جاري تحضير فيديو رقم {display_index}...**")

    downloaded_file = None
    try:
        msg = await user_client.get_messages(PRIVATE_CHANNEL, ids=msg_id)
        if not msg or not msg.media:
            await status.edit(f"❌ **الفيديو رقم {display_index} غير متوفر.**")
            return

        await status.edit(f"🚀 **جاري رفع فيديو رقم {display_index}...**")
        downloaded_file = await user_client.download_media(msg)

        caption_text = VIDEO_CAPTION.format(display_index=display_index)
        await bot.send_file(
            event.sender_id,
            file=downloaded_file,
            caption=caption_text,
            protect_content=True
        )
        await status.delete()

    except Exception as e:
        print(f"Error sending video: {e}")
        await status.edit("❌ **حدث خطأ أثناء جلب الفيديو.**")

    finally:
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass

async def main():
    await user_client.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ البوت يعمل بنجاح ويمكن تعديل رسائله بسهولة!")
    await asyncio.gather(
        bot.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())
