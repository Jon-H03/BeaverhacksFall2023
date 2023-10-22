import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import datetime
import asyncio
import csv

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
    """
    print(f'We have logged in as {bot.user}')


@bot.command()
async def hello(ctx):
    """
    Simple command to make sure bot is functioning as intended.


    """
    await ctx.send('Hello, World!')


@bot.command()
@commands.has_any_role('Teacher')
async def assignrole(ctx, user: discord.Member, *, role_name: str):
    """
    Allows server owner or a 'Teacher' to assign roles to other teachers, TAs, and students.
    It is case-insensitive so it will work regardless of how "Teacher", "TA", and "Student" when
    using the command.

    To use this command: "!assignrole @User student"
    """
    # Make sure person using command is the server owner or has role 'Teacher'
    if not ctx.author == ctx.guild.owner and not discord.utils.get(ctx.author.roles, name="Teacher"):
        await ctx.send("You don't have permission to use this command.")
        return

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


@bot.command()
@commands.has_any_role('Teacher')
async def unassignrole(ctx, user: discord.Member, *, role_name: str):
    """
    Allows server owner or a 'Teacher' to unassign roles to other teachers, TAs, and students.
    It pretty much works the same way as !assignrole except opposite.

    To use this command: "!unassignrole @User student"
    """
    # Make sure person using command is the server owner or has role 'Teacher'
    if not ctx.author == ctx.guild.owner and not discord.utils.get(ctx.author.roles, name="Teacher"):
        await ctx.send("You don't have permission to use this command.")
        return

    # Convert to lower case for case insensitivity.
    role_name_lower = role_name.lower()

    # Search for the role using the lowercase role name
    role = discord.utils.find(lambda r: r.name.lower() == role_name_lower, ctx.guild.roles)

    # if role does not exist in the server
    if not role:
        await ctx.send("Role not found!")
        return

    # If user doesn't have the specified role
    if role not in user.roles:
        await ctx.send(f"{user.name} doesn't have the {role.name} role!")
        return

    # Tell user they don't have permissions to use this command
    bot_member = ctx.guild.me
    if role >= bot_member.top_role:
        await ctx.send("You don't have the permissions to unassign this role.")
        return

    # Make sure role exists
    allowed_roles = ["student", "ta", "teacher"]
    if role_name_lower not in allowed_roles:
        await ctx.send("This role cannot be unassigned.")
        return

    # Remove the role from the user in the server
    await user.remove_roles(role)
    await ctx.send(f"{role.name} has been unassigned from {user.name}.")


# The attendance records, stored by date
attendance = {}


@bot.command()
@commands.has_any_role('Teacher', 'TA')
async def start_attendance(ctx, duration: int = 5):  # default is 5 seconds (for testing purposes)
    """
    A command that allows teachers and TAs the ability to start an attendance check for
    the current date. The teacher can specify the amount of times in seconds that they wish to keep
    the check open for.

    To start use this command: '!start_attendance (time)', but the time will have a default value of 5 mins.
    """
    message = await ctx.send("React to this message to mark your attendance for today!")
    await message.add_reaction("✅")

    # Get all members with the "Student" role
    student_role = discord.utils.get(ctx.guild.roles, name="Student")
    students = [member.name for member in student_role.members]

    # Initialize the attendance for today's date
    today = datetime.date.today()
    if today not in attendance:
        # Initialize every student's attendance to False
        attendance[today] = {student: False for student in students}

    # Wait for the specified duration
    await asyncio.sleep(duration)

    # After the duration is over, send the closing message
    await ctx.send("Attendance has been closed!")


@bot.event
async def on_reaction_add(reaction, user):
    """
    Bot event that checks which users reacted to the attendance message.
    """
    if user == bot.user:
        return
    if reaction.emoji == "✅":
        today = datetime.date.today()
        # Check if the reacting student's name is in the attendance record for today
        if today in attendance and user.name in attendance[today]:
            attendance[today][user.name] = True


@bot.command()
@commands.has_any_role('Teacher', 'TA')
async def export_attendance(ctx):
    """
    Bot command that will export all current attendance data to a csv for download. This is perfect as there's no
    current database and no intention to add one. So the teachers can take with them their attendance records everyday.

    To use this command: '!export_attendance'
    """
    if not attendance:
        await ctx.send("No attendance data available.")
        return

    # Name of the temporary CSV file
    filename = "attendance_records.csv"

    # Writing to the CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow(["Date", "Member Username", "Present"])

        # Write the data
        for date, members in attendance.items():
            for member_name, was_present in members.items():
                writer.writerow([date, member_name, was_present])

    # Send the CSV file in the channel
    with open(filename, 'rb') as file:
        await ctx.send(file=discord.File(file, filename))

    # Optionally, remove the temporary file after sending
    os.remove(filename)
##

# Teacher can post assignments
assignments = {}


@bot.command()
@commands.has_any_role('Teacher', 'TA')
async def post_assignment(ctx, title: str, description: str, due_date: str):
    """
    A bot command that allows teachers/TAs to create an embed homework assignment on an assignments page.

    To use this command: '!post_assignment {assignment name} {description} {due date}'
    """
    # Create an embed for the assignment
    embed = discord.Embed(title=f"📚 Assignment: {title}", description=description + "\n\n", color=0x00ff00)
    embed.add_field(name="📅 Due Date", value=due_date, inline=True)

    # Check if there's an 'assignments' channel, if not, create one
    assignments_channel = discord.utils.get(ctx.guild.channels, name='assignments')
    if not assignments_channel:
        bot_member = ctx.guild.me  # Get the bot member object
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            bot_member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = discord.utils.get(ctx.guild.categories, name="Text Channels")
        assignments_channel = await ctx.guild.create_text_channel('assignments', overwrites=overwrites,
                                                                  category=category)

    await assignments_channel.send(embed=embed)

    # Store the assignment details in the assignments dictionary
    assignments[title] = {"description": description, "due_date": due_date}


# Allow teacher to schedule announcements.

@bot.command()
@commands.has_any_role('Teacher', 'TA')
async def announcement(ctx, title: str, description: str, date: str):
    """
    A bot command that allows teacher/TAs to create an embed announcement in the announcements channel.

    To use this command: '!post_assignment {announcement name} {description} {date}'
    """
    # Check if there's an 'announcements' channel, if not, create one
    announcements_channel = discord.utils.get(ctx.guild.channels, name='announcements')
    bot_member = ctx.guild.me
    if not announcements_channel:
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            bot_member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Get the category of the default "general" channel
        general_channel = discord.utils.get(ctx.guild.text_channels, name='general')
        if general_channel:
            category = general_channel.category
        else:
            # If for some reason "general" doesn't exist, create a new "text channels" category
            category = await ctx.guild.create_category(name='text channels')

        announcements_channel = await ctx.guild.create_text_channel('announcements', overwrites=overwrites,
                                                                    category=category)

    # Create and send the embed message
    embed = discord.Embed(title=title, description=description, color=0x3498db)
    embed.add_field(name="Date", value=date)
    await announcements_channel.send(embed=embed)

    await ctx.send(f"Announcement for {date} set. Feel free to review in {announcements_channel.mention}.")


# Allow teacher to create special groups in server
@bot.command()
@commands.has_any_role('Teacher', 'TA')
async def breakout(ctx, channel_name: str, *members: discord.Member):
    """
    A bot command that allows teachers/TAs to create a breakout room with specified students.

    To use this command: '!create_breakout {channel name} {@student1} {@student2} ...'
    """
    # Check if the channel already exists
    existing_channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    if existing_channel:
        await ctx.send(f"The channel `{channel_name}` already exists.")
        return

    # Set permissions
    overwrites = {
        # No one can access
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),

        # Bot can access
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
    }
    # Specified members can access
    for member in members:
        overwrites[member] = discord.PermissionOverwrite(read_messages=True)

    # Teachers and TAs can access
    teacher_role = discord.utils.get(ctx.guild.roles, name="Teacher")
    ta_role = discord.utils.get(ctx.guild.roles, name="TA")
    overwrites[teacher_role] = discord.PermissionOverwrite(read_messages=True)
    overwrites[ta_role] = discord.PermissionOverwrite(read_messages=True)

    # Check if "breakouts" category exists, if not create one
    breakouts_category = discord.utils.get(ctx.guild.categories, name="breakouts")
    if not breakouts_category:
        breakouts_category = await ctx.guild.create_category("breakouts")

    # Create the channel within the "breakouts" category
    try:
        await ctx.guild.create_text_channel(channel_name, overwrites=overwrites, category=breakouts_category)
        await ctx.send(f"Channel `{channel_name}` created successfully in 'breakouts'.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to create channels.")
    except discord.HTTPException:
        await ctx.send("Failed to create channel. Please try again.")


# Q & A feature where students can ask and vote on questions, and teachers/TAs can answer the most relevant ones.


# Can create feedback so teachers can get opinions from students


# Quiz/poll functionality



bot.run(TOKEN)
