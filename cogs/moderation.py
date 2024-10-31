import discord
from discord.ext import commands
import datetime

import json
def config():
    with open("config.json") as file:
        return json.load(file)
    
async def getUserId(ctx: commands.Context) -> int:
    user = ctx.message.content.split(" ")[1]

    if user.isdigit():
        return int(user)
    elif (user == "u") and ctx.message.reference: 
        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        return int(message.author.id)
    elif user.startswith("<@") and user.endswith(">"):
        return int(user[3:-1])
    else:
        return None

class Moderation(commands.Cog, name="moderation"):
    def __init__(self, client) -> None:
        self.client = client

    def is_staff():
        def predicate(ctx):
            roles = [role.id for role in ctx.author.roles]
            for perms in config()["permissions"]:
                if perms["staff"] is True and perms[ctx.command.name] is True:
                    if perms["roleid"] in roles:
                        return True
            raise commands.CheckFailure("You don't have the required permissions to run this command")
        return commands.check(predicate)
    
    def is_self():
        async def predicate(ctx: commands.Context):

            if ctx.author.id != await getUserId(ctx):
                return True
            raise commands.CheckFailure("You can't perform this action on yourself")
        return commands.check(predicate)
    
    def is_higher():
        async def predicate(ctx: commands.Context):
            author_roles = [role.position for role in ctx.author.roles]
            user_roles = [role.position for role in ctx.guild.get_member(await getUserId(ctx)).roles]

            highest_author_role = max(author_roles)
            highest_mentioned_role = max(user_roles)

            if highest_author_role > highest_mentioned_role:
                return True
            raise commands.CheckFailure("You cannot perform this action on a user with a higher or equal role")
        return commands.check(predicate)

    @commands.command(
        name="timeout",
        description="Put a user in timeout",
        aliases=["mute", "time", "t"]
    )
    @commands.bot_has_permissions(moderate_members=True)
    @is_staff()
    @is_self()
    @is_higher()
    async def timeout(self, ctx: commands.Context, member: str, time: str, *, reason: str = "No reason provided") -> None:
        member = ctx.guild.get_member(await getUserId(ctx))
        if member == ctx.author:
            await ctx.send("You can't timeout yourself", delete_after=3)

        if time.endswith("s"):
            time = datetime.timedelta(seconds=int(time[:-1]))
        elif time.endswith("m"):
            time = datetime.timedelta(minutes=int(time[:-1]))
        elif time.endswith("h"):
            time = datetime.timedelta(hours=int(time[:-1]))
        elif time.endswith("d"):
            time = datetime.timedelta(days=int(time[:-1]))
        elif time.isdigit():
            time = datetime.timedelta(minutes=int(time))
        else:
            await ctx.reply("Invalid time format")
            return
        
        if time and time.days > 27:
            await ctx.reply("You can't timeout for more than 27 days")
            return
        
        embed = discord.Embed(
            title="User Timed Out",
            color=discord.Color.red()
        )
        embed.add_field(name="User", value=member.mention, inline=False)
        embed.add_field(name="Duration", value=f"{int(time.total_seconds() // 60)} minutes", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Moderator: {ctx.author.name}")

        if time:
            time = discord.utils.utcnow() + time
            self.client.database.infractions.insert_one({
                "guild_id": ctx.message.guild.id,
                "user_id": member.id,
                "user_name": member.name,
                "mod_id": ctx.message.author.id,
                "mod_name": ctx.message.author.name,
                "reason": reason,
                "created_at": datetime.datetime.now()
            })

        await member.timeout(time, reason=reason)
        await ctx.message.delete()

        await ctx.send(embed=embed)

    @commands.command(
        name="infractions",
        description="Get the infractions of a user",
        aliases=["infraction", "infs"]
    )
    @commands.bot_has_permissions(send_messages=True)
    async def infractions(self, ctx: commands.Context, member: str = None) -> None:
        if not member: member = ctx.author.id
        member = ctx.guild.get_member(await getUserId(ctx))
  
        infractions = self.client.database.infractions.find({
            "guild_id": ctx.guild.id,
            "user_id": member.id
        })

        if self.client.database.infractions.count_documents({
            "guild_id": ctx.guild.id,
            "user_id": member.id
        }) == 0:
            await ctx.send(f"**{member.name}** has no infractions")
            return

        embed = discord.Embed(
            title=f"Infractions for {member.name}",
            color=discord.Color.red()
        )

        infraction_number = 0
        for infraction in infractions:
            infraction_number += 1
            expires_in = (infraction["created_at"] + datetime.timedelta(days=60)) - datetime.datetime.now()
            embed.add_field(
                name=f"Infraction {infraction_number} (Expires In {expires_in.days} days)",
                value=f"**Reason:** {infraction['reason']}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(
        name="clear-infraction",
        description="Clear an infraction from a user",
        aliases=["clearinf", "del-infraction", "delinf"]
    )
    @is_staff()
    @is_self()
    async def clear_infraction(self, ctx: commands.Context, member: str, infraction_number: int) -> None:
        member = ctx.guild.get_member(await getUserId(ctx))
        infractions = self.client.database.infractions.find({
            "guild_id": ctx.guild.id,
            "user_id": member.id
        })

        if self.client.database.infractions.count_documents({
            "guild_id": ctx.guild.id,
            "user_id": member.id
        }) == 0:
            await ctx.send(f"**{member.name}** has no infractions")
            return

        infraction_number = 0
        for infraction in infractions:
            infraction_number += 1
            if infraction_number == infraction_number:
                self.client.database.infractions.delete_one({
                    "guild_id": ctx.guild.id,
                    "user_id": member.id,
                    "reason": infraction["reason"]
                })
                await ctx.send(f"Infraction {infraction_number} has been cleared")

    @commands.command(
        name="ban",
        description="Ban a user from the server"
    )
    @commands.bot_has_permissions(ban_members=True)
    @is_staff()
    @is_self()
    @is_higher()
    async def ban(self, ctx: commands.Context, user: str, *, reason: str = "No reason provided") -> None:
        user = ctx.guild.get_member(await getUserId(ctx))
        if user == ctx.author:
            await ctx.send("You can't ban yourself", delete_after=3)

        await ctx.message.delete()

        ban_entry = await ctx.guild.fetch_ban(user)
        if ban_entry:
            await ctx.send(f"<@{ctx.author.id}> **{user.name}** is already banned", delete_after=3)
        else:
            await ctx.guild.ban(user=user, delete_message_days=1, reason=reason)
            await ctx.send(f"<@{ctx.author.id}> **{user.name}** has been banned", delete_after=3)

    @commands.command(
        name="unban",
        description="Unban a user from the server"
    )
    @commands.bot_has_permissions(ban_members=True)
    @is_staff()
    @is_self()
    async def unban(self, ctx: commands.Context, user: discord.User) -> None:
        await ctx.message.delete()
        await ctx.guild.unban(user.id)
        await ctx.send(f"<@{ctx.author.id}> **{user.name}** has been unbanned", delete_after=3)

async def setup(client) -> None:
    await client.add_cog(Moderation(client))