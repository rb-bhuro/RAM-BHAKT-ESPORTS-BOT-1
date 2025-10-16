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
TOKEN = os.getenv("DISCORD_TOKEN") or ""
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
    """Load permanent schedules from JSON file."""
    global default_schedules
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                default_schedules = json.load(f)
                print(f"✅ Loaded {len(default_schedules)} default schedules from file.")
        except Exception as e:
            print("⚠️ Failed to load defaults:", e)
            default_schedules = []
    else:
        default_schedules = []

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
    modal = ScheduleModal(channel, time, days, TIMEZONE_DEFAULT, save_default=False)
    await interaction.response.send_modal(modal)

@tree.command(name="adddefaultschedule", description="Add a permanent schedule that stays saved even after restart.")
@app_commands.describe(channel="Channel to send the message in", time="Time in HH:MM (24h)", days="Comma-separated days (monday,tuesday)")
async def adddefaultschedule(interaction: discord.Interaction, channel: discord.TextChannel, time: str, days: str):
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

# ---------------- Warn Command ---------------- #
@tree.command(name="warn", description="Send a warning DM to a user")
@app_commands.describe(member="User to warn", reason="Reason for the warning")
async def warn(interaction: discord.Interaction, member: discord.User, reason: str):
    try:
        await member.send(f"⚠️ **You have been warned!**\nReason: {reason}")
        await interaction.response.send_message(f"✅ Warning sent to {member.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Could not DM {member.mention}. Their DMs might be closed.", ephemeral=True)

# ---------------- Background scheduler ---------------- #
@tasks.loop(seconds=50)
async def schedule_checker():
    now = datetime.now(pytz.timezone(TIMEZONE_DEFAULT))
    current_day = now.strftime("%A").lower()
    current_hour = now.hour
    current_minute = now.minute
    current_date = now.date()

    for s in default_schedules + schedules:
        if (current_day in s["days"] and current_hour == s["hour"] and current_minute == s["minute"]):
            if s.get("last_sent") != str(current_date):
                ch = client.get_channel(s["channel_id"])
                if ch:
                    try:
                        await ch.send(s["message"])
                        s["last_sent"] = str(current_date)
                        save_defaults()
                    except Exception as e:
                        print("❌ Failed to send message:", e)

@schedule_checker.before_loop
async def before_schedule_checker():
    await client.wait_until_ready()

# ---------------- RUN ---------------- #
client.run(TOKEN)
