import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="warn", help="Warns a user.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await ctx.send(f"⚠️ {member.mention} has been warned. Reason: {reason}")

def setup(bot):
    bot.add_cog(Moderation(bot))
