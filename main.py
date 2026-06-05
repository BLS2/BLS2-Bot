import datetime
import io
import os
from threading import Thread

import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View
from flask import Flask


# =====================================
# Flask keep-alive
# =====================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Review Bot Online"


def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


def keep_alive():
    Thread(target=run_web, daemon=True).start()


# =====================================
# Settings
# =====================================

TOKEN = os.getenv("TOKEN")

REVIEW_CHANNEL_ID = 1481443704383340585
BROADCAST_CHANNEL_ID = int(os.getenv("BROADCAST_CHANNEL_ID", REVIEW_CHANNEL_ID))

REVIEW_ROLE_ID = 1507511064399577098

PANEL_TITLE = "⭐ تقييم العملاء"
PANEL_DESCRIPTION = "اضغط الزر لتقييم المنتج والخدمة"

review_panel_message_id = None


# =====================================
# Bot
# =====================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)


# =====================================
# Helpers
# =====================================

def stars(amount: int) -> str:
    return "⭐" * amount + "☆" * (10 - amount)


def build_panel_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=PANEL_TITLE,
        description=PANEL_DESCRIPTION,
        color=0xFFD700,
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=f"{guild.name} • Reviews System")
    return embed


async def send_review_panel(channel: discord.TextChannel) -> discord.Message:
    global review_panel_message_id

    if review_panel_message_id:
        try:
            old_panel = await channel.fetch_message(review_panel_message_id)
            await old_panel.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    message = await channel.send(embed=build_panel_embed(channel.guild), view=ReviewView())
    review_panel_message_id = message.id
    return message


async def read_attachments(message: discord.Message) -> list[tuple[str, bytes]]:
    files = []

    for attachment in message.attachments:
        try:
            files.append((attachment.filename, await attachment.read()))
        except discord.HTTPException:
            continue

    return files


def make_files(files_data: list[tuple[str, bytes]]) -> list[discord.File]:
    return [
        discord.File(io.BytesIO(file_bytes), filename=file_name)
        for file_name, file_bytes in files_data
    ]


# =====================================
# Review modal
# =====================================

class ReviewModal(Modal, title="تقييم المنتج والخدمة"):
    product = TextInput(
        label="تقييم المنتج من 1 إلى 10",
        placeholder="مثال: 10",
        required=True,
        max_length=2,
    )

    service = TextInput(
        label="تقييم الخدمة من 1 إلى 10",
        placeholder="مثال: 10",
        required=True,
        max_length=2,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            product_score = int(self.product.value)
            service_score = int(self.service.value)
        except ValueError:
            return await interaction.response.send_message(
                "❌ يجب إدخال أرقام فقط.",
                ephemeral=True,
            )

        if not 1 <= product_score <= 10:
            return await interaction.response.send_message(
                "❌ تقييم المنتج يجب أن يكون بين 1 و 10.",
                ephemeral=True,
            )

        if not 1 <= service_score <= 10:
            return await interaction.response.send_message(
                "❌ تقييم الخدمة يجب أن يكون بين 1 و 10.",
                ephemeral=True,
            )

        average = round((product_score + service_score) / 2, 1)
        channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)

        review_role = discord.utils.get(interaction.user.roles, id=REVIEW_ROLE_ID)
        role_name = review_role.mention if review_role else "لا يوجد"

        embed = discord.Embed(
            title="🌟 تقييم جديد",
            color=0xFFD700,
            timestamp=datetime.datetime.now(datetime.UTC),
        )

        embed.add_field(name="👤 العميل", value=interaction.user.mention, inline=False)
        embed.add_field(name="🏪 رتبة المتجر", value=role_name, inline=False)
        embed.add_field(
            name="📦 تقييم المنتج",
            value=f"{stars(product_score)}\n**{product_score}/10**",
            inline=False,
        )
        embed.add_field(
            name="💎 تقييم الخدمة",
            value=f"{stars(service_score)}\n**{service_score}/10**",
            inline=False,
        )
        embed.add_field(name="🏆 التقييم النهائي", value=f"**{average}/10**", inline=False)

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"{interaction.guild.name} • Reviews System")

        if channel:
            await channel.send(
                content=f"📢 تقييم جديد من {interaction.user.mention}",
                embed=embed,
            )
            await send_review_panel(channel)

        await interaction.response.send_message(
            "✅ تم إرسال تقييمك بنجاح.",
            ephemeral=True,
        )


# =====================================
# Review view
# =====================================

class ReviewView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="تقييم المنتج والخدمة",
        emoji="⭐",
        style=discord.ButtonStyle.success,
        custom_id="review_button",
    )
    async def review_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel_id != REVIEW_CHANNEL_ID:
            return await interaction.response.send_message(
                "❌ التقييم متاح فقط في روم التقييمات.",
                ephemeral=True,
            )

        if not any(role.id == REVIEW_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ لا تملك صلاحية التقييم.",
                ephemeral=True,
            )

        await interaction.response.send_modal(ReviewModal())


# =====================================
# Broadcast confirmation
# =====================================

class BroadcastConfirmView(View):
    def __init__(self, message: discord.Message, files_data: list[tuple[str, bytes]]):
        super().__init__(timeout=60)
        self.message = message
        self.files_data = files_data

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.message.author.id:
            await interaction.response.send_message(
                "❌ هذا التأكيد خاص بصاحب الرسالة فقط.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="نعم، أرسل", emoji="✅", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        sent_count = 0
        failed_count = 0
        content = self.message.content or None

        for member in self.message.guild.members:
            if member.bot:
                continue

            try:
                await member.send(content=content, files=make_files(self.files_data))
                sent_count += 1
            except discord.HTTPException:
                failed_count += 1

        self.disable_all_items()
        await interaction.message.edit(
            content=f"✅ تم الإرسال الخاص.\nنجح: **{sent_count}**\nفشل: **{failed_count}**",
            view=self,
        )
        await interaction.followup.send("✅ انتهى الإرسال.", ephemeral=True)

    @discord.ui.button(label="لا، إلغاء", emoji="❌", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all_items()
        await interaction.response.edit_message(content="تم إلغاء الإرسال الخاص.", view=self)

    async def on_timeout(self):
        self.disable_all_items()

        try:
            await self.message.channel.send("انتهى وقت تأكيد الإرسال الخاص.")
        except discord.HTTPException:
            pass


# =====================================
# Commands
# =====================================

@bot.command(name="تقييم", aliases=["تقيم", "reviewpanel"])
@commands.has_permissions(administrator=True)
async def review_panel(ctx: commands.Context):
    if ctx.channel.id != REVIEW_CHANNEL_ID:
        return await ctx.reply(
            f"❌ هذا الأمر يعمل فقط في روم <#{REVIEW_CHANNEL_ID}>.",
            mention_author=False,
        )

    await send_review_panel(ctx.channel)

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass


@review_panel.error
async def review_panel_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ هذا الأمر للإدارة فقط.", mention_author=False)


# =====================================
# Events
# =====================================

@bot.event
async def on_ready():
    bot.add_view(ReviewView())
    print(f"✅ Logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    if message.channel.id != BROADCAST_CHANNEL_ID:
        return

    if not message.author.guild_permissions.administrator:
        return

    if not message.content and not message.attachments:
        return

    files_data = await read_attachments(message)
    view = BroadcastConfirmView(message, files_data)

    await message.reply(
        "هل تريد إرسال هذه الرسالة في الخاص لكل أعضاء السيرفر؟",
        mention_author=False,
        view=view,
    )


# =====================================
# Run
# =====================================

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is missing.")

keep_alive()
bot.run(TOKEN)
