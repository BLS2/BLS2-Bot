import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput
import datetime
import os

TOKEN = os.getenv("TOKEN")

# ===============================
# الإعدادات
# ===============================

REVIEW_CHANNEL = 148144370438334058
REVIEW_ROLE = 1507511064399577098

# ===============================
# البوت
# ===============================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ===============================
# النجوم
# ===============================

def stars(amount):
    return "⭐" * amount

# ===============================
# مودال التقييم
# ===============================

class ReviewModal(Modal, title="تقييم المنتج والخدمة"):

    product = TextInput(
        label="تقييم المنتج (1-10)",
        placeholder="اكتب رقم من 1 إلى 10",
        required=True,
        max_length=2
    )

    service = TextInput(
        label="تقييم الخدمة (1-10)",
        placeholder="اكتب رقم من 1 إلى 10",
        required=True,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            product_score = int(self.product.value)
            service_score = int(self.service.value)

        except:
            return await interaction.response.send_message(
                "❌ يجب كتابة أرقام فقط.",
                ephemeral=True
            )

        if not 1 <= product_score <= 10:
            return await interaction.response.send_message(
                "❌ تقييم المنتج يجب أن يكون بين 1 و 10.",
                ephemeral=True
            )

        if not 1 <= service_score <= 10:
            return await interaction.response.send_message(
                "❌ تقييم الخدمة يجب أن يكون بين 1 و 10.",
                ephemeral=True
            )

        average = round(
            (product_score + service_score) / 2,
            1
        )

        embed = discord.Embed(
            title="⭐ تقييم جديد",
            color=0xFFD700,
            timestamp=datetime.datetime.now(datetime.UTC)
        )

        embed.add_field(
            name="👤 العميل",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="🏆 تقييم المنتج",
            value=f"{stars(product_score)}\n**{product_score}/10**",
            inline=False
        )

        embed.add_field(
            name="💎 تقييم الخدمة",
            value=f"{stars(service_score)}\n**{service_score}/10**",
            inline=False
        )

        embed.add_field(
            name="📊 التقييم النهائي",
            value=f"**{average}/10**",
            inline=False
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text=f"تم التقييم بواسطة {interaction.user}"
        )

        channel = bot.get_channel(REVIEW_CHANNEL)

        if channel:
            await channel.send(
                content=interaction.user.mention,
                embed=embed
            )

        role = interaction.guild.get_role(REVIEW_ROLE)

        if role and role in interaction.user.roles:
            await interaction.user.remove_roles(role)

        await interaction.response.send_message(
            "✅ تم إرسال تقييمك بنجاح.",
            ephemeral=True
        )

# ===============================
# زر التقييم
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
                "❌ لا تملك صلاحية التقييم.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            ReviewModal()
        )

# ===============================
# إرسال لوحة التقييم
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def reviewpanel(ctx):

    embed = discord.Embed(
        title="⭐ تقييم العملاء",
        description=(
            "نرحب بتقييمكم لخدماتنا.\n\n"
            "اضغط الزر بالأسفل لتقييم المنتج والخدمة."
        ),
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
# تشغيل البوت
# ===============================

@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")

    bot.add_view(
        ReviewView()
    )

bot.run(TOKEN)
