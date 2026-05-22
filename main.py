import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import asyncio

# ===============================
# Flask (تشغيل البوت 24/7)
# ===============================

app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web).start()

# ===============================
# إعدادات البوت
# ===============================

TOKEN = os.getenv("TOKEN")

# ايدي الروم
CHANNEL_ID = 1507516304716992654

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ===============================
# عند تشغيل البوت
# ===============================

@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")

# ===============================
# نظام الإرسال الخاص
# ===============================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # يتأكد ان الرسالة من الروم المحدد
    if message.channel.id == CHANNEL_ID:

        # يمنع الرد على نعم او لا
        if message.content.lower() in ["نعم", "لا", "yes", "no", "y", "n"]:
            return

        # رسالة التأكيد
        await message.channel.send(
            f"{message.author.mention}\n"
            "هل أنت متأكد من إرسال هذه الرسالة لجميع أعضاء السيرفر؟\n\n"
            "اكتب: نعم\n"
            "أو اكتب: لا"
        )

        def check(m):

            return (
                m.author == message.author
                and m.channel == message.channel
            )

        try:

            while True:

                reply = await bot.wait_for(
                    "message",
                    timeout=30,
                    check=check
                )

                # موافقة
                if reply.content.lower() in ["نعم", "yes", "y"]:

                    sent = 0
                    failed = 0

                    loading = await message.channel.send(
                        "📨 جاري إرسال الرسائل الخاصة..."
                    )

                    for member in message.guild.members:

                        # يتخطى البوتات
                        if member.bot:
                            continue

                        try:

                            await member.send(message.content)
                            sent += 1

                            # تأخير بسيط
                            await asyncio.sleep(1)

                        except:

                            failed += 1

                    await loading.edit(

                        content=(
                            f"✅ تم إرسال الرسالة لـ {sent} عضو\n"
                            f"❌ فشل الإرسال لـ {failed} عضو"
                        )

                    )

                    break

                # رفض
                elif reply.content.lower() in ["لا", "no", "n"]:

                    await message.channel.send(
                        "❌ تم إلغاء الإرسال"
                    )

                    break

                # اذا كتب شيء غلط
                else:

                    await message.channel.send(
                        "❌ اكتب فقط نعم أو لا"
                    )

        except asyncio.TimeoutError:

            await message.channel.send(
                "⌛ انتهى وقت التأكيد"
            )

    await bot.process_commands(message)

# ===============================
# تشغيل البوت
# ===============================

keep_alive()

bot.run(TOKEN)
