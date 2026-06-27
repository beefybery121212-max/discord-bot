import discord
from discord.ext import commands
import sqlite3

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup", help="Sets up the server with channels and roles.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def setup(self, ctx):
        guild = ctx.guild
        
        # Create categories and channels
        categories = {
            "General": ["general", "announcements"],
            "Garden": ["garden-chat", "garden-tips"],
            "Support": ["support", "bug-reports"],
            "Voice": []
        }
        
        created_channels = []
        for category_name, channels in categories.items():
            category = await guild.create_category(category_name)
            for channel_name in channels:
                channel = await guild.create_text_channel(channel_name, category=category)
                created_channels.append(channel.mention)
            
            # Create voice channel in Voice category
            if category_name == "Voice":
                await guild.create_voice_channel("General Voice", category=category)
        
        embed = discord.Embed(title="✅ Server Setup Complete!", color=discord.Color.green())
        embed.add_field(name="Created Channels", value="\n".join(created_channels) if created_channels else "None", inline=False)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Setup(bot))
