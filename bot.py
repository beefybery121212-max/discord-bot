import discord
import os
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

SERVER_STRUCTURE = {
    "📢 INFORMATION": [
        "welcome",
        "rules",
        "announcements",
        "server-updates",
        "roles"
    ],
    "💬 COMMUNITY": [
        "general-chat",
        "garden-talk",
        "screenshots",
        "show-off-your-garden",
        "memes"
    ],
    "💰 TRADING": [
        "trade-chat",
        "buying",
        "selling",
        "price-checks",
        "trusted-traders"
    ],
    "🎮 GAME": [
        "tips-and-guides",
        "crop-values",
        "updates-and-leaks",
        "questions"
    ],
    "🎫 SUPPORT": [
        "create-ticket",
        "report-player",
        "appeals"
    ]
}

VOICE_CHANNELS = [
    "🌱 Garden VC 1",
    "🌱 Garden VC 2",
    "🎵 Chill VC",
    "Staff VC"
]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

@bot.tree.command(name="setup", description="Create Grow a Garden server structure")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Creating server structure...",
        ephemeral=True
    )
    guild = interaction.guild
    for category_name, channels in SERVER_STRUCTURE.items():
        category = discord.utils.get(
            guild.categories,
            name=category_name
        )
        if category is None:
            category = await guild.create_category(category_name)
        for channel_name in channels:
            existing = discord.utils.get(
                guild.text_channels,
                name=channel_name
            )
            if existing is None:
                await guild.create_text_channel(
                    channel_name,
                    category=category
            )
    voice_category = discord.utils.get(
        guild.categories,
        name="🔊 VOICE"
    )
    if voice_category is None:
        voice_category = await guild.create_category("🔊 VOICE")
    for vc_name in VOICE_CHANNELS:
        existing = discord.utils.get(
            guild.voice_channels,
            name=vc_name
        )
        if existing is None:
            await guild.create_voice_channel(
                vc_name,
                category=voice_category
            )
    await interaction.followup.send(
        "✅ Grow a Garden server setup complete!"
    )

bot.run(TOKEN)
