import discord
from discord.ext import commands
import os
from dotenv import load_dotenv


# Load the .env file
load_dotenv()

# Fetch the token from the environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """
    Simple event when bot first connects to notify the user.
    :return:
    """
    print(f'We have logged in as {bot.user}')


@bot.command()
async def hello(ctx):
    """
    Simple command to make sure bot is functioning as intended.
    :param ctx:
    :return:
    """
    await ctx.send('Hello, World!')


@bot.command()
@commands.is_owner()
async def assignrole(ctx, user: discord.Member, *, role_name: str):
    # Convert to lower case for case insensitivity.
    role_name_lower = role_name.lower()

    # Search for the role using the lowercase role name
    role = discord.utils.find(lambda r: r.name.lower() == role_name_lower, ctx.guild.roles)

    # if role does not exist in the server
    if not role:
        await ctx.send("Role not found!")
        return

    # If user already has specified role
    if role in user.roles:
        await ctx.send(f"{user.name} already has the {role.name} role!")
        return

    # Tell user they don't have permissions to use this command
    bot_member = ctx.guild.me
    if role >= bot_member.top_role:
        await ctx.send("You don't have the permissions to assign this role.")
        return

    # Make sure role exists
    allowed_roles = ["student", "ta", "teacher"]
    if role_name_lower not in allowed_roles:
        await ctx.send("This role cannot be assigned.")
        return

    # Add user to role in server
    await user.add_roles(role)
    await ctx.send(f"{role.name} has been assigned to {user.name}.")


bot.run(TOKEN)
