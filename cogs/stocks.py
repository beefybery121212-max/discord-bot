import discord
from discord.ext import commands

class Stocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="stock", help="Check stock prices.")
    async def stock(self, ctx, symbol: str):
        await ctx.send(f"Stock info for {symbol} coming soon!")

def setup(bot):
    bot.add_cog(Stocks(bot))
