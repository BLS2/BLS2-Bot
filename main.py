import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput
from flask import Flask
from threading import Thread
import datetime
import os

# ===============================
# Flask
# ===============================

app = Flask(__name__)

@app.route("/")
def home():
    return "Review Bot Online"

def run_web():
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )

def keep_alive():
    Thread(target=run_web).start()

# ===============================
# Settings
# ===============================

TOKEN = os.getenv("TOKEN")

REVIEW_CHANNEL = 148144370438334058
REVIEW_ROLE = 1507511064399577098

# ===============================
# Bot
# ===============================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ===============================
# Stars
# ===============================

def stars(count):
    return "⭐" * count

# ===============================
# Review Modal
# ===============================

class ReviewModal(Modal, title="تقييم المنتج والخدمة"):

    product = TextInput(
        label="تقييم المنتج (1-10)",
        placeholder="مثال: 10",
        required=True,
        max_length=2
    )

    service = TextInput(
        label="تقييم الخدمة (1-10)",
        placeholder="مثال: 10",
        required=True,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            product_score = int(self.product.value)
            service_score = int(self.service.value)

        except:
            return await interaction.response.send_message(
                "❌ يجب إدخال أرقام فقط",
                ephemeral=True
            )

        if product_score < 1 or product_score > 10:
            return await interaction.response.send_message(
                "❌ تقييم المنتج يجب أن يكون بين 1 و 10",
                ephemeral=True
            )

        if service_score < 1 or service_score > 10:
            return await interaction.response.send_message(
                "❌ تقييم الخدمة يجب أن يكون بين 1 و 10",
                ephemeral=True
            )

        average = round(
            (product_score + service_score) / 2,
            1
        )

        review_channel = bot.get_channel(
            REVIEW_CHANNEL
        )

        embed = discord.Embed(
            title="📊 تم التقييم",
            color=0xFFD700,
            timestamp=datetime.datetime.now(datetime.UTC)
        )

        embed.add_field(
            name="👤 المستخدم",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="📦 تقييم المنتج",
            value=f"{product_score}/10\n{stars(product_score)}",
            inline=False
        )

        embed.add_field(
            name="💎 تقييم الخدمة",
            value=f"{service_score}/10\n{stars(service_score)}",
            inline=False
        )

        embed.add_field(
            name="🎯 التقييم النهائي",
            value=f"{average}/10",
            inline=False
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text="BLS Reviews System"
        )

        if review_channel:

            await review_channel.send(
                content=f"{interaction.user.mention}",
                embed=embed
            )

        role = interaction.guild.get_role(
            REVIEW_ROLE
        )

        if role and role in interaction.user.roles:

            try:
                await interaction.user.remove_roles(
                    role,
                    reason="Used Review System"
                )
            except:
                pass

        await interaction.response.send_message(
            "✅ تم إرسال تقييمك بنجاح",
            ephemeral=True
        )

# ===============================
# Button
# ===============================

class ReviewView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="⭐ تقييم المنتج والخدمة",
        style=discord.ButtonStyle.success,
        custom_id="review_button"
    )
    async def review_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not any(
            role.id == REVIEW_ROLE
            for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ لا تملك صلاحية التقييم",
                ephemeral=True
            )

        await interaction.response.send_modal(
            ReviewModal()
        )

# ===============================
# Review Panel Command
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def reviewpanel(ctx):

    embed = discord.Embed(
        title="⭐ تقييم العملاء",
        description="اضغط الزر بالأسفل لتقييم المنتج والخدمة",
        color=0xFFD700
    )

    if ctx.guild.icon:
        embed.set_thumbnail(
            url=ctx.guild.icon.url
        )

    await ctx.send(
        embed=embed,
        view=ReviewView()
    )

# ===============================
# Ready
# ===============================

@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")

    bot.add_view(
        ReviewView()
    )

# ===============================
# Run
# ===============================

keep_alive()

bot.run(TOKEN)

