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

# ايدي الروم المخصص للإرسال
CHANNEL_ID = 1507516304716992654

# ايدي الرتبة المستهدفة
ROLE_ID = 1480272598649671730

intents = discord.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ===============================
# عند تشغيل البوت
# ===============================

@bot.event
async def on_ready():

    print("===================================")
    print(f"✅ Logged in as {bot.user}")
    print("🚀 Bot is online and ready")
    print("===================================")

# ===============================
# نظام الإرسال الخاص
# ===============================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # التأكد من الروم المحدد
    if message.channel.id == CHANNEL_ID:

        # تجاهل نعم ولا
        if message.content.lower() in [
            "نعم", "لا",
            "yes", "no",
            "y", "n"
        ]:
            return

        # رسالة التأكيد
        await message.channel.send(
            f"📨 | {message.author.mention}\n\n"
            "هل تريد إرسال هذه الرسالة إلى جميع أعضاء الرتبة المحددة؟\n\n"
            "✅ اكتب: نعم\n"
            "❌ اكتب: لا"
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

                # ===============================
                # الموافقة
                # ===============================

                if reply.content.lower() in [
                    "نعم",
                    "yes",
                    "y"
                ]:

                    role = message.guild.get_role(ROLE_ID)

                    if not role:

                        await message.channel.send(
                            "❌ لم يتم العثور على الرتبة المطلوبة."
                        )
                        return

                    loading = await message.channel.send(
                        "⏳ جاري إرسال الرسائل الخاصة..."
                    )

                    sent = 0
                    failed = 0

                    for member in role.members:

                        # تجاهل البوتات
                        if member.bot:
                            continue

                        try:

                            # إنشاء Embed احترافي
                            embed = discord.Embed(
                                title="📩 رسالة جديدة",
                                description=message.content if message.content else "بدون نص",
                                color=0x2F3136
                            )

                            embed.set_footer(
                                text=f"مرسلة من سيرفر: {message.guild.name}"
                            )

                            # إرسال النص
                            await member.send(embed=embed)

                            # إرسال المرفقات
                            for attachment in message.attachments:

                                await member.send(
                                    attachment.url
                                )

                            sent += 1

                            # تأخير لتجنب Rate Limit
                            await asyncio.sleep(1)

                        except:

                            failed += 1

                    # تعديل رسالة التحميل
                    await loading.edit(

                        content=(
                            "✅ انتهى الإرسال بنجاح\n\n"
                            f"📨 تم الإرسال إلى: {sent} عضو\n"
                            f"❌ فشل الإرسال إلى: {failed} عضو"
                        )

                    )

                    break

                # ===============================
                # الرفض
                # ===============================

                elif reply.content.lower() in [
                    "لا",
                    "no",
                    "n"
                ]:

                    await message.channel.send(
                        "❌ تم إلغاء عملية الإرسال."
                    )

                    break

                # ===============================
                # إدخال خاطئ
                # ===============================

                else:

                    await message.channel.send(
                        "⚠️ الرجاء كتابة نعم أو لا فقط."
                    )

        except asyncio.TimeoutError:

            await message.channel.send(
                "⌛ انتهى وقت التأكيد."
            )

    await bot.process_commands(message)

# ===============================
# تشغيل البوت
# ===============================

keep_alive()

bot.run(TOKEN)
