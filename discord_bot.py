# discord_bot.py
import os
import discord
from discord.ext import commands
import requests

# Set up the bot with required intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

# Your API endpoint and Roblox group id
API_BASE_URL = "https://xp-api.onrender.com"
GROUP_ID = 7444608

def get_headshot(user_id):
    """
    Returns the URL for the Roblox player's headshot thumbnail.
    """
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

def get_group_rank(user_id, group_id):
    """
    Calls Roblox's group roles endpoint to get the player's role name (i.e. group rank)
    in the specified group.
    """
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        for group in data.get("data", []):
            if group.get("group", {}).get("id") == group_id:
                return group.get("role", {}).get("name")
        return "Not in group"
    except Exception as e:
        return "Unknown"

@bot.command()
async def data(ctx, platform: str, username: str):
    """
    Usage: -data roblox <username>
    Fetches the player's data from your API, then retrieves and displays:
      - XP
      - Their group rank (via Roblox group API)
      - Their headshot image (set as the embed's thumbnail)
      - Offense data if available
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    api_url = f"{API_BASE_URL}/get_user_data?username={username}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            await ctx.send(f"Error: {result['error']}")
            return

        xp = result.get("xp", "Unknown")
        offense_data = result.get("offenseData", {})
        # Make sure the API returns the player's Roblox userId.
        user_id = result.get("userId", None)
        if user_id is None:
            await ctx.send("User data does not include a userId.")
            return

        # Retrieve additional Roblox info
        group_rank = get_group_rank(user_id, GROUP_ID)
        headshot_url = get_headshot(user_id)

        # Build a string for offense data if available
        offense_text = "None"
        if offense_data and isinstance(offense_data, dict):
            offense_lines = []
            for rule, count in offense_data.items():
                offense_lines.append(f"Rule {rule}: {count} strikes")
            offense_text = "\n".join(offense_lines)

        embed = discord.Embed(
            title=f"{username}'s Roblox Data",
            description=f"**XP:** {xp}\n**Group Rank:** {group_rank}\n**Offense Data:**\n{offense_text}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=headshot_url)
        await ctx.send(embed=embed)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching data: {e}")

# Retrieve the token from the environment variable
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No Discord bot token provided! Please set the DISCORD_BOT_TOKEN environment variable.")

bot.run(TOKEN)

