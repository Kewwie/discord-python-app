import discord
from discord import app_commands
from discord.ext import commands

maxPremissionLevel = 1000

async def getId(target) -> int:
    if target.isdigit():
        return int(target)
    elif target.startswith("<@&") and target.endswith(">"):
        return int(target[4:-1])
    elif target.startswith("<@") and target.endswith(">"):
        return int(target[3:-1])
    else:
        return None

class Config(commands.Cog, name="config"):
    def __init__(self, client) -> None:
        self.client = client

    @commands.group(
        name="permissions",
        description="Manage the permissions of a user or role",
        aliases=["perms"],
        invoke_without_command=True
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(administrator=True)
    async def permissions(self, ctx: commands.Context) -> None:
        await ctx.reply("Please specify a subcommand: set, view, or list")

    @permissions.command(
        name="set",
        description="Set permissions for a user or role"
    )
    async def set(self, ctx: commands.Context, target: str = None, level: int = None) -> None:
        if target is None or level is None:
            await ctx.reply("Please specify a target and level")
            return
        print(target)
        targetId = await getId(target)
        print(targetId)
        if targetId is None:
            await ctx.reply("Invalid target")
            return

        if level > maxPremissionLevel:
            await ctx.reply("Invalid permission level, must be below 1000")
            return
        
        await ctx.reply(f"Set permission level {level} for {targetId}")
        self.client.database.permissions.insert_one({
            "guild_id": ctx.message.guild.id,
            "id": targetId,
            "level": level
        })


    @permissions.command(
        name="view",
        description="View a user or roles permissions"
    )
    async def permissions_view(self, ctx: commands.Context, target: str = None) -> None:
        if target is None:
            await ctx.reply("Please specify a target")
            return
        
        targetId = await getId(target)

        if targetId is None:
            await ctx.reply("Invalid target")
            return
        
        targetPermissions = self.client.database.permissions.find_one({
            "guild_id": ctx.message.guild.id,
            "id": targetId
        })
        print(targetPermissions)

        if targetPermissions is None:
            await ctx.reply("No permissions found for this user or role")
            return
        
        await ctx.reply(f"Permissions for {targetId}: {targetPermissions['level']}")

    @permissions.command(
        name="list",
        description="List all permissions"
    )
    async def list(self, ctx: commands.Context) -> None:
        permissions = self.client.database.permissions.find({
            "guild_id": ctx.message.guild.id
        })

        if permissions.count() == 0:
            await ctx.reply("No permissions found")
            return

        for permission in permissions:
            print(permission)


async def setup(client) -> None:
    await client.add_cog(Config(client))