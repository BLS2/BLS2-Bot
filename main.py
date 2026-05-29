import discord
from discord.ext import commands
from discord.ui import View, Button
from flask import Flask
from threading import Thread
from datetime import timedelta
import os
import re

# ==========================================
# إعدادات البوت
# ==========================================

TOKEN = os.getenv("TOKEN")

# ايدي السيرفر
GUILD_ID = 000000000000000000

# روم مراقبة الروابط
LINK_ROOM_ID = 1487001594300989461

# روم الانذارات
WARN_ROOM_ID = 1479608600350429194

# كاتقوري التكتات
TICKET_CATEGORY_ID = 1487848330804330699

# رتبة الادارة
STAFF_ROLE_ID = 000000000000000000

# ايدي الشخص الي ينمنشن
OWNER_ID = 1354946253623922738

# ==========================================
# تشغيل Flask
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==========================================
# إعدادات البوت
# ==========================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ==========================================
# كشف روابط الدسكورد
# ==========================================

discord_link_regex = r"(discord\.gg\/|discord\.com\/invite\/|discordapp\.com\/invite\/)"

# ==========================================
# المحظورين من فتح التكت
# ==========================================

blacklisted_users = set()

# ==========================================
# إرسال الانذار
# ==========================================

async def send_warning(member, duration_text):

    channel = bot.get_channel(WARN_ROOM_ID)

    embed = discord.Embed(
        title="🚨 تـنـبـيـه إداري",
        color=discord.Color.red()
    )

    embed.description = (
        f"﷽\n\n"
        f"**العضو المخالف:**\n"
        f"{member.mention}\n\n"
        f"**نوع المخالفة:**\n"
        f"رابط دسكورد\n\n"
        f"**المدة:**\n"
        f"{duration_text}\n\n"
        f"|| <@{OWNER_ID}> ||\n"
        f"سبب التايم اوت ارسال رابط"
    )

    if member.guild.icon:
        embed.set_thumbnail(url=member.guild.icon.url)

    embed.set_footer(text="نظام الانذارات")

    await channel.send(embed=embed)

# ==========================================
# أزرار التكت
# ==========================================

class TicketView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="فتح تكت",
        style=discord.ButtonStyle.green,
        custom_id="open_ticket"
    )
    async def open_ticket(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if interaction.user.id in blacklisted_users:

            await interaction.response.send_message(
                "تم رفض طلب فك الباند مسبقا",
                ephemeral=True
            )
            return

        guild = interaction.guild

        existing_ticket = discord.utils.get(
            guild.text_channels,
            name=f"ban-ticket-{interaction.user.id}"
        )

        if existing_ticket:

            await interaction.response.send_message(
                "عندك تكت مفتوح بالفعل",
                ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)

        staff_role = guild.get_role(STAFF_ROLE_ID)

        overwrites = {

            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ban-ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📩 تكت فك باند",
            description=(
                f"{interaction.user.mention}\n\n"
                f"الان اي رسالة ترسلها هنا الادارة بتشوفها"
            ),
            color=discord.Color.red()
        )

        await ticket_channel.send(
            content=f"<@&{STAFF_ROLE_ID}>",
            embed=embed
        )

        await interaction.response.send_message(
            f"تم فتح التكت {ticket_channel.mention}",
            ephemeral=True
        )

    @discord.ui.button(
        label="رفض فك الباند",
        style=discord.ButtonStyle.red,
        custom_id="deny_unban"
    )
    async def deny_unban(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        blacklisted_users.add(interaction.user.id)

        await interaction.response.send_message(
            "تم رفض طلب فك الباند",
            ephemeral=True
        )

# ==========================================
# عند تشغيل البوت
# ==========================================

@bot.event
async def on_ready():

    print(f"تم تشغيل البوت | {bot.user}")

    bot.add_view(TicketView())

# ==========================================
# عند الباند
# ==========================================

@bot.event
async def on_member_ban(guild, user):

    try:

        embed = discord.Embed(
            title="🚫 تم تبنيدك",
            description="اذا حاب تفك الباند اضغط الزر تحت",
            color=discord.Color.red()
        )

        view = TicketView()

        await user.send(
            embed=embed,
            view=view
        )

    except:
        pass

# ==========================================
# مراقبة الرسائل
# ==========================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # ======================================
    # نقل رسائل التكت
    # ======================================

    if message.channel.name.startswith("ban-ticket-"):

        await message.channel.send(
            f"<@{OWNER_ID}> رسالة جديدة من {message.author.mention}"
        )

    # ======================================
    # كشف روابط الدسكورد
    # ======================================

    if message.channel.id == LINK_ROOM_ID:

        if message.author.guild_permissions.administrator:
            return

        if re.search(discord_link_regex, message.content):

            try:

                await message.delete()

                timeout_duration = timedelta(days=7)

                await message.author.timeout(
                    timeout_duration,
                    reason="ارسال رابط دسكورد"
                )

                await send_warning(
                    message.author,
                    "اسبوع"
                )

                await message.channel.send(
                    f"{message.author.mention} تم اعطائك تايم اوت بسبب ارسال رابط"
                )

            except Exception as e:
                print(e)

    await bot.process_commands(message)

# ==========================================
# اغلاق التكت
# ==========================================

@bot.command()
@commands.has_permissions(administrator=True)
async def close(ctx):

    if ctx.channel.name.startswith("ban-ticket-"):

        await ctx.send("تم اغلاق التكت")

        await ctx.channel.delete()

# ==========================================
# تشغيل البوت
# ==========================================

keep_alive()

bot.run(TOKEN)

