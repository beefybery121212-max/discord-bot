import discord
from discord.ext import commands

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setalert", help="Set a price alert.")
    async def set_alert(self, ctx):
        await ctx.send("Alert system coming soon!")

def setup(bot):
    bot.add_cog(Alerts(bot))
