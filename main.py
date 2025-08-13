import discord
from discord.ext import commands, tasks
from datetime import datetime
import pytz

# ---------------- CONFIG ---------------- #
TOKEN = "MTM5NTQzMDQ0Mjk0OTI4NDA3Mw.GiauwA.r5WBBNAZr5mtQeX5SwxUokHayGxJ3nRvSLEp8g"  # Replace with your bot token
TIMEZONE_DEFAULT = "Asia/Kolkata"  # Change if needed

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# In-memory schedule storage
schedules = []  # Each schedule will have a "last_sent" to avoid duplicates

# ---------------- SCHEDULE FUNCTIONS ---------------- #
def add_schedule(message, channel_id, days, hour, minute, timezone):
    schedules.append({
        "channel_id": channel_id,
        "days": days,
        "hour": hour,
        "minute": minute,
        "message": message,
        "timezone": timezone,
        "last_sent": None  # Track when it was last sent
    })

# ---------------- EVENTS ---------------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    schedule_checker.start()

# ---------------- COMMANDS ---------------- #
@bot.command()
async def addschedule(ctx, channel: discord.TextChannel, time_str: str, days: str, *, message: str):
    """
    Add a schedule.
    Example:
    !addschedule #general 21:29 monday,tuesday Hello World!
    """
    try:
        hour, minute = map(int, time_str.split(":"))
        days_list = [d.strip().lower() for d in days.split(",")]

        add_schedule(message, channel.id, days_list, hour, minute, TIMEZONE_DEFAULT)

        await ctx.send(
            f"✅ **Schedule added:**\n"
            f"📢 Channel: {channel.mention}\n"
            f"📅 Days: {', '.join(days_list)}\n"
            f"⏰ Time: {hour:02d}:{minute:02d} ({TIMEZONE_DEFAULT})\n"
            f"💬 Message: {message}"
        )
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def listschedules(ctx):
    """List all schedules."""
    if not schedules:
        await ctx.send("📭 No schedules set.")
        return

    msg = "**📅 Current Schedules:**\n"
    for i, s in enumerate(schedules, start=1):
        ch = bot.get_channel(s["channel_id"])
        ch_name = ch.mention if ch else f"ID:{s['channel_id']}"
        msg += f"**{i}** ➡ {ch_name} | {', '.join(s['days'])} at {s['hour']:02d}:{s['minute']:02d} ({s['timezone']}) | Msg: {s['message']}\n"
    await ctx.send(msg)

@bot.command()
async def removeschedule(ctx, index: str = None):
    """Remove a schedule by its index."""
    if index is None:
        await ctx.send("❌ Please provide the schedule number to remove. Example: `!removeschedule 1`")
        return

    if not index.isdigit():
        await ctx.send("❌ Please provide a valid number for the schedule index.")
        return

    index = int(index)
    if index < 1 or index > len(schedules):
        await ctx.send(f"❌ Invalid index. Please choose a number between 1 and {len(schedules)}.")
        return

    removed = schedules.pop(index - 1)
    await ctx.send(f"✅ Removed schedule: `{removed['message']}`")

@bot.command()
async def clearschedules(ctx):
    """Clear all schedules."""
    schedules.clear()
    await ctx.send("🗑️ All schedules cleared.")

@bot.command()
async def help(ctx):
    """List all commands."""
    embed = discord.Embed(title="📖 Bot Commands", color=discord.Color.blue())
    embed.add_field(name="!addschedule #channel HH:MM days message", value="Add a schedule.\nExample: `!addschedule #general 21:30 monday,tuesday Hello!`", inline=False)
    embed.add_field(name="!listschedules", value="Show all schedules.", inline=False)
    embed.add_field(name="!removeschedule index", value="Remove schedule by index.", inline=False)
    embed.add_field(name="!clearschedules", value="Remove all schedules.", inline=False)
    embed.add_field(name="!help", value="Show this help message.", inline=False)
    await ctx.send(embed=embed)

# ---------------- BACKGROUND TASK ---------------- #
@tasks.loop(seconds=10)
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

            # Avoid sending multiple times in the same day
            if s["last_sent"] != current_date:
                ch = bot.get_channel(s["channel_id"])
                if ch:
                    await ch.send(s["message"])
                    s["last_sent"] = current_date

@schedule_checker.before_loop
async def before_schedule_checker():
    await bot.wait_until_ready()

# ---------------- RUN BOT ---------------- #
bot.run(TOKEN)
