import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import asyncio

# ==================================================
# Flask Keep Alive
# ==================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Broadcast Bot Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==================================================
# إعدادات البوت
# ==================================================

TOKEN = os.getenv("TOKEN")

# ايدي روم البرودكاست
CHANNEL_ID = 1507516304716992654

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ==================================================
# عند تشغيل البوت
# ==================================================

@bot.event
async def on_ready():

    print("===================================")
    print(f"✅ Logged in as {bot.user}")
    print("🚀 Broadcast Bot Ready")
    print("===================================")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Professional Broadcast System"
        )
    )

# ==================================================
# نظام البرودكاست
# ==================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # فقط روم البرودكاست
    if message.channel.id == CHANNEL_ID:

        # تجاهل نعم/لا
        if message.content.lower() in [
            "نعم", "لا",
            "yes", "no",
            "y", "n"
        ]:
            return

        # رسالة التأكيد
        confirm_embed = discord.Embed(
            title="📨 تأكيد البرودكاست",
            description=(
                "هل تريد إرسال هذه الرسالة إلى جميع أعضاء السيرفر؟\n\n"
                "✅ اكتب: نعم\n"
                "❌ اكتب: لا"
            ),
            color=0x5865F2
        )

        confirm_embed.set_footer(
            text="لديك 30 ثانية للرد"
        )

        await message.channel.send(
            content=message.author.mention,
            embed=confirm_embed
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

                # ==================================================
                # موافقة
                # ==================================================

                if reply.content.lower() in [
                    "نعم",
                    "yes",
                    "y"
                ]:

                    loading = await message.channel.send(
                        "⏳ | جاري تجهيز البرودكاست..."
                    )

                    sent = 0
                    failed = 0

                    # تحميل كل الأعضاء
                    await message.guild.chunk()

                    members = message.guild.members

                    total_members = len([
                        m for m in members if not m.bot
                    ])

                    await loading.edit(

                        content=(
                            f"🚀 بدأ الإرسال إلى {total_members} عضو...\n"
                            f"⏳ الرجاء الانتظار"
                        )

                    )

                    for member in members:

                        # تجاهل البوتات
                        if member.bot:
                            continue

                        try:

                            # Embed احترافي
                            embed = discord.Embed(
                                title="📩 رسالة جديدة",
                                description=(
                                    message.content
                                    if message.content
                                    else "بدون نص"
                                ),
                                color=0x2B2D31
                            )

                            embed.add_field(
                                name="📌 السيرفر",
                                value=message.guild.name,
                                inline=False
                            )

                            embed.set_footer(
                                text="Broadcast System"
                            )

                            # صورة السيرفر
                            if message.guild.icon:
                                embed.set_thumbnail(
                                    url=message.guild.icon.url
                                )

                            # إرسال الرسالة
                            await member.send(
                                embed=embed
                            )

                            # إرسال المرفقات
                            for attachment in message.attachments:

                                await member.send(
                                    attachment.url
                                )

                            sent += 1

                            print(
                                f"✅ Sent to: {member}"
                            )

                            # تأخير مهم جدًا ضد الرايت ليمت
                            await asyncio.sleep(1.5)

                        except discord.Forbidden:

                            # الخاص مقفل
                            failed += 1

                            print(
                                f"❌ Closed DM: {member}"
                            )

                        except discord.HTTPException as e:

                            failed += 1

                            print(
                                f"⚠️ HTTP Error -> {member}: {e}"
                            )

                            # انتظار إضافي لو حصل Rate Limit
                            await asyncio.sleep(5)

                        except Exception as e:

                            failed += 1

                            print(
                                f"❌ Unknown Error -> {member}: {e}"
                            )

                    # النتيجة النهائية
                    result_embed = discord.Embed(
                        title="✅ انتهى البرودكاست",
                        color=0x57F287
                    )

                    result_embed.add_field(
                        name="📨 تم الإرسال بنجاح",
                        value=f"{sent}",
                        inline=True
                    )

                    result_embed.add_field(
                        name="❌ فشل الإرسال",
                        value=f"{failed}",
                        inline=True
                    )

                    result_embed.set_footer(
                        text="Broadcast Completed Successfully"
                    )

                    await loading.edit(
                        content=None,
                        embed=result_embed
                    )

                    break

                # ==================================================
                # رفض
                # ==================================================

                elif reply.content.lower() in [
                    "لا",
                    "no",
                    "n"
                ]:

                    cancel_embed = discord.Embed(
                        title="❌ تم إلغاء البرودكاست",
                        description="تم إلغاء عملية الإرسال بنجاح.",
                        color=0xED4245
                    )

                    await message.channel.send(
                        embed=cancel_embed
                    )

                    break

                # ==================================================
                # إدخال خاطئ
                # ==================================================

                else:

                    error_embed = discord.Embed(
                        title="⚠️ إدخال غير صحيح",
                        description="الرجاء كتابة نعم أو لا فقط.",
                        color=0xFEE75C
                    )

                    await message.channel.send(
                        embed=error_embed
                    )

        except asyncio.TimeoutError:

            timeout_embed = discord.Embed(
                title="⌛ انتهى الوقت",
                description="لم يتم الرد خلال 30 ثانية.",
                color=0xED4245
            )

            await message.channel.send(
                embed=timeout_embed
            )

    await bot.process_commands(message)

# ==================================================
# تشغيل البوت
# ==================================================

keep_alive()
bot.run(TOKEN)
