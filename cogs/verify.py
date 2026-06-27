import discord
from discord.ext import commands

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="verify", help="Verify your account.")
    async def verify(self, ctx):
        await ctx.send("Verification system coming soon!")

def setup(bot):
    bot.add_cog(Verify(bot))
