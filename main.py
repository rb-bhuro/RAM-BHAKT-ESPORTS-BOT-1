# main.py
import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime
import pytz
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------- CONFIG ---------------- #
TOKEN = os.getenv("DISCORD_TOKEN") or ""
TIMEZONE_DEFAULT = "Asia/Kolkata"
PORT = int(os.environ.get("PORT", 8080))

intents = discord.Intents.default()
intents.members = True  # needed to find members by ID in guild
intents.message_content = True  # not strictly required for slash commands but good to keep

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Global schedules (shared across servers)
schedules = []  # each: {"channel_id": int, "days": ["monday"], "hour": int, "minute": int, "message": str, "timezone": str, "last_sent": date_or_None}

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

# ---------------- Helper ---------------- #
def add_schedule(message, channel_id, days, hour, minute, timezone):
    schedules.append({
        "channel_id": channel_id,
        "days": days,
        "hour": hour,
        "minute": minute,
        "message": message,
        "timezone": timezone,
        "last_sent": None
    })

# ---------------- Modal for multiline message ---------------- #
class ScheduleModal(discord.ui.Modal, title="Schedule message"):
    message = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        placeholder="Type your announcement here. Press Enter for new lines.",
        max_length=2000
    )

    def __init__(self, channel: discord.TextChannel, time_str: str, days: str, timezone: str):
        super().__init__()
        self.channel = channel
        self.time_str = time_str
        self.days = days
        self.timezone = timezone

    async def on_submit(self, interaction: discord.Interaction):
        text = self.message.value
        text = text.replace("\\n", "\n")  # convert literal \n to real newline
        try:
            hour, minute = map(int, self.time_str.split(":"))
        except Exception:
            await interaction.response.send_message("❌ Invalid time format. Use HH:MM (24-hour).", ephemeral=True)
            return

        days_list = [d.strip().lower() for d in self.days.split(",")]
        add_schedule(text, self.channel.id, days_list, hour, minute, self.timezone)

        await interaction.response.send_message(
            f"✅ Schedule added for {self.channel.mention} at {hour:02d}:{minute:02d} ({self.timezone}) on {', '.join(days_list)}",
            ephemeral=True
        )

# ---------------- on_ready ---------------- #
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user} (ID: {client.user.id})")
    try:
        await tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print("⚠️ Command sync failed:", e)
    schedule_checker.start()

# ---------------- Slash commands ---------------- #
@tree.command(name="addschedule", description="Add a schedule (opens a modal to enter multiline message).")
@app_commands.describe(channel="Channel to send the message in", time="Time in HH:MM (24h)", days="Comma-separated days (monday,tuesday)")
async def addschedule(interaction: discord.Interaction, channel: discord.TextChannel, time: str, days: str):
    modal = ScheduleModal(channel, time, days, TIMEZONE_DEFAULT)
    await interaction.response.send_modal(modal)

@tree.command(name="listschedules", description="List all schedules")
async def listschedules(interaction: discord.Interaction):
    if not schedules:
        await interaction.response.send_message("📭 No schedules set.", ephemeral=True)
        return
    lines = ["**📅 Current Schedules:**"]
    for i, s in enumerate(schedules, start=1):
        ch = client.get_channel(s["channel_id"])
        ch_name = ch.mention if ch else f"ID:{s['channel_id']}"
        lines.append(f"**{i}** ➤ {ch_name} | {', '.join(s['days'])} at {s['hour']:02d}:{s['minute']:02d} ({s['timezone']}) | Msg: {s['message'][:200]}{'...' if len(s['message'])>200 else ''}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)

@tree.command(name="removeschedule", description="Remove a schedule by index (use /listschedules to see indices)")
async def removeschedule(interaction: discord.Interaction, index: int):
    if index < 1 or index > len(schedules):
        await interaction.response.send_message(f"❌ Invalid index. Choose between 1 and {len(schedules)}.", ephemeral=True)
        return
    removed = schedules.pop(index - 1)
    await interaction.response.send_message(f"✅ Removed schedule: `{removed['message'][:80]}{'...' if len(removed['message'])>80 else ''}`", ephemeral=True)

@tree.command(name="clearschedules", description="Clear all schedules")
async def clearschedules(interaction: discord.Interaction):
    schedules.clear()
    await interaction.response.send_message("🗑️ All schedules cleared.", ephemeral=True)

@tree.command(name="help", description="Show help")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Bot Commands", color=discord.Color.blue())
    embed.add_field(name="/addschedule channel time days", value="Add a schedule. Opens a modal to type the multi-line message.", inline=False)
    embed.add_field(name="/listschedules", value="Show all schedules.", inline=False)
    embed.add_field(name="/removeschedule index", value="Remove schedule by index.", inline=False)
    embed.add_field(name="/clearschedules", value="Remove all schedules.", inline=False)
    embed.add_field(name="/warn member reason", value="Send a private DM warning to a member.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------------- NEW COMMAND: Warn ---------------- #
@tree.command(name="warn", description="Send a warning DM to a user")
@app_commands.describe(member="User to warn", reason="Reason for the warning")
async def warn(interaction: discord.Interaction, member: discord.User, reason: str):
    """Warns a member by sending them a direct message. Works in DMs and servers."""
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
    for s in schedules:
        if (current_day in s["days"] and current_hour == s["hour"] and current_minute == s["minute"]):
            if s["last_sent"] != current_date:
                ch = client.get_channel(s["channel_id"])
                if ch:
                    try:
                        await ch.send(s["message"])
                        s["last_sent"] = current_date
                    except Exception as e:
                        print("❌ Failed to send message:", e)

@schedule_checker.before_loop
async def before_schedule_checker():
    await client.wait_until_ready()

# ---------------- RUN ---------------- #
client.run(TOKEN)
