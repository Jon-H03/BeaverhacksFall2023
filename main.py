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

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


@bot.event
async def on_ready():
    """
    Simple event when bot first connects to notify the client.
    """
    print(f'We have logged in as {bot.user}')


@bot.command()
async def hello(ctx):
    """
    Simple command to make bot give welcome message.

    Usage: `!hello`
    """
    await ctx.send("Hello, I'm Teacher's Pet, and you can count on me to assist with performing classroom functions and keeping things orderly.\n\n"
                   "To see a list of my possible commands, type `!help`.")


@bot.event
async def on_command_error(ctx, error):
    """
    The event triggered when an error is raised while invoking a command.
    """
    # Get the actual cause of error
    error = getattr(error, 'original', error)

    # Anything in `ignored` will return and prevent anything happening.
    ignored = commands.CommandNotFound
    if isinstance(error, ignored):
        await ctx.send('Command not recognized, to see a list of commands type `!help`')
        return


@bot.command()
async def help(ctx):
    """
    Displays a list of all commands and their descriptions.

    Usage: `!help`
    """
    # Using the predefined order for commands.
    command_order = ["help", "hello", "assign_role", "unassign_role",
                     "start_attendance", "export_attendance", "post_assignment", "announcement",
                     "breakout", "ask", "feedback", "quiz"]

    # Ensure all commands are present in the order list, if not add them to the end.
    for cmd in bot.commands:
        if cmd.name not in command_order:
            command_order.append(cmd.name)

    embed = discord.Embed(title="📔 Bot Commands", description="List of available commands", color=0x00ff00)

    # Display commands in the predefined order.
    for cmd_name in command_order:
        cmd = bot.get_command(cmd_name)
        if cmd:  # This check ensures that the command exists.
            command_info = cmd.help or "No description"
            embed.add_field(name=f"🔴 !{cmd.name}", value=command_info, inline=False)

    await ctx.send(embed=embed)


@bot.command()
@commands.has_any_role('Teacher')
async def assign_role(ctx, user: discord.Member, *, role_name: str):
    """
    Allows server owner or a 'Teacher' to assign roles to other teachers, TAs, and students. It is case-insensitive so it will work regardless of how "Teacher", "TA", and "Student" when
    using the command.

    Usage: `!assign_role @User student`
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
async def unassign_role(ctx, user: discord.Member, *, role_name: str):
    """
    Allows server owner or a 'Teacher' to unassign roles to other teachers, TAs, and students. It pretty much works the same way as !assign_role except opposite.

    Usage: `!unassign_role @User student`
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
    A command that allows teachers and TAs the ability to start an attendance check for the current date. The teacher can specify the amount of time in minutes that they wish to keep the check open for.

    Usage: `!start_attendance (time)`
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
    await asyncio.sleep(duration*60)

    # After the duration is over, send the closing message
    await ctx.send("Attendance has been closed!")


@bot.event
async def on_reaction_add(reaction, user):
    """
    Bot event that checks which users reacted to the attendance message and changes their value to "True" in the attendance.
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
    Bot command that will export all current attendance data to a csv for download.

    Usage: `!export_attendance`
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

    Usage: `!post_assignment {assignment name} {description} {due date}`
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

    Usage: `!post_assignment {announcement name} {description} {date}`
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

    Usage: `!create_breakout {channel name} {@student1} {@student2} ...`
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
@bot.command()
async def ask(ctx, *, question: str):
    """
    Allows students to ask questions and creates an embed and thread for them.

    Usage: `!ask {question}`
    """
    embed = discord.Embed(title="❓ New Question", description=question, color=0xf1c40f)
    embed.set_footer(text=f"Asked by {ctx.author.name}")
    message = await ctx.send(embed=embed)

    # Create a thread for this question. The thread lasts for 1 day by default.
    await message.create_thread(name=f"Q from {ctx.author.name}", auto_archive_duration=1440)

# Can create feedback so teachers can get opinions from students
@bot.command()
async def feedback(ctx):
    """
    Create a feedback poll for teachers, so they can get opinions from students.

    Usage: `!feedback`.
    """

    question = "How was today's lecture?"
    options = ["Great", "Good", "Okay", "Bad"][::-1]
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']

    embed = discord.Embed(title="📊 Feedback Poll", description=question, color=0x3498db)
    for i, option in enumerate(options):
        embed.add_field(name=reactions[i], value=option, inline=False)

    poll_message = await ctx.send(embed=embed)
    for i, _ in enumerate(options):
        await poll_message.add_reaction(reactions[i])

    # Create a thread for detailed feedback
    thread = await poll_message.create_thread(name="Detailed Feedback", auto_archive_duration=1440)  # 24 hours before auto-archiving

    # Embed for feedback
    feedback_embed = discord.Embed(title="🌟 Detailed Feedback", description="✨ Share what you think went well... and \n 🌱 what could be improved.", color=0x2ecc71)
    await thread.send(embed=feedback_embed)


# Quiz/poll functionality
@bot.command()
@commands.has_any_role('Teacher', 'TA')  # Only Teachers and TAs can create quizzes/polls
async def quiz(ctx, duration: int, question: str, *options: str):
    """
    Create a quiz/poll with a question and multiple choice answers. Duration is in minutes.

    Usage: `!quiz {minutes} {question} {answer1} {answer2} ...`
    """

    # Make sure there are at least two options and not more than 5
    if not (2 <= len(options) <= 5):
        await ctx.send("You must provide between 2 and 5 options for the quiz/poll.")
        return

    reactions = ['🇦', '🇧', '🇨', '🇩', '🇪']

    # Formatting options for the embed
    formatted_options = '\n'.join([f"{reactions[i]}: {option}\n" for i, option in enumerate(options)])
    embed_description = f"**{question}**\n\n{formatted_options}"

    embed = discord.Embed(title="❗❗ Pop Quiz ❗❗", description=embed_description, color=0x3498db)

    poll_message = await ctx.send(embed=embed)
    for i, _ in enumerate(options):
        await poll_message.add_reaction(reactions[i])

    # Wait for the specified duration (in minutes)
    await asyncio.sleep(duration * 60)

    # Refresh the poll_message to get the updated reactions
    poll_message = await ctx.channel.fetch_message(poll_message.id)

    results = {}
    for i, option in enumerate(options):
        reaction = discord.utils.get(poll_message.reactions, emoji=reactions[i])
        results[option] = reaction.count - 1  # subtract 1 to exclude bot's reaction

    # Display the results
    results_embed = discord.Embed(title="📈 Results", description=f"**{question}**", color=0x2ecc71)
    for option, count in results.items():
        results_embed.add_field(name=option, value=f"{count} votes", inline=False)

    await ctx.send(embed=results_embed)


bot.run(TOKEN)
