python
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import re
from datetime import timedelta

# =========================
# إعدادات البوت
# =========================

TOKEN = "حط_توكن_البوت"

GUILD_ID = 000000000000000000

# روم مراقبة الروابط
LINK_ROOM_ID = 1487001594300989461

# روم الانذارات
WARN_ROOM_ID = 1479608600350429194

# روم التكتات
TICKET_CHANNEL_ID = 000000000000000000

# رتبة الادارة الي تشوف التكتات
STAFF_ROLE_ID = 000000000000000000

# ايدي الشخص الي تبيه يتمنشن داخل التكت
OWNER_ID = 1354946253623922738

# =========================
# تشغيل البوت
# =========================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

tree = bot.tree

# =========================
# كشف روابط الدسكورد
# =========================

discord_link_regex = r"(discord\.gg\/|discord\.com\/invite\/)"

# =========================
# رسالة الانذار
# =========================

async def send_warning(member, duration_text):

    channel = bot.get_channel(WARN_ROOM_ID)

    embed = discord.Embed(
        title="🚨 تـنـبـيـه إداري",
        description=(
            f"### العضو المخالف:\n"
            f"{member.mention}\n\n"
            f"### نوع المخالفة:\n"
            f"رابط دسكورد\n\n"
            f"### المدة:\n"
            f"{duration_text}\n\n"
            f"|| <@{OWNER_ID}> ||\n"
            f"سبب التايم اوت ارسال رابط"
        ),
        color=discord.Color.red()
    )

    embed.set_thumbnail(
        url=member.guild.icon.url if member.guild.icon else None
    )

    embed.set_footer(text="نظام الانذارات")

    await channel.send(embed=embed)

# =========================
# مراقبة الرسائل
# =========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id == LINK_ROOM_ID:

        if re.search(discord_link_regex, message.content):

            try:

                timeout_duration = timedelta(days=7)

                await message.author.timeout(
                    timeout_duration,
                    reason="ارسال رابط دسكورد"
                )

                await send_warning(
                    message.author,
                    "اسبوع"
                )

                await message.reply(
                    "تم اعطائك تايم اوت بسبب ارسال رابط دسكورد"
                )

            except Exception as e:
                print(e)

    await bot.process_commands(message)

# =========================
# رسالة الباند
# =========================

class TicketView(View):

    def __init__(self, banned_user_id):
        super().__init__(timeout=None)

        self.banned_user_id = banned_user_id

    @discord.ui.button(
        label="فتح تكت",
        style=discord.ButtonStyle.green
    )
    async def open_ticket(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        guild = bot.get_guild(GUILD_ID)

        existing = discord.utils.get(
            guild.text_channels,
            name=f"ban-ticket-{interaction.user.id}"
        )

        if existing:
            await interaction.response.send_message(
                "عندك تكت مفتوح بالفعل",
                ephemeral=True
            )
            return

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

        category = bot.get_channel(TICKET_CHANNEL_ID)

        ticket_channel = await guild.create_text_channel(
            name=f"ban-ticket-{interaction.user.id}",
            overwrites=overwrites,
            category=category
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
            f"تم فتح التكت: {ticket_channel.mention}",
            ephemeral=True
        )

    @discord.ui.button(
        label="رفض فك الباند",
        style=discord.ButtonStyle.red
    )
    async def deny_unban(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        await interaction.response.send_message(
            "تم رفض طلب فك الباند",
            ephemeral=True
        )

# =========================
# عند الباند
# =========================

@bot.event
async def on_member_ban(guild, user):

    try:

        embed = discord.Embed(
            title="🚫 تم تبنيدك",
            description=(
                "اذا حاب تفك الباند اضغط الزر تحت"
            ),
            color=discord.Color.red()
        )

        await user.send(
            embed=embed,
            view=TicketView(user.id)
        )

    except:
        pass

# =========================
# نسخ الرسائل داخل التكت
# =========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.name.startswith("ban-ticket-"):

        await message.channel.send(
            f"<@{OWNER_ID}> الرسالة الجديدة من {message.author.mention}"
        )

    # فحص روابط الدسكورد
    if message.channel.id == LINK_ROOM_ID:

        if re.search(discord_link_regex, message.content):

            try:

                timeout_duration = timedelta(days=7)

                await message.author.timeout(
                    timeout_duration,
                    reason="ارسال رابط دسكورد"
                )

                await send_warning(
                    message.author,
                    "اسبوع"
                )

                await message.reply(
                    "تم اعطائك تايم اوت بسبب ارسال رابط دسكورد"
                )

            except Exception as e:
                print(e)

    await bot.process_commands(message)

# =========================
# امر اغلاق التكت
# =========================

@bot.command()
@commands.has_permissions(administrator=True)
async def close(ctx):

    if ctx.channel.name.startswith("ban-ticket-"):

        await ctx.send("تم اغلاق التكت")

        await ctx.channel.delete()

# =========================
# تشغيل البوت
# =========================

@bot.event
async def on_ready():

    print(f"تم تشغيل البوت | {bot.user}")

    try:
        synced = await tree.sync()
        print(f"تم مزامنة {len(synced)} امر")
    except Exception as e:
        print(e)

bot.run(TOKEN)

