import datetime
import os
from threading import Thread

import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View
from flask import Flask


# =====================================
# Keep alive
# =====================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Professional Review Bot Online"


def run_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))


def keep_alive():
    Thread(target=run_web, daemon=True).start()


# =====================================
# Settings
# =====================================

TOKEN = os.getenv("TOKEN")

# روم التقييم فقط
REVIEW_CHANNEL_ID = 1481443704383340585

# الرتبة المسموح لها بالتقييم
REVIEW_ROLE_ID = 1507511064399577098

REVIEW_PANEL_TITLE = "⭐ تقييم العملاء"
REVIEW_PANEL_DESCRIPTION = "اضغط الزر لتقييم المنتج والخدمة"

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

def stars(score: int) -> str:
    return "⭐" * score + "☆" * (10 - score)


def build_review_panel_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=REVIEW_PANEL_TITLE,
        description=REVIEW_PANEL_DESCRIPTION,
        color=0xFFD700,
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=f"{guild.name} • Reviews System")
    return embed


def disable_view_items(view: View) -> None:
    for item in view.children:
        item.disabled = True


async def send_review_panel(channel: discord.TextChannel) -> discord.Message:
    global review_panel_message_id

    if review_panel_message_id:
        try:
            old_message = await channel.fetch_message(review_panel_message_id)
            await old_message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    message = await channel.send(
        embed=build_review_panel_embed(channel.guild),
        view=ReviewView(),
    )
    review_panel_message_id = message.id
    return message


# =====================================
# Review system
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

        review_channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        if not review_channel:
            return await interaction.response.send_message(
                "❌ لم أستطع العثور على روم التقييمات.",
                ephemeral=True,
            )

        average = round((product_score + service_score) / 2, 1)
        review_role = discord.utils.get(interaction.user.roles, id=REVIEW_ROLE_ID)
        role_text = review_role.mention if review_role else "لا يوجد"

        embed = discord.Embed(
            title="🌟 تقييم جديد",
            color=0xFFD700,
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        embed.add_field(name="👤 العميل", value=interaction.user.mention, inline=False)
        embed.add_field(name="🏷️ رتبة العميل", value=role_text, inline=False)
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

        await review_channel.send(
            content=f"📢 تقييم جديد من {interaction.user.mention}",
            embed=embed,
        )
        await send_review_panel(review_channel)

        await interaction.response.send_message(
            "✅ تم إرسال تقييمك بنجاح.",
            ephemeral=True,
        )


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
                "❌ التقييم يعمل فقط في روم التقييمات.",
                ephemeral=True,
            )

        if not any(role.id == REVIEW_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ لا تملك صلاحية التقييم.",
                ephemeral=True,
            )

        await interaction.response.send_modal(ReviewModal())


@bot.command(name="تقييم", aliases=["تقيم", "reviewpanel"])
@commands.has_permissions(administrator=True)
async def review_panel(ctx: commands.Context):
    if ctx.channel.id != REVIEW_CHANNEL_ID:
        return await ctx.reply(
            f"❌ أمر التقييم يعمل فقط في روم <#{REVIEW_CHANNEL_ID}>.",
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
    print(f"✅ Review channel: {REVIEW_CHANNEL_ID}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)


# =====================================
# Run
# =====================================

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is missing.")

keep_alive()
bot.run(TOKEN)
