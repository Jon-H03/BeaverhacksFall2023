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
async def assignrole(ctx, user: discord.Member, role_name: str):
    """
    A bot command that allows the owner of the server to assign roles to users. This is useful
    to assign the teacher, TA(s), and students in their designated roles.

    Use the command like this: '!assignrole @User Teacher'
    """
    # Check if the command invoker is the server owner
    if ctx.author != ctx.guild.owner:
        await ctx.send("Sorry, only the server owner can use this command.")
        return

    # Check if user exists
    if not user:
        await ctx.send("User not found!")
        return

    # Fetch role by its name
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("Role not found!")
        return

    # Check if user already has the role
    if role in user.roles:
        await ctx.send(f"{user.name} already has the {role.name} role!")
        return

    # Check bot's permissions
    bot_member = ctx.guild.me
    if role >= bot_member.top_role:
        await ctx.send("Sorry, only the owner of the server can assign roles.")
        return

    # Define allowed roles that can be assigned
    allowed_roles = ["Student", "TA", "Teacher"]
    if role.name not in allowed_roles:
        await ctx.send("This role cannot be assigned.")
        return

    # Assign the role to the user
    await user.add_roles(role)
    await ctx.send(f"{role.name} has been assigned to {user.name}.")


bot.run(TOKEN)
