import datetime
import json
import os
import re
from pathlib import Path
from threading import Thread

import discord
from discord.ext import commands, tasks
from discord.ui import Modal, TextInput, View
from flask import Flask


# =====================================
# Keep alive
# =====================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Professional Discord Bot Online"


def run_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))


def keep_alive():
    Thread(target=run_web, daemon=True).start()


# =====================================
# Settings
# =====================================

TOKEN = os.getenv("TOKEN")
DATA_FILE = Path("bot_data.json")

# نظام التقييم
REVIEW_CHANNEL_ID = 1481443704383340585
REVIEW_ROLE_ID = 1507511064399577098

REVIEW_PANEL_TITLE = "⭐ تقييم العملاء"
REVIEW_PANEL_DESCRIPTION = "اضغط الزر لتقييم المنتج والخدمة"

# نظام الإجازات
# مهم: غير هذا ID لروم لوحة الإجازات الصحيح.
# ما وصلني ID روم لوحة الإجازات، فحطيته مؤقتا نفس روم لوقات الإجازات.
LEAVE_PANEL_CHANNEL_ID = 1490820000477610036
LEAVE_LOG_CHANNEL_ID = 1490820000477610036
LEAVE_ROLE_ID = 1492607429249339502
MIN_LEAVE_DAYS = 3
MAX_LEAVE_DAYS = 14
LEAVE_WITHDRAW_LIMIT_HOURS = 24

LEAVE_PANEL_TITLE = "نظام الإجازات"
LEAVE_PANEL_DESCRIPTION = (
    "رصيد كل إداري: 14 يوم شهريا\n"
    "أقل طلب إجازة: 3 أيام\n"
    "يمكن سحب الإجازة خلال أول 24 ساعة فقط"
)

# نظام الإنذارات
WARNING_PANEL_CHANNEL_ID = 1519288509633138740
WARNING_LOG_CHANNEL_ID = 1479608600350429194

WARNING_PANEL_TITLE = "نظام الإنذارات"
WARNING_PANEL_DESCRIPTION = "استخدم الأزرار لتنزيل إنذار أو سحب إنذار من عضو"


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
# Data
# =====================================

default_data = {
    "review_panel_message_id": None,
    "leave_panel_message_id": None,
    "warning_panel_message_id": None,
    "active_leaves": {},
}

data = default_data.copy()
views_registered = False


def load_data() -> None:
    global data

    if not DATA_FILE.exists():
        data = default_data.copy()
        return

    try:
        loaded = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = default_data.copy()
        return

    data = default_data.copy()
    data.update(loaded)
    data.setdefault("active_leaves", {})


def save_data() -> None:
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# =====================================
# Helpers
# =====================================

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def parse_datetime(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value)


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


def build_leave_panel_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=LEAVE_PANEL_TITLE,
        description=LEAVE_PANEL_DESCRIPTION,
        color=0x5865F2,
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=f"{guild.name} • Vacation System")
    return embed


def build_warning_panel_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=WARNING_PANEL_TITLE,
        description=WARNING_PANEL_DESCRIPTION,
        color=0xED4245,
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=f"{guild.name} • Warning System")
    return embed


def parse_duration(value: str) -> datetime.timedelta | None:
    text = value.strip().lower()
    match = re.search(r"(\d+)\s*(دقيقة|دقايق|د|m|minute|minutes|ساعة|ساعات|س|h|hour|hours|يوم|ايام|أيام|d|day|days)", text)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit in {"دقيقة", "دقايق", "د", "m", "minute", "minutes"}:
        return datetime.timedelta(minutes=amount)

    if unit in {"ساعة", "ساعات", "س", "h", "hour", "hours"}:
        return datetime.timedelta(hours=amount)

    if unit in {"يوم", "ايام", "أيام", "d", "day", "days"}:
        return datetime.timedelta(days=amount)

    return None


async def get_text_channel(guild: discord.Guild, channel_id: int) -> discord.TextChannel | None:
    channel = guild.get_channel(channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    return channel if isinstance(channel, discord.TextChannel) else None


async def send_or_replace_panel(
    channel: discord.TextChannel,
    message_key: str,
    embed: discord.Embed,
    view: View,
) -> discord.Message:
    old_message_id = data.get(message_key)
    if old_message_id:
        try:
            old_message = await channel.fetch_message(old_message_id)
            await old_message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    message = await channel.send(embed=embed, view=view)
    data[message_key] = message.id
    save_data()
    return message


async def send_review_panel(channel: discord.TextChannel) -> discord.Message:
    return await send_or_replace_panel(
        channel=channel,
        message_key="review_panel_message_id",
        embed=build_review_panel_embed(channel.guild),
        view=ReviewView(),
    )


async def send_leave_panel(channel: discord.TextChannel) -> discord.Message:
    return await send_or_replace_panel(
        channel=channel,
        message_key="leave_panel_message_id",
        embed=build_leave_panel_embed(channel.guild),
        view=LeaveView(),
    )


async def send_warning_panel(channel: discord.TextChannel) -> discord.Message:
    return await send_or_replace_panel(
        channel=channel,
        message_key="warning_panel_message_id",
        embed=build_warning_panel_embed(channel.guild),
        view=WarningView(),
    )


# =====================================
# Review system
# =====================================

class ReviewModal(Modal, title="تقييم المنتج والخدمة"):
    product_name = TextInput(
        label="المنتج الذي اشتريته",
        placeholder="مثال: بوت حماية، سيرفر كامل، رتبة...",
        required=True,
        max_length=50,
    )

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
                "❌ يجب إدخال أرقام فقط في خانات التقييم.",
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
            timestamp=utc_now(),
        )
        embed.add_field(name="👤 العميل", value=interaction.user.mention, inline=False)
        embed.add_field(name="🏷️ رتبة العميل", value=role_text, inline=False)
        embed.add_field(name="🛒 المنتج المشترى", value=f"**{self.product_name.value}**", inline=False)
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
# Leave system
# =====================================

class LeaveRequestModal(Modal, title="طلب إجازة"):
    reason = TextInput(
        label="سبب الإجازة",
        placeholder="اكتب سبب الإجازة",
        required=True,
        max_length=300,
        style=discord.TextStyle.paragraph,
    )

    days = TextInput(
        label="عدد الأيام",
        placeholder="من 3 إلى 14",
        required=True,
        max_length=2,
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_key = str(interaction.user.id)

        if user_key in data["active_leaves"]:
            return await interaction.response.send_message(
                "❌ لديك إجازة فعالة بالفعل.",
                ephemeral=True,
            )

        try:
            days = int(self.days.value)
        except ValueError:
            return await interaction.response.send_message(
                "❌ عدد الأيام لازم يكون رقم.",
                ephemeral=True,
            )

        if not MIN_LEAVE_DAYS <= days <= MAX_LEAVE_DAYS:
            return await interaction.response.send_message(
                f"❌ أقل إجازة {MIN_LEAVE_DAYS} أيام وأكثر إجازة {MAX_LEAVE_DAYS} يوم.",
                ephemeral=True,
            )

        role = interaction.guild.get_role(LEAVE_ROLE_ID)
        if role is None:
            return await interaction.response.send_message(
                "❌ لم أستطع العثور على رتبة الإجازات.",
                ephemeral=True,
            )

        try:
            await interaction.user.add_roles(role, reason="Vacation request")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ لا أملك صلاحية إعطاء رتبة الإجازات.",
                ephemeral=True,
            )

        requested_at = utc_now()
        ends_at = requested_at + datetime.timedelta(days=days)
        data["active_leaves"][user_key] = {
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "reason": self.reason.value,
            "days": days,
            "requested_at": requested_at.isoformat(),
            "ends_at": ends_at.isoformat(),
        }
        save_data()

        log_channel = await get_text_channel(interaction.guild, LEAVE_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="طلب إجازة جديد",
                color=0x57F287,
                timestamp=requested_at,
            )
            embed.add_field(name="الشخص", value=interaction.user.mention, inline=False)
            embed.add_field(name="عدد الأيام", value=f"{days} يوم", inline=True)
            embed.add_field(name="تنتهي في", value=discord.utils.format_dt(ends_at, "F"), inline=True)
            embed.add_field(name="السبب", value=self.reason.value, inline=False)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"{interaction.guild.name} • Vacation System")
            await log_channel.send(content=f"📌 {interaction.user.mention} طلب إجازة.", embed=embed)

        await interaction.response.send_message(
            f"✅ تم قبول طلب إجازتك لمدة {days} يوم.",
            ephemeral=True,
        )


class LeaveView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="طلب إجازة",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="leave_request_button",
    )
    async def request_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LeaveRequestModal())

    @discord.ui.button(
        label="سحب الإجازة",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="leave_withdraw_button",
    )
    async def withdraw_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_key = str(interaction.user.id)
        leave = data["active_leaves"].get(user_key)

        if leave is None:
            return await interaction.response.send_message(
                "❌ لا توجد لديك إجازة فعالة.",
                ephemeral=True,
            )

        requested_at = parse_datetime(leave["requested_at"])
        withdraw_limit = requested_at + datetime.timedelta(hours=LEAVE_WITHDRAW_LIMIT_HOURS)
        if utc_now() > withdraw_limit:
            return await interaction.response.send_message(
                "❌ انتهت مدة سحب الإجازة. يمكنك السحب خلال أول 24 ساعة فقط.",
                ephemeral=True,
            )

        role = interaction.guild.get_role(LEAVE_ROLE_ID)
        if role:
            try:
                await interaction.user.remove_roles(role, reason="Vacation withdrawn")
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "❌ لا أملك صلاحية سحب رتبة الإجازات.",
                    ephemeral=True,
                )

        data["active_leaves"].pop(user_key, None)
        save_data()

        log_channel = await get_text_channel(interaction.guild, LEAVE_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="تم سحب الإجازة",
                color=0xED4245,
                timestamp=utc_now(),
            )
            embed.add_field(name="الشخص", value=interaction.user.mention, inline=False)
            embed.add_field(name="مدة الإجازة السابقة", value=f"{leave['days']} يوم", inline=True)
            embed.add_field(name="السبب السابق", value=leave["reason"], inline=False)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"{interaction.guild.name} • Vacation System")
            await log_channel.send(content=f"📌 {interaction.user.mention} سحب إجازته.", embed=embed)

        await interaction.response.send_message(
            "✅ تم سحب إجازتك بنجاح.",
            ephemeral=True,
        )


@tasks.loop(minutes=5)
async def check_expired_leaves():
    now = utc_now()
    changed = False

    for user_key, leave in list(data["active_leaves"].items()):
        ends_at = parse_datetime(leave["ends_at"])
        if now < ends_at:
            continue

        guild = bot.get_guild(int(leave["guild_id"]))
        if guild is None:
            continue

        member = guild.get_member(int(leave["user_id"]))
        role = guild.get_role(LEAVE_ROLE_ID)
        if member and role:
            try:
                await member.remove_roles(role, reason="Vacation ended")
            except discord.Forbidden:
                continue

        data["active_leaves"].pop(user_key, None)
        changed = True

        log_channel = await get_text_channel(guild, LEAVE_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="انتهت الإجازة",
                color=0x5865F2,
                timestamp=now,
            )
            embed.add_field(name="الشخص", value=f"<@{leave['user_id']}>", inline=False)
            embed.add_field(name="مدة الإجازة", value=f"{leave['days']} يوم", inline=True)
            embed.set_footer(text=f"{guild.name} • Vacation System")
            await log_channel.send(content=f"📌 انتهت إجازة <@{leave['user_id']}> وتم سحب الرتبة.", embed=embed)

    if changed:
        save_data()


# =====================================
# Warning system
# =====================================

class WarningIssueModal(Modal, title="تنزيل إنذار"):
    member_id = TextInput(
        label="كوبي ID الشخص",
        placeholder="مثال: 123456789012345678",
        required=True,
        max_length=25,
    )

    reason = TextInput(
        label="سبب الإنذار",
        placeholder="اكتب سبب الإنذار",
        required=True,
        max_length=300,
        style=discord.TextStyle.paragraph,
    )

    duration = TextInput(
        label="مدة التايم آوت",
        placeholder="مثال: 1 يوم أو 6 ساعات أو 30 دقيقة",
        required=True,
        max_length=30,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                "❌ هذا النظام يحتاج صلاحية Moderate Members.",
                ephemeral=True,
            )

        try:
            member_id = int(self.member_id.value.strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ اكتب ID الشخص بشكل صحيح.",
                ephemeral=True,
            )

        member = interaction.guild.get_member(member_id)
        if member is None:
            try:
                member = await interaction.guild.fetch_member(member_id)
            except (discord.NotFound, discord.HTTPException):
                return await interaction.response.send_message(
                    "❌ لم أستطع العثور على العضو.",
                    ephemeral=True,
                )

        duration_delta = parse_duration(self.duration.value)
        if duration_delta is None:
            return await interaction.response.send_message(
                "❌ اكتب المدة مثل: 1 يوم، 6 ساعات، 30 دقيقة.",
                ephemeral=True,
            )

        if duration_delta < datetime.timedelta(minutes=1):
            return await interaction.response.send_message(
                "❌ أقل مدة تايم آوت دقيقة واحدة.",
                ephemeral=True,
            )

        if duration_delta > datetime.timedelta(days=28):
            return await interaction.response.send_message(
                "❌ أقصى مدة تايم آوت في ديسكورد 28 يوم.",
                ephemeral=True,
            )

        until = utc_now() + duration_delta
        try:
            await member.timeout(until, reason=self.reason.value)
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ لا أملك صلاحية إعطاء تايم آوت لهذا الشخص.",
                ephemeral=True,
            )

        log_channel = await get_text_channel(interaction.guild, WARNING_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="إنذار جديد",
                color=0xED4245,
                timestamp=utc_now(),
            )
            embed.add_field(name="الشخص", value=member.mention, inline=False)
            embed.add_field(name="المسؤول", value=interaction.user.mention, inline=False)
            embed.add_field(name="المدة", value=self.duration.value, inline=True)
            embed.add_field(name="ينتهي في", value=discord.utils.format_dt(until, "F"), inline=True)
            embed.add_field(name="السبب", value=self.reason.value, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"{interaction.guild.name} • Warning System")
            await log_channel.send(content=f"⚠️ تم إنذار {member.mention}", embed=embed)

        await interaction.response.send_message(
            f"✅ تم تنزيل إنذار على {member.mention}.",
            ephemeral=True,
        )


class WarningRemoveModal(Modal, title="سحب إنذار"):
    member_id = TextInput(
        label="كوبي ID الشخص",
        placeholder="مثال: 123456789012345678",
        required=True,
        max_length=25,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                "❌ هذا النظام يحتاج صلاحية Moderate Members.",
                ephemeral=True,
            )

        try:
            member_id = int(self.member_id.value.strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ اكتب ID الشخص بشكل صحيح.",
                ephemeral=True,
            )

        member = interaction.guild.get_member(member_id)
        if member is None:
            try:
                member = await interaction.guild.fetch_member(member_id)
            except (discord.NotFound, discord.HTTPException):
                return await interaction.response.send_message(
                    "❌ لم أستطع العثور على العضو.",
                    ephemeral=True,
                )

        try:
            await member.timeout(None, reason=f"Warning removed by {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ لا أملك صلاحية سحب التايم آوت من هذا الشخص.",
                ephemeral=True,
            )

        log_channel = await get_text_channel(interaction.guild, WARNING_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="تم سحب الإنذار",
                color=0x57F287,
                timestamp=utc_now(),
            )
            embed.add_field(name="الشخص", value=member.mention, inline=False)
            embed.add_field(name="المسؤول", value=interaction.user.mention, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"{interaction.guild.name} • Warning System")
            await log_channel.send(content=f"✅ تم سحب الإنذار من {member.mention}", embed=embed)

        await interaction.response.send_message(
            f"✅ تم سحب الإنذار من {member.mention}.",
            ephemeral=True,
        )


class WarningView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="تنزيل إنذار",
        emoji="⚠️",
        style=discord.ButtonStyle.danger,
        custom_id="warning_issue_button",
    )
    async def issue_warning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WarningIssueModal())

    @discord.ui.button(
        label="سحب إنذار",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="warning_remove_button",
    )
    async def remove_warning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WarningRemoveModal())


# =====================================
# Events
# =====================================

@bot.event
async def on_ready():
    global views_registered

    load_data()

    if not views_registered:
        bot.add_view(ReviewView())
        bot.add_view(LeaveView())
        bot.add_view(WarningView())
        views_registered = True

    for guild in bot.guilds:
        leave_channel = await get_text_channel(guild, LEAVE_PANEL_CHANNEL_ID)
        if leave_channel:
            await send_leave_panel(leave_channel)

        warning_channel = await get_text_channel(guild, WARNING_PANEL_CHANNEL_ID)
        if warning_channel:
            await send_warning_panel(warning_channel)

    if not check_expired_leaves.is_running():
        check_expired_leaves.start()

    print(f"✅ Logged in as {bot.user}")
    print(f"✅ Review channel: {REVIEW_CHANNEL_ID}")
    print(f"✅ Leave panel channel: {LEAVE_PANEL_CHANNEL_ID}")
    print(f"✅ Warning panel channel: {WARNING_PANEL_CHANNEL_ID}")


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
