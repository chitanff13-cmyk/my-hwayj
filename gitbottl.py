import asyncio
from telethon import TelegramClient, events

# ==================== الإعدادات ====================
API_ID = 31726034
API_HASH = '9d0b6b8cfdda846f5dbf8543fd6f7e9e'
BOT_TOKEN = '8716514427:AAHSvYDqyThe-pTSVis8qavNc05H-Pi5EE0' # احصل عليه من @BotFather

# أيدي القناة التي تحتوي على الفيديوهات
SOURCE_CHANNEL = -1004273448312  # استبدله بأيدي قناتك إذا كان مختلفاً

# عدد ثواني الانتظار قبل إرسال الفيديو للزبون
WAIT_TIME_SECONDS = 5
# ===================================================

# عميل البوت للاستجابة للزبائن
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# عميل الحساب الشخصي (الأدمن) لسحب الملفات من القناة
user_client = TelegramClient('uploader_session', API_ID, API_HASH)

@bot.on(events.NewMessage(pattern=r'^/start$'))
async def start_handler(event):
    welcome_msg = (
        "مرحباً بك! 👋\n\n"
        "للحصول على أي فيديو، قم بإرسال **رقم الفيديو** فقط (مثال: `1` أو `15` أو `50`)."
    )
    await event.respond(welcome_msg)

@bot.on(events.NewMessage)
async def video_request_handler(event):
    text = event.text.strip()
    
    # تجاهل أمر /start
    if text == "/start":
        return

    # التحقق من أن المكتوب هو رقم فيديو
    if not text.isdigit():
        await event.respond("⚠️ يرجى إرسال رقم الفيديو فقط (مثال: 5).")
        return

    msg_id = int(text)
    user_id = event.sender_id

    # 1. إرسال رسالة التمهيد مع العداد
    status_msg = await event.respond(f"⏳ جاري تجهيز الفيديو رقم **{msg_id}**... يرجى الانتظار {WAIT_TIME_SECONDS} ثوانٍ.")

    try:
        # 2. الانتظار لمدة 5 ثوانٍ
        await asyncio.sleep(WAIT_TIME_SECONDS)

        # 3. جلب الرسالة/الفيديو من القناة بواسطة حساب الأدمن
        message = await user_client.get_messages(SOURCE_CHANNEL, ids=msg_id)

        if not message or not message.media:
            await status_msg.edit("✕ لم يتم العثور على فيديو بهذا الرقم!")
            return

        # 4. إرسال الفيديو للزبون مع تفعيل حماية منع الحفظ والتوجيه
        await bot.send_file(
            user_id,
            file=message.media,
            caption=f"🎥 **فيديو رقم {msg_id}**\n\n🔒 هذا المحتوى محمي وخاص بك فقط.",
            protect_content=True, # منع التحميل، التوجيه، والتسجيل
            has_spoiler=True       # إخفاء المعاينة بالضباب
        )

        # 5. حذف رسالة الانتظار بعد إرسال الفيديو بنجاح
        await status_msg.delete()

    except Exception as e:
        print(f"خطأ أثناء جلب الفيديو: {e}")
        await status_msg.edit("✕ حدث خطأ أثناء إرسال الفيديو. تأكد من الرقم وصلاحيات الأدمن.")

async def main():
    await user_client.start()
    print("🤖 بوت التوزيع الحصري شغال وجاهز لاستقبال الطلبات مع مؤقت الانتظار!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())