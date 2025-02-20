# discord_bot.py
import os
import discord
from discord.ext import commands
import requests

# Set up the bot with required intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

# Replace with your live API endpoint
API_BASE_URL = "https://xp-api.onrender.com"
# Replace with your Roblox group ID
GROUP_ID = 7444608

def get_headshot(user_id):
    """
    Returns a URL for the Roblox player's headshot thumbnail.
    """
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

def get_group_rank(user_id, group_id):
    """
    Queries Roblox's group roles endpoint to get the player's role name (group rank).
    """
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        for group_info in data.get("data", []):
            if group_info.get("group", {}).get("id") == group_id:
                return group_info.get("role", {}).get("name", "Unknown Role")
        return "Not in group"
    except Exception as e:
        return f"Unknown (error: {e})"

@bot.command()
async def data(ctx, platform: str, username: str):
    """
    Usage: -data roblox <username>
    Fetches the player's data from your API, then:
      - XP
      - Offense Data
      - userId -> used to get headshot & group rank
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    # Get data from your Flask API
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
        user_id = result.get("userId")  # The key field needed for headshot & rank

        if user_id is None:
            await ctx.send("User data does not include a userId.")
            return

        # Fetch the player's group rank & headshot
        group_rank = get_group_rank(user_id, GROUP_ID)
        headshot_url = get_headshot(user_id)

        # Build offense data text
        offense_text = "None"
        if offense_data and isinstance(offense_data, dict):
            lines = []
            for rule, count in offense_data.items():
                lines.append(f"Rule {rule}: {count} strikes")
            offense_text = "\n".join(lines)

        # Create the embed
        embed = discord.Embed(
            title=f"{username}'s Roblox Data",
            description=(
                f"**XP:** {xp}\n"
                f"**Group Rank:** {group_rank}\n"
                f"**Offense Data:**\n{offense_text}"
            ),
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=headshot_url)

        await ctx.send(embed=embed)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching data: {e}")

# Get the bot token from environment variable
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No Discord bot token provided!")

bot.run(TOKEN)

