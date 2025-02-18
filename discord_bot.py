import discord
from discord.ext import commands
import requests

# Set up the bot with required intents (ensure Message Content Intent is enabled in the Discord Developer Portal)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

# Set your API endpoint base URL from Render
API_BASE_URL = "https://xp-api.onrender.com"

@bot.command()
async def data(ctx, platform: str, username: str):
    """
    Usage: -data roblox <username>
    This command fetches the user's data (like XP) from your API and sends an embed message.
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    # Construct the URL to fetch the user data
    api_url = f"{API_BASE_URL}/get_user_data?username={username}"
    try:
        # Request data from the API
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for non-200 responses
        data = response.json()

        # Check if the API returned an error
        if "error" in data:
            await ctx.send(f"Error: {data['error']}")
            return

        # Retrieve the XP (or any other data)
        xp = data.get("xp", "Unknown")

        # Create an embed message with the retrieved data
        embed = discord.Embed(
            title=f"{username}'s Roblox Data",
            description=f"Total in-game experience: **{xp}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching data: {e}")

# Replace 'YOUR_DISCORD_BOT_TOKEN' with your actual Discord bot token
bot.run("MTM0MTIwOTQ1MzQzMjgwMzM2OQ.G2O4SI.tq_a2sO5ViiauXWGBvw6WvAHU3zomunu4_HHe0")
