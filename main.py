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
    print(f'We have logged in as {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello, World!')


bot.run(TOKEN)


