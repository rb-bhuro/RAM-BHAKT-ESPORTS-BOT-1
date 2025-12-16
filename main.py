# main.py
import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime
import pytz
import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------- CONFIG ---------------- #
TOKEN = os.getenv("DISCORD_TOKEN_") or ""
TIMEZONE_DEFAULT = "Asia/Kolkata"
PORT = int(os.environ.get("PORT", 8080))
DATA_FILE = "schedules.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Global memory schedules
schedules = []          # temporary (reset on restart)
default_schedules = []  # permanent (stored in file)

# Global toggle for schedule sending
schedules_enabled = True

# 🔒 MOD LOGGING FILE
MOD_LOG_FILE = "modlog.json"

# intents = discord.Intents.default()
# intents.members = True
# intents.message_content = True
# intents.guilds = True
# intents.voice_states = True
# intents.moderation = True

# client = discord.Client(intents=intents)
# tree = app_commands.CommandTree(client)

import re

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Normalize message
    raw = message.content.lower()
    cleaned = re.sub(r'[^a-z\s]', '', raw)   # remove emojis & symbols
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # remove extra spaces

    # 👋 Normal greetings
    if any(w in ["hi", "hello", "hey", "helo", "hy"] for w in words):
       await message.reply("Hello 👋, Kaise ho sab thik..!")
       return

    # 🙏 Special greetings
    if "ram ram" in cleaned:
        await message.reply("🙏 Ram Ram")
        return

    if "radhe radhe" in cleaned:
        await message.reply("🌸 Radhe Radhe")
        return

    if "jai shree krishna" in cleaned or "jay shree krishn" in cleaned:
        await message.reply("🦚 Jai Shree Krishna")
        return

    if "good morning" in cleaned or "shubh prabhat" in cleaned:
        await message.reply("🌅 Good Morning")
        return

    if "good night" in cleaned or "shubh ratri" in cleaned or "subh ratri" in cleaned:
        await message.reply("🌙 Shubh Ratri")
        return

    # 🆘 Help message
    if "help" in cleaned or "support" in cleaned:
        await message.reply(
            "🆘 **Need help?**\n"
            "Please create a ticket in <#1437688698064867492> for fast support 🎫"
        )
        return

    # IMPORTANT: allow other commands & listeners
    await client.process_commands(message)


# ---------------- MOD LOGGING STORAGE ---------------- #
modlog_config = {
    "mod_role_id": None,
    "log_channel_id": None
}

def save_modlog():
    with open(MOD_LOG_FILE, "w") as f:
        json.dump(modlog_config, f)

def load_modlog():
    global modlog_config
    if os.path.exists(MOD_LOG_FILE):
        with open(MOD_LOG_FILE, "r") as f:
            modlog_config = json.load(f)

def is_mod(member: discord.Member):
    if not modlog_config["mod_role_id"]:
        return False
    return any(r.id == modlog_config["mod_role_id"] for r in member.roles)

async def send_log(guild, embed):
    if not modlog_config["log_channel_id"]:
        return
    ch = guild.get_channel(modlog_config["log_channel_id"])
    if ch:
        await ch.send(embed=embed)

def make_log_embed(title, mod, target, details=None, color=discord.Color.red()):
    embed = discord.Embed(title=title, color=color, timestamp=datetime.utcnow())
    embed.add_field(name="👮 Moderator", value=f"{mod.mention} (`{mod.id}`)", inline=False)
    embed.add_field(
        name="🎯 Target",
        value=f"{target.mention if hasattr(target,'mention') else target} (`{getattr(target,'id','N/A')}`)",
        inline=False
    )
    if details:
        embed.add_field(name="📄 Details", value=details, inline=False)
    return embed

# # ---------------- Permission Helper ---------------- #
# def is_admin(interaction: discord.Interaction) -> bool:
#     perms = getattr(interaction.user, "guild_permissions", None)
#     return perms and (perms.administrator or perms.manage_guild)


# ---------------- Permission Helper ---------------- #
def is_admin(interaction: discord.Interaction) -> bool:
    """Return True if the user has Manage Guild or Administrator permissions."""
    perms = getattr(interaction.user, "guild_permissions", None)
    if not perms:
        return False
    if perms.administrator or perms.manage_guild:
        return True
    return False


# ---------------- HTTP SERVER (keepalive) ---------------- #
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), PingHandler)
    print(f"✅ HTTP server running on port {PORT}")
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# ---------------- Persistence Helpers ---------------- #
def save_defaults():
    """Save permanent schedules to JSON file."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_schedules, f, indent=2)
    except Exception as e:
        print("⚠️ Failed to save defaults:", e)


def load_defaults():
    """Load permanent schedules from JSON file or set hardcoded defaults."""
    global default_schedules
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                default_schedules = json.load(f)
                print(f"✅ Loaded {len(default_schedules)} default schedules from file.")
                if default_schedules:
                    return
        except Exception as e:
            print("⚠️ Failed to load defaults:", e)
            default_schedules = []

    # Hardcoded fallback schedules (always available)
    default_schedules = [
        {
            "channel_id": 1375715974774394901,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "hour": 11,
            "minute": 55,
            "message": "# Registration Starting For 3 PM In 5 Min!!!\n\n**Register here <#1375715974774394901> **  \n**Check Tag in <#1375716156836548650> with proper 2 tags**\n\n|| @everyone ||",
            "timezone": TIMEZONE_DEFAULT,
            "last_sent": None
        },
        {
            "channel_id": 1380043318037057656,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "hour": 14,
            "minute": 55,
            "message": "# Registration Starting For 6 PM In 5 Min!!!\n\n**Register here <#1380043318037057656> **  \n**Check Tag in <#1375716156836548650> with proper 2 tags**\n\n|| @everyone ||",
            "timezone": TIMEZONE_DEFAULT,
            "last_sent": None
        },
        {
            "channel_id": 1418814352580149399,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "hour": 17,
            "minute": 55,
            "message": "# Registration Starting For 9 PM In 5 Min!!!\n\n**Register here <#1418814352580149399> **  \n**Check Tag in <#1375716156836548650> with proper 2 tags**\n\n|| @everyone ||",
            "timezone": TIMEZONE_DEFAULT,
            "last_sent": None
        },
        {
            "channel_id": 1377871211765436468,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "hour": 14,
            "minute": 50,
            "message": "**RULES OF CUSTOM** !!\n\n• RANDOM INVITE = KICK  \n• NO CHAT  \n• TAKE SQUAD ENTRY  \n• AFTER JOINING TELL TEAM NAME & SLOT NO.  \n• IF ANY ISSUE THEN TAG IN <#1375716279981183056>  \n• ALSO COME TO HELP DESK  \n\n**IDP TIME :- 2:55PM**  \n**ST TIME :- 3:07PM**",
            "timezone": TIMEZONE_DEFAULT,
            "last_sent": None
        },
        {
            "channel_id": 1380043562338484314,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "hour": 17,
            "minute": 50,
            "message": "**RULES OF CUSTOM** !!\n\n• RANDOM INVITE = KICK  \n• NO CHAT  \n• TAKE SQUAD ENTRY  \n• AFTER JOINING TELL TEAM NAME & SLOT NO.  \n• IF ANY ISSUE THEN TAG IN <#1375716279981183056>  \n• ALSO COME TO HELP DESK  \n\n**IDP TIME :- 5:55PM**  \n**ST TIME :- 6:07PM**",
            "timezone": TIMEZONE_DEFAULT,
            "last_sent": None
        },
        {
            "channel_id": 1418814704444244009,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "hour": 20,
            "minute": 50,
            "message": "**RULES OF CUSTOM** !!\n\n• RANDOM INVITE = KICK  \n• NO CHAT  \n• TAKE SQUAD ENTRY  \n• AFTER JOINING TELL TEAM NAME & SLOT NO.  \n• IF ANY ISSUE THEN TAG IN <#1375716279981183056>  \n• ALSO COME TO HELP DESK  \n\n**IDP TIME :- 8:55PM**  \n**ST TIME :- 9:07PM**",
            "timezone": TIMEZONE_DEFAULT,
            "last_sent": None
        },
        {
            "channel_id": 1335115774674862203,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "hour": 8,
            "minute": 0,
            "message": "**Ram Ram <@&1348282469115367497> 🙏**  \n**Good morning! 🌞**  \n**Aasha hai aaj ka din aapke liye khushiyon aur sukh-shanti se bhara ho ✨🌸**",
            "timezone": TIMEZONE_DEFAULT,
            "last_sent": None
        },
    ]
    print(f"✅ Loaded {len(default_schedules)} hardcoded fallback schedules.")


def add_schedule(message, channel_id, days, hour, minute, timezone, last_sent=None):
    schedules.append({
        "channel_id": channel_id,
        "days": days,
        "hour": hour,
        "minute": minute,
        "message": message,
        "timezone": timezone,
        "last_sent": last_sent
    })

# ---------------- SETUP MOD LOG ---------------- #
@tree.command(name="setmodlog", description="Setup moderator activity logging")
@app_commands.describe(mod_role_id="Moderator role ID")
async def setmodlog(interaction: discord.Interaction, mod_role_id: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    guild = interaction.guild
    mod_role = guild.get_role(int(mod_role_id))
    if not mod_role:
        await interaction.response.send_message("❌ Invalid role ID.", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True),
        mod_role: discord.PermissionOverwrite(view_channel=True)
    }

    channel = await guild.create_text_channel(
        "mod-activity-logs",
        overwrites=overwrites,
        reason="Moderator activity logging"
    )

    modlog_config["mod_role_id"] = int(mod_role_id)
    modlog_config["log_channel_id"] = channel.id
    save_modlog()

    await interaction.response.send_message(
        f"✅ Mod log channel created: {channel.mention}",
        ephemeral=True
    )

# ---------------- MESSAGE DELETE ---------------- #
@client.event
async def on_message_delete(message):
    if not message.guild:
        return

    async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
        mod = entry.user
        if isinstance(mod, discord.Member) and is_mod(mod):
            embed = make_log_embed(
                "🗑 Message Deleted",
                mod,
                message.author,
                f"📍 Channel: {message.channel.mention}\n```{message.content or 'Empty'}```"
            )
            await send_log(message.guild, embed)
        break

# ---------------- ROLE ADD / REMOVE ---------------- #
@client.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            mod = entry.user
            if is_mod(mod) and entry.target.id == after.id:
                added = set(after.roles) - set(before.roles)
                removed = set(before.roles) - set(after.roles)
                details = ""
                if added:
                    details += "➕ Added: " + ", ".join(r.mention for r in added) + "\n"
                if removed:
                    details += "➖ Removed: " + ", ".join(r.mention for r in removed)
                embed = make_log_embed("🎭 Role Updated", mod, after, details, discord.Color.orange())
                await send_log(after.guild, embed)
            break

    if before.communication_disabled_until != after.communication_disabled_until:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
            mod = entry.user
            if is_mod(mod) and entry.target.id == after.id:
                action = "⏱ Timeout Applied" if after.communication_disabled_until else "✅ Timeout Removed"
                embed = make_log_embed(
                    action,
                    mod,
                    after,
                    f"Until: {after.communication_disabled_until}"
                )
                await send_log(after.guild, embed)
            break

# ---------------- KICK ---------------- #
@client.event
async def on_member_remove(member):
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        mod = entry.user
        if is_mod(mod) and entry.target.id == member.id:
            embed = make_log_embed("👢 Member Kicked", mod, member)
            await send_log(member.guild, embed)
        break

# ---------------- BAN ---------------- #
@client.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        mod = entry.user
        if is_mod(mod) and entry.target.id == user.id:
            embed = make_log_embed("🔨 Member Banned", mod, user)
            await send_log(guild, embed)
        break

# ---------------- VOICE ---------------- #
@client.event
async def on_voice_state_update(member, before, after):
    if not is_mod(member):
        return
    if before.channel != after.channel:
        action = "🔊 Joined VC" if after.channel else "🔇 Left VC"
        channel = after.channel or before.channel
        embed = make_log_embed(action, member, member, f"Channel: {channel.mention}")
        await send_log(member.guild, embed)

# ---------------- ROLE CREATE / DELETE ---------------- #
@client.event
async def on_guild_role_create(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        mod = entry.user
        if is_mod(mod):
            embed = make_log_embed("🆕 Role Created", mod, role)
            await send_log(role.guild, embed)
        break

@client.event
async def on_guild_role_delete(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        mod = entry.user
        if is_mod(mod):
            embed = make_log_embed("❌ Role Deleted", mod, role)
            await send_log(role.guild, embed)
        break

# # ---------------- Schedule Checker (UNCHANGED) ---------------- #
# @tasks.loop(seconds=30)
# async def schedule_checker():
#     pass

# ---------------- Modal for multiline message ---------------- #
class ScheduleModal(discord.ui.Modal, title="Schedule message"):
    message = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        placeholder="Type your announcement here. Press Enter for new lines.",
        max_length=2000
    )

    def __init__(self, channel: discord.TextChannel, time_str: str, days: str, timezone: str, save_default=False):
        super().__init__()
        self.channel = channel
        self.time_str = time_str
        self.days = days
        self.timezone = timezone
        self.save_default = save_default

    async def on_submit(self, interaction: discord.Interaction):
        text = self.message.value.replace("\\n", "\n")
        try:
            hour, minute = map(int, self.time_str.split(":"))
        except Exception:
            await interaction.response.send_message("❌ Invalid time format. Use HH:MM (24-hour).", ephemeral=True)
            return

        days_list = [d.strip().lower() for d in self.days.split(",")]
        schedule_obj = {
            "channel_id": self.channel.id,
            "days": days_list,
            "hour": hour,
            "minute": minute,
            "message": text,
            "timezone": self.timezone,
            "last_sent": None
        }

        if self.save_default:
            default_schedules.append(schedule_obj)
            save_defaults()
            msg = "✅ Default schedule saved permanently."
        else:
            schedules.append(schedule_obj)
            msg = "✅ Temporary schedule added."

        await interaction.response.send_message(
            f"{msg}\nChannel: {self.channel.mention} | Time: {hour:02d}:{minute:02d} ({self.timezone}) | Days: {', '.join(days_list)}",
            ephemeral=True
        )

# ---------------- on_ready ---------------- #
@client.event
async def on_ready():
    load_defaults()
    print(f"✅ Logged in as {client.user} (ID: {client.user.id})")
    try:
        await tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print("⚠️ Command sync failed:", e)
    schedule_checker.start()

# ---------------- Slash commands ---------------- #
@tree.command(name="addschedule", description="Add a temporary schedule (lost on restart).")
@app_commands.describe(channel="Channel to send the message in", time="Time in HH:MM (24h)", days="Comma-separated days (monday,tuesday)")
async def addschedule(interaction: discord.Interaction, channel: discord.TextChannel, time: str, days: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    modal = ScheduleModal(channel, time, days, TIMEZONE_DEFAULT, save_default=False)
    await interaction.response.send_modal(modal)


@tree.command(name="adddefaultschedule", description="Add a permanent schedule that stays saved even after restart.")
@app_commands.describe(channel="Channel to send the message in", time="Time in HH:MM (24h)", days="Comma-separated days (monday,tuesday)")
async def adddefaultschedule(interaction: discord.Interaction, channel: discord.TextChannel, time: str, days: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    modal = ScheduleModal(channel, time, days, TIMEZONE_DEFAULT, save_default=True)
    await interaction.response.send_modal(modal)


@tree.command(name="listschedules", description="List all schedules (temporary + permanent)")
async def listschedules(interaction: discord.Interaction):
    all_schedules = default_schedules + schedules
    if not all_schedules:
        await interaction.response.send_message("📭 No schedules set.", ephemeral=True)
        return
    lines = ["**📅 All Schedules:**"]
    for i, s in enumerate(all_schedules, start=1):
        ch = client.get_channel(s["channel_id"])
        ch_name = ch.mention if ch else f"ID:{s['channel_id']}"
        t = "🧷 (Permanent)" if s in default_schedules else "🕐 (Temporary)"
        lines.append(f"**{i}** {t} ➤ {ch_name} | {', '.join(s['days'])} at {s['hour']:02d}:{s['minute']:02d} ({s['timezone']}) | Msg: {s['message'][:150]}{'...' if len(s['message'])>150 else ''}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@tree.command(name="listdefaultschedules", description="List permanent schedules only")
async def listdefaultschedules(interaction: discord.Interaction):
    if not default_schedules:
        await interaction.response.send_message("📭 No default schedules saved.", ephemeral=True)
        return
    lines = ["**🧷 Permanent Schedules:**"]
    for i, s in enumerate(default_schedules, start=1):
        ch = client.get_channel(s["channel_id"])
        ch_name = ch.mention if ch else f"ID:{s['channel_id']}"
        lines.append(f"**{i}** ➤ {ch_name} | {', '.join(s['days'])} at {s['hour']:02d}:{s['minute']:02d} ({s['timezone']}) | Msg: {s['message'][:150]}{'...' if len(s['message'])>150 else ''}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@tree.command(name="removedefaultschedule", description="Remove a permanent schedule by index")
async def removedefaultschedule(interaction: discord.Interaction, index: int):
    if index < 1 or index > len(default_schedules):
        await interaction.response.send_message(f"❌ Invalid index. Choose between 1 and {len(default_schedules)}.", ephemeral=True)
        return
    removed = default_schedules.pop(index - 1)
    save_defaults()
    await interaction.response.send_message(f"✅ Removed permanent schedule: `{removed['message'][:80]}...`", ephemeral=True)


@tree.command(name="clearschedules", description="Clear all temporary schedules")
async def clearschedules(interaction: discord.Interaction):
    schedules.clear()
    await interaction.response.send_message("🗑️ All temporary schedules cleared.", ephemeral=True)


@tree.command(name="help", description="Show help")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Bot Commands", color=discord.Color.blue())
    embed.add_field(name="/addschedule", value="Add a temporary schedule (lost on restart).", inline=False)
    embed.add_field(name="/adddefaultschedule", value="Add a permanent schedule (saved to file).", inline=False)
    embed.add_field(name="/listschedules", value="Show all schedules.", inline=False)
    embed.add_field(name="/listdefaultschedules", value="Show permanent ones only.", inline=False)
    embed.add_field(name="/removedefaultschedule", value="Delete a permanent schedule.", inline=False)
    embed.add_field(name="/clearschedules", value="Clear temporary schedules only.", inline=False)
    embed.add_field(name="/warn", value="Send a private DM warning to a member.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="toggleschedules", description="Turn all scheduled messages on or off.")
async def toggleschedules(interaction: discord.Interaction, state: str):
    global schedules_enabled
    if not is_admin(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    state = state.lower()
    if state not in ["on", "off"]:
        await interaction.response.send_message("⚠️ Use `/toggleschedules on` or `/toggleschedules off`.", ephemeral=True)
        return

    schedules_enabled = (state == "on")
    status_text = "🟢 Schedules enabled." if schedules_enabled else "🔴 Schedules disabled for now."
    await interaction.response.send_message(status_text, ephemeral=True)

# ---------------- Warn Command (with multiline input) ---------------- #
class WarnModal(discord.ui.Modal, title="Send Warning"):
    reason = discord.ui.TextInput(
        label="Warning Reason",
        style=discord.TextStyle.paragraph,
        placeholder="Enter reason for warning. You can use multiple lines.",
        max_length=2000
    )

    def __init__(self, member: discord.User):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.member.send(f"⚠️ **You have been warned!**\n\n{self.reason.value}")
            await interaction.response.send_message(f"✅ Warning sent to {self.member.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ Could not DM {self.member.mention}. Their DMs might be closed.", ephemeral=True)


@tree.command(name="warn", description="Send a warning DM to a user")
@app_commands.describe(member="User to warn")
async def warn(interaction: discord.Interaction, member: discord.User):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    modal = WarnModal(member)
    await interaction.response.send_modal(modal)


# ---------------- Direct DM Command (with multiline input) ---------------- #
class DMModal(discord.ui.Modal, title="Send Direct Message"):
    message = discord.ui.TextInput(
        label="Message Content",
        style=discord.TextStyle.paragraph,
        placeholder="Type your message here. You can use multiple lines.",
        max_length=2000
    )

    def __init__(self, member: discord.User):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.member.send(self.message.value)
            await interaction.response.send_message(f"✅ DM sent to {self.member.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ Could not DM {self.member.mention}. Their DMs might be closed.", ephemeral=True)


@tree.command(name="dmuser", description="Send a direct DM to a user")
@app_commands.describe(member="User to DM")
async def dmuser(interaction: discord.Interaction, member: discord.User):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    modal = DMModal(member)
    await interaction.response.send_modal(modal)

# ---------------- Schedule Checker ---------------- #
@tasks.loop(seconds=30)
async def schedule_checker():
    if not schedules_enabled:
        return

    now_utc = datetime.utcnow().replace(second=0, microsecond=0)
    all_scheds = default_schedules + schedules

    for s in all_scheds:
        tz = pytz.timezone(s.get("timezone", TIMEZONE_DEFAULT))
        now = datetime.now(tz)
        current_day = now.strftime("%A").lower()

        if current_day not in s["days"]:
            continue

        if s.get("last_sent") == now.strftime("%Y-%m-%d %H:%M"):
            continue

        if now.hour == s["hour"] and now.minute == s["minute"]:
            ch = client.get_channel(s["channel_id"])
            if ch:
                try:
                    formatted_msg = s["message"].replace("\\n", "\n").strip()
                    await ch.send(formatted_msg)
                    s["last_sent"] = now.strftime("%Y-%m-%d %H:%M")
                    print(f"✅ Sent scheduled message to #{ch.name}")
                except Exception as e:
                    print(f"⚠️ Failed to send message to {ch.id}: {e}")

# ---------------- Run Bot ---------------- #
client.run(TOKEN)







