import discord
from discord.ext import commands
import sqlite3

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="createticket", help="Creates a support ticket.")
    @commands.guild_only()
    async def create_ticket(self, ctx):
        await ctx.send("Ticket system coming soon!")

def setup(bot):
    bot.add_cog(Tickets(bot))
