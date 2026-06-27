import discord
from discord.ext import commands

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addrole", help="Add a role to a user.")
    @commands.has_permissions(manage_roles=True)
    async def add_role(self, ctx, member: discord.Member, *, role_name: str):
        await ctx.send(f"Role system coming soon!")

def setup(bot):
    bot.add_cog(Roles(bot))
