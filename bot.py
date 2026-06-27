import discord
from discord.ext import commands
import sqlite3
import json
import os
import asyncio
from datetime import datetime, timedelta

# --- Configuration ---
CONFIG_FILE = "config.json"
DATABASE_FILE = "grow_garden.db"

# --- Database Setup ---
def setup_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Tickets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_id INTEGER UNIQUE NOT NULL,
            status TEXT DEFAULT 'open'
        )
    ''')

    # Warnings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            warning_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Stock Alerts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_symbol TEXT NOT NULL,
            price_threshold REAL,
            is_rare INTEGER DEFAULT 0, -- 0 for normal, 1 for rare
            channel_id INTEGER,
            role_id INTEGER
        )
    ''')

    # User Data (for economy/rewards)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_daily DATETIME,
            work_cooldown DATETIME
        )
    ''')

    # Giveaways
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            giveaway_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE NOT NULL,
            channel_id INTEGER NOT NULL,
            end_time DATETIME NOT NULL,
            winners INTEGER NOT NULL,
            prize TEXT NOT NULL,
            entries TEXT -- Stores entries as JSON string of user IDs
        )
    ''')

    # Server Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_settings (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT DEFAULT '!',
            ticket_category_id INTEGER,
            logging_channel_id INTEGER,
            member_role_id INTEGER,
            bot_role_id INTEGER,
            admin_role_id INTEGER,
            mod_role_id INTEGER,
            vip_role_id INTEGER,
            garden_expert_role_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()

# --- Load Configuration ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        print(f"Configuration file '{CONFIG_FILE}' not found. Please create it.")
        return None

# --- Bot Setup ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Helper Functions ---
def get_db_connection():
    return sqlite3.connect(DATABASE_FILE)

async def send_embed(ctx, title, description, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

async def create_ticket_channel(guild, user, category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_id FROM tickets WHERE user_id = ? AND status = 'open'", (user.id,))
    existing_ticket = cursor.fetchone()
    if existing_ticket:
        await user.send("You already have an open ticket.")
        return

    ticket_category = guild.get_channel(category_id)
    if not ticket_category:
        await user.send("Ticket category not found. Please configure it.")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_history=True),
        guild.get_role(bot.config.get('admin_role_id')): discord.PermissionOverwrite(read_messages=True, send_messages=True, read_history=True),
        guild.get_role(bot.config.get('mod_role_id')): discord.PermissionOverwrite(read_messages=True, send_messages=True, read_history=True),
    }

    channel_name = f"ticket-{user.name}-{user.discriminator}"
    try:
        ticket_channel = await guild.create_text_channel(channel_name, category=ticket_category, overwrites=overwrites)
        cursor.execute("INSERT INTO tickets (user_id, channel_id) VALUES (?, ?)", (user.id, ticket_channel.id))
        conn.commit()
        await ticket_channel.send(f"Welcome {user.mention}! Please describe your issue. Staff will be with you shortly.")
        await ticket_channel.send("Use `/close` to close this ticket.")
        return ticket_channel
    except Exception as e:
        print(f"Error creating ticket channel: {e}")
        await user.send("An error occurred while creating your ticket.")
    finally:
        conn.close()

async def close_ticket_channel(channel):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel.id,))
    conn.commit()
    conn.close()
    await channel.delete()

async def add_auto_roles(member):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT member_role_id, bot_role_id, admin_role_id, mod_role_id, vip_role_id, garden_expert_role_id FROM server_settings WHERE guild_id = ?", (member.guild.id,))
    roles = cursor.fetchone()
    conn.close()

    if not roles:
        return

    role_ids = {
        "member": roles[0],
        "bot": roles[1],
        "admin": roles[2],
        "mod": roles[3],
        "vip": roles[4],
        "garden_expert": roles[5],
    }

    assigned_roles = []
    if member.bot and role_ids["bot"]:
        role = member.guild.get_role(role_ids["bot"])
        if role:
            assigned_roles.append(role)
    elif not member.bot:
        if role_ids["member"]:
            role = member.guild.get_role(role_ids["member"])
            if role:
                assigned_roles.append(role)

    # Add other roles based on conditions (e.g., VIP status, specific commands)
    # This is a simplified example. Real implementation might check user data or external factors.

    if assigned_roles:
        try:
            await member.add_roles(*assigned_roles)
        except discord.Forbidden:
            print(f"Missing permissions to add roles to {member.display_name} in {member.guild.name}")
        except Exception as e:
            print(f"Error adding roles to {member.display_name}: {e}")

# --- Bot Events ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    setup_database()
    bot.config = load_config()
    if not bot.config:
        print("Bot cannot start without configuration.")
        await bot.close()
        return

    # Load Cogs (for better organization)
    cogs_to_load = [
        "tickets",
        "moderation",
        "setup",
        "stocks",
        "alerts",
        "giveaways",
        "economy",
        "verify",
        "logging",
        "roles"
    ]
    for cog in cogs_to_load:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"Loaded cog: {cog}")
        except Exception as e:
            print(f"Failed to load cog {cog}: {e}")

    # Start background tasks
    bot.loop.create_task(check_giveaway_deadlines())
    bot.loop.create_task(check_stock_alerts())

@bot.event
async def on_member_join(member):
    await add_auto_roles(member)
    # Send welcome message if configured
    welcome_channel_id = bot.config.get("welcome_channel_id")
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            await channel.send(f"Welcome {member.mention} to the server! 🎉 Please check out the rules and get started.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await send_embed(ctx, "Command Not Found", "The command you entered does not exist.", discord.Color.red())
    elif isinstance(error, commands.MissingRequiredArgument):
        await send_embed(ctx, "Missing Argument", f"You are missing a required argument: `{error.param.name}`", discord.Color.red())
    elif isinstance(error, commands.BadArgument):
        await send_embed(ctx, "Bad Argument", "The argument you provided is invalid.", discord.Color.red())
    elif isinstance(error, commands.MissingPermissions):
        await send_embed(ctx, "Permissions Error", "You do not have the necessary permissions to use this command.", discord.Color.red())
    elif isinstance(error, commands.BotMissingPermissions):
        await send_embed(ctx, "Bot Permissions Error", "The bot is missing the necessary permissions to perform this action.", discord.Color.red())
    elif isinstance(error, commands.CheckFailure):
        await send_embed(ctx, "Check Failed", "You failed a check to use this command.", discord.Color.red())
    else:
        print(f"Unhandled command error: {error}")
        await send_embed(ctx, "An Error Occurred", "An unexpected error occurred. Please try again later.", discord.Color.red())

# --- Core Commands (Example) ---
@bot.command(name="ping", help="Checks the bot's latency.")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await send_embed(ctx, "Pong!", f"{latency}ms", discord.Color.green())

@bot.command(name="server", help="Shows server information.")
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Information", color=guild.owner.color if guild.owner else discord.Color.blue())
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="help", help="Shows all available commands or help for a specific command.")
async def help_command(ctx, *, command_name: str = None):
    if command_name:
        command = bot.get_command(command_name)
        if command:
            embed = discord.Embed(title=f"Help: {command.name}", description=command.help, color=discord.Color.blue())
            embed.add_field(name="Usage", value=f"`{bot.command_prefix}{command.signature}`", inline=False)
            await ctx.send(embed=embed)
        else:
            await send_embed(ctx, "Command Not Found", f"Could not find the command `{command_name}`.", discord.Color.red())
    else:
        embed = discord.Embed(title="Bot Commands", description="Here's a list of commands you can use:", color=discord.Color.purple())
        for command in bot.commands:
            if not command.hidden:
                embed.add_field(name=command.name, value=command.help or "No description provided.", inline=True)
        await ctx.send(embed=embed)

# --- Placeholder for Cogs ---
# The actual commands for tickets, moderation, setup, etc., would be in separate cog files (cogs/tickets.py, etc.)

# Example of how a cog would be structured:
# Assume 'cogs/tickets.py' exists with the following content:

"""
# cogs/tickets.py
import discord
from discord.ext import commands
import sqlite3

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        return sqlite3.connect('grow_garden.db')

    @commands.command(name="createticket", help="Creates a new support ticket.")
    @commands.guild_only()
    async def create_ticket(self, ctx):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticket_category_id FROM server_settings WHERE guild_id = ?", (ctx.guild.id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            await ctx.send("Ticket system not configured for this server.")
            return

        category_id = result[0]
        ticket_channel = await self.bot.loop.run_in_executor(None, lambda: self.bot.get_channel(category_id)) # Run in executor for blocking IO
        if not ticket_channel:
            await ctx.send("Ticket category not found. Please ensure it's set up correctly.")
            return

        # Check if user already has an open ticket (simplified, actual check in bot.py's helper)
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id FROM tickets WHERE user_id = ? AND status = 'open'", (ctx.author.id,))
        existing_ticket = cursor.fetchone()
        conn.close()

        if existing_ticket:
            await ctx.send("You already have an open ticket. Please check your channels.")
            return

        await self.bot.loop.run_in_executor(None, lambda: self.bot.create_ticket_channel(ctx.guild, ctx.author, category_id)) # Run in executor
        await ctx.send("Your ticket has been created. Please check the new channel.")

    @commands.command(name="closeticket", help="Closes the current ticket.")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True) # Or a specific ticket manager role
    async def close_ticket(self, ctx):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM tickets WHERE channel_id = ? AND status = 'open'", (ctx.channel.id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            await ctx.send("This is not a ticket channel.")
            return

        await self.bot.loop.run_in_executor(None, lambda: self.bot.close_ticket_channel(ctx.channel)) # Run in executor
        await ctx.send("Ticket closed.")

    @commands.command(name="ticketlogs", help="Shows logs for a specific ticket (requires ticket ID).")
    async def ticket_logs(self, ctx, ticket_id: int):
        # This would involve fetching logs from a dedicated logging channel or database
        await ctx.send("Ticket log functionality is still under development.")


def setup(bot):
    bot.add_cog(Tickets(bot))
"""

# --- Background Tasks ---
async def check_giveaway_deadlines():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT giveaway_id, message_id, channel_id, end_time, winners, prize FROM giveaways WHERE end_time <= ?", (now,))
        expired_giveaways = cursor.fetchall()
        conn.close()

        for giveaway in expired_giveaways:
            giveaway_id, message_id, channel_id, end_time, winners, prize = giveaway
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(message_id)
                    # Logic to pick winners and announce
                    await channel.send(f"🎉 Giveaway for '{prize}' has ended!")
                    # ... (winner picking logic)
                except discord.NotFound:
                    print(f"Giveaway message not found for ID: {message_id}")
                except Exception as e:
                    print(f"Error processing expired giveaway {giveaway_id}: {e}")

            # Remove from database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM giveaways WHERE giveaway_id = ?", (giveaway_id,))
            conn.commit()
            conn.close()

        await asyncio.sleep(60) # Check every minute

async def check_stock_alerts():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT alert_id, stock_symbol, price_threshold, is_rare, channel_id, role_id FROM stock_alerts")
        alerts = cursor.fetchall()
        conn.close()

        for alert in alerts:
            alert_id, stock_symbol, price_threshold, is_rare, channel_id, role_id = alert
            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            # --- Placeholder for actual stock data fetching ---
            # In a real bot, you would use an API like Alpha Vantage, Yahoo Finance, etc.
            # For this example, we'll simulate a prediction.
            stock_data = await get_simulated_stock_data(stock_symbol)

            if stock_data:
                current_price = stock_data["price"]
                prediction = stock_data["prediction"]
                likelihood = stock_data["likelihood"]
                item_name = stock_data.get("item_name", stock_symbol) # For rare items

                triggered = False
                if price_threshold is not None and current_price >= price_threshold:
                    triggered = True
                elif is_rare and prediction == "Likely" or prediction == "Very Likely": # Example for rare item alerts
                    triggered = True

                if triggered:
                    alert_message = ""
                    if is_rare:
                        alert_message = f"🌟 **Rare Seed in stock!**\n\n**Item:** {item_name}\n**Time:** {now.strftime('%I:%M %p')}"
                        role_to_ping = discord.utils.get(channel.guild.roles, name="@RareStock") # Example role name
                        if role_to_ping:
                            alert_message = f"{role_to_ping.mention}\n{alert_message}"
                    else:
                        alert_message = f"🚨 **Alert for {stock_symbol}**\n\nCurrent Price: ${current_price:.2f}\nPrediction: {prediction} ({likelihood})"
                        if role_id:
                            role = channel.guild.get_role(role_id)
                            if role:
                                alert_message = f"{role.mention}\n{alert_message}"

                    await channel.send(alert_message)

                    # Remove the alert after it's triggered, or implement a mechanism to re-trigger
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM stock_alerts WHERE alert_id = ?", (alert_id,))
                    conn.commit()
                    conn.close()

        await asyncio.sleep(30) # Check every 30 seconds

async def get_simulated_stock_data(symbol):
    # This is a placeholder for actual stock data fetching and prediction.
    # In a real bot, you'd integrate with a financial API.
    await asyncio.sleep(0.5) # Simulate API call delay
    prices = {
        "CARROT": {"price": 1.50, "prediction": "Likely", "likelihood": "⭐⭐⭐", "item_name": "Carrot"},
        "STRAWBERRY": {"price": 3.20, "prediction": "Very Likely", "likelihood": "⭐⭐⭐⭐", "item_name": "Strawberry"},
        "CORN": {"price": 0.80, "prediction": "Low Chance", "likelihood": "⭐", "item_name": "Corn"},
        "GOLDENPUMPKIN": {"price": 100.00, "prediction": "Likely", "likelihood": "⭐⭐⭐", "item_name": "Golden Pumpkin"} # Example rare item
    }
    symbol_upper = symbol.upper()
    if symbol_upper in prices:
        data = prices[symbol_upper]
        return {
            "price": data["price"] + (random.uniform(-0.5, 0.5) if symbol_upper != "GOLDENPUMPKIN" else random.uniform(-20, 20)), # Add some volatility
            "prediction": data["prediction"],
            "likelihood": data["likelihood"],
            "item_name": data.get("item_name")
        }
    else:
        # Simulate a generic stock if not in our predefined list
        return {
            "price": random.uniform(10, 1000),
            "prediction": random.choice(["Likely", "Unlikely", "Neutral"]),
            "likelihood": "⭐" * random.randint(1, 5)
        }

import random # Import random for simulation

# --- Run the Bot ---
if __name__ == "__main__":
    if bot.config:
        bot.run(bot.config['token'])
    else:
        print("Bot could not start due to missing configuration.")
