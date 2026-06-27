import discord
from discord.ext import commands

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="balance", help="Check your balance.")
    async def balance(self, ctx):
        await ctx.send(f"{ctx.author.mention}, your balance is 0 coins.")

def setup(bot):
    bot.add_cog(Economy(bot))
