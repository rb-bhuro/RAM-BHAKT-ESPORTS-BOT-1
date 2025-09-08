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
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# In-memory schedule storage
schedules = []

# ---------------- TINY HTTP SERVER ---------------- #
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

def start_http_server():
    server = HTTPServer(("", PORT), SimpleHandler)
    print(f"✅ HTTP server running on port {PORT}")
    server.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

# ---------------- FUNCTIONS ---------------- #
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

# ---------------- EVENTS ---------------- #
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    await tree.sync()  # sync slash commands
    schedule_checker.start()

# ---------------- SLASH COMMANDS ---------------- #
@tree.command(name="addschedule", description="Add a schedule")
async def addschedule(interaction: discord.Interaction, channel: discord.TextChannel, time: str, days: str, message: str):
    try:
        hour, minute = map(int, time.split(":"))
        days_list = [d.strip().lower() for d in days.split(",")]
        add_schedule(message, channel.id, days_list, hour, minute, TIMEZONE_DEFAULT)

        await interaction.response.send_message(
            f"✅ **Schedule added:**\n"
            f"📢 Channel: {channel.mention}\n"
            f"📅 Days: {', '.join(days_list)}\n"
            f"⏰ Time: {hour:02d}:{minute:02d} ({TIMEZONE_DEFAULT})\n"
            f"💬 Message: {message}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}")

@tree.command(name="listschedules", description="List all schedules")
async def listschedules(interaction: discord.Interaction):
    if not schedules:
        await interaction.response.send_message("📭 No schedules set.")
        return
    msg = "**📅 Current Schedules:**\n"
    for i, s in enumerate(schedules, start=1):
        ch = client.get_channel(s["channel_id"])
        ch_name = ch.mention if ch else f"ID:{s['channel_id']}"
        msg += f"**{i}** ➡ {ch_name} | {', '.join(s['days'])} at {s['hour']:02d}:{s['minute']:02d} ({s['timezone']}) | Msg: {s['message']}\n"
    await interaction.response.send_message(msg)

@tree.command(name="removeschedule", description="Remove a schedule by index")
async def removeschedule(interaction: discord.Interaction, index: int):
    if index < 1 or index > len(schedules):
        await interaction.response.send_message(f"❌ Invalid index. Choose between 1 and {len(schedules)}.")
        return
    removed = schedules.pop(index - 1)
    await interaction.response.send_message(f"✅ Removed schedule: `{removed['message']}`")

@tree.command(name="clearschedules", description="Clear all schedules")
async def clearschedules(interaction: discord.Interaction):
    schedules.clear()
    await interaction.response.send_message("🗑️ All schedules cleared.")

@tree.command(name="help", description="Show help")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Bot Commands", color=discord.Color.blue())
    embed.add_field(name="/addschedule", value="Add a New schedule.\nExample: `!addschedule #general 21:30 monday,tuesday Hello!`", inline=False)
    embed.add_field(name="/listschedules", value="Show all schedules", inline=False)
    embed.add_field(name="/removeschedule", value="Remove a schedule", inline=False)
    embed.add_field(name="/clearschedules", value="Remove all schedules", inline=False)
    embed.add_field(name="/help", value="Show this help message", inline=False)
    await interaction.response.send_message(embed=embed)

# ---------------- BACKGROUND TASK ---------------- #
@tasks.loop(seconds=50)
async def schedule_checker():
    now = datetime.now(pytz.timezone(TIMEZONE_DEFAULT))
    current_day = now.strftime("%A").lower()
    current_hour = now.hour
    current_minute = now.minute
    current_date = now.date()

    for s in schedules:
        if (current_day in s["days"]
            and current_hour == s["hour"]
            and current_minute == s["minute"]):

            if s["last_sent"] != current_date:
                ch = client.get_channel(s["channel_id"])
                if ch:
                    try:
                        await ch.send(s["message"])
                        s["last_sent"] = current_date
                    except Exception as e:
                        print(f"❌ Failed to send message: {e}")

@schedule_checker.before_loop
async def before_schedule_checker():
    await client.wait_until_ready()

# ---------------- RUN BOT ---------------- #
client.run(TOKEN)
