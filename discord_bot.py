# discord_bot.py
import os
import discord
from discord.ext import commands
import requests

# Set up the bot with required intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

# Use your live API endpoint from Render
API_BASE_URL = "https://xp-api.onrender.com"

@bot.command()
async def data(ctx, platform: str, username: str):
    """
    Usage: -data roblox <username>
    Fetches the user's data from your API and sends an embed message.
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
        offense_data = result.get("offenseData", {})  # New field
        offense_text = "None"
        if offense_data and isinstance(offense_data, dict):
            offense_lines = []
            for rule, count in offense_data.items():
                offense_lines.append(f"Rule {rule}: {count} strikes")
            offense_text = "\n".join(offense_lines)

        embed = discord.Embed(
            title=f"{username}'s Roblox Data",
            description=f"XP: **{xp}**\nOffense Data:\n{offense_text}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching data: {e}")

# Retrieve the token from the environment variable
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No Discord bot token provided! Please set the DISCORD_BOT_TOKEN environment variable.")

bot.run(TOKEN)
