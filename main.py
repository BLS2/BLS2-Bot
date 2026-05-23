import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import asyncio

# =========================================
# Flask Keep Alive
# =========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running successfully"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web).start()

# =========================================
# إعدادات البوت
# =========================================

TOKEN = os.getenv("TOKEN")

# روم الإرسال
CHANNEL_ID = 1507516304716992654

intents = discord.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================================
# تشغيل البوت
# =========================================

@bot.event
async def on_ready():

    print("======================================")
    print(f"✅ Logged in as: {bot.user}")
    print("🚀 DM Broadcast Bot is Online")
    print("======================================")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Sending Professional Broadcasts"
        )
    )

# =========================================
# نظام البرودكاست
# =========================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # التأكد من الروم المحدد
    if message.channel.id == CHANNEL_ID:

        # تجاهل رسائل التأكيد
        if message.content.lower() in [
            "نعم", "لا",
            "yes", "no",
            "y", "n"
        ]:
            return

        # رسالة التأكيد
        confirm_embed = discord.Embed(
            title="📨 تأكيد عملية الإرسال",
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
            content=f"{message.author.mention}",
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

                # =========================================
                # الموافقة
                # =========================================

                if reply.content.lower() in [
                    "نعم",
                    "yes",
                    "y"
                ]:

                    loading = await message.channel.send(
                        "⏳ | جاري إرسال الرسائل الخاصة لجميع الأعضاء..."
                    )

                    sent = 0
                    failed = 0

                    # جميع أعضاء السيرفر
                    members = message.guild.members

                    for member in members:

                        # تجاهل البوتات
                        if member.bot:
                            continue

                        try:

                            # إنشاء Embed احترافي
                            embed = discord.Embed(
                                title="📩 رسالة جديدة",
                                description=(
                                    message.content
                                    if message.content
                                    else "بدون محتوى نصي"
                                ),
                                color=0x2B2D31
                            )

                            embed.add_field(
                                name="📌 السيرفر",
                                value=message.guild.name,
                                inline=False
                            )

                            embed.set_thumbnail(
                                url=message.guild.icon.url
                                if message.guild.icon
                                else discord.Embed.Empty
                            )

                            embed.set_footer(
                                text="تم الإرسال عبر نظام البرودكاست"
                            )

                            # إرسال الرسالة
                            await member.send(embed=embed)

                            # إرسال المرفقات
                            for attachment in message.attachments:

                                await member.send(
                                    attachment.url
                                )

                            sent += 1

                            # تأخير بسيط لتجنب Rate Limit
                            await asyncio.sleep(0.8)

                        except discord.Forbidden:

                            # الخاص مقفل
                            failed += 1

                        except Exception as e:

                            print(f"Error sending to {member}: {e}")
                            failed += 1

                    # النتيجة النهائية
                    done_embed = discord.Embed(
                        title="✅ اكتملت عملية الإرسال",
                        color=0x57F287
                    )

                    done_embed.add_field(
                        name="📨 تم الإرسال إلى",
                        value=f"{sent} عضو",
                        inline=True
                    )

                    done_embed.add_field(
                        name="❌ فشل الإرسال إلى",
                        value=f"{failed} عضو",
                        inline=True
                    )

                    done_embed.set_footer(
                        text="Broadcast System Finished Successfully"
                    )

                    await loading.edit(
                        content=None,
                        embed=done_embed
                    )

                    break

                # =========================================
                # الرفض
                # =========================================

                elif reply.content.lower() in [
                    "لا",
                    "no",
                    "n"
                ]:

                    cancel_embed = discord.Embed(
                        title="❌ تم إلغاء العملية",
                        description="تم إلغاء إرسال البرودكاست بنجاح.",
                        color=0xED4245
                    )

                    await message.channel.send(
                        embed=cancel_embed
                    )

                    break

                # =========================================
                # إدخال خاطئ
                # =========================================

                else:

                    warn_embed = discord.Embed(
                        title="⚠️ إدخال غير صحيح",
                        description="الرجاء كتابة نعم أو لا فقط.",
                        color=0xFEE75C
                    )

                    await message.channel.send(
                        embed=warn_embed
                    )

        except asyncio.TimeoutError:

            timeout_embed = discord.Embed(
                title="⌛ انتهى الوقت",
                description="لم يتم استلام رد خلال 30 ثانية.",
                color=0xED4245
            )

            await message.channel.send(
                embed=timeout_embed
            )

    await bot.process_commands(message)

# =========================================
# تشغيل البوت
# =========================================

keep_alive()
bot.run(TOKEN)
