import os
import discord
from discord.ext import commands
import requests

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

API_BASE_URL = "https://xp-api.onrender.com"  # Replace with your actual API URL

MAIN_GROUP_ID = 7444608  # Example "main" group
OTHER_KINGDOM_IDS = {
    11592051: "Artic's Kingdom",
    4561896:  "Kavra's Kingdom",
    16132358: "Vinay's Kingdom"
}

def get_headshot(user_id):
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

def get_group_rank(user_id, group_id):
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

def get_all_group_ranks(user_id, group_ids):
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    ranks = {gid: "Not in group" for gid in group_ids}

    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        for group_info in data.get("data", []):
            gid = group_info.get("group", {}).get("id")
            if gid in ranks:
                role_name = group_info.get("role", {}).get("name", "Unknown Role")
                ranks[gid] = role_name
    except Exception as e:
        for gid in group_ids:
            ranks[gid] = f"Unknown (error: {e})"

    return ranks

@bot.command()
async def data(ctx, platform: str, username: str):
    """
    Usage: -data roblox <username>
    Fetches the player's data from your API and displays it.
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
        user_id = result.get("userId")

        if user_id is None:
            await ctx.send("User data does not include a userId.")
            return

        # Main group rank
        main_group_rank = get_group_rank(user_id, MAIN_GROUP_ID)

        # Other kingdoms
        other_ranks = get_all_group_ranks(user_id, OTHER_KINGDOM_IDS.keys())
        kingdoms_text = []
        for gid, kingdom_name in OTHER_KINGDOM_IDS.items():
            role = other_ranks[gid]
            kingdoms_text.append(f"**{kingdom_name}:** {role}")
        kingdoms_info = "\n".join(kingdoms_text)

        # Offense data
        offense_text = "None"
        if offense_data and isinstance(offense_data, dict):
            lines = []
            for rule, count in offense_data.items():
                lines.append(f"Rule {rule}: {count} strikes")
            offense_text = "\n".join(lines)

        # Headshot
        headshot_url = get_headshot(user_id)

        # Construct embed
        description = (
            f"**XP:** {xp}\n"
            f"**Main Group Rank:** {main_group_rank}\n"
            f"**Offense Data:**\n{offense_text}\n\n"
            f"**Other Kingdom Ranks:**\n{kingdoms_info}"
        )
        embed = discord.Embed(
            title=f"{username}'s Roblox Data",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=headshot_url)

        await ctx.send(embed=embed)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching data: {e}")

@bot.command()
@commands.has_any_role(
    "Proxy",
    "Head Proxy",
    "Vortex",
    "Noob",
    "Alaska's Father",
    "Alaska",
    "The Queen",
    "Bacon",
    "Role Updater"
)
async def setxp(ctx, platform: str, username: str, new_xp: int):
    """
    Usage: -setxp roblox <username> <new_xp>
    Updates the player's XP in your API, restricted to 'Proxy' role and above.
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    # 1) Get user data to find userId
    get_url = f"{API_BASE_URL}/get_user_data?username={username}"
    try:
        get_resp = requests.get(get_url)
        get_resp.raise_for_status()
        user_data = get_resp.json()

        if "error" in user_data:
            await ctx.send(f"Error: {user_data['error']}")
            return

        user_id = user_data.get("userId")
        if user_id is None:
            await ctx.send("User data does not include a userId.")
            return

        # 2) Call /set_xp with userId and new_xp
        post_url = f"{API_BASE_URL}/set_xp"
        payload = {"userId": user_id, "xp": new_xp}
        post_resp = requests.post(post_url, json=payload)
        post_resp.raise_for_status()
        result = post_resp.json()

        if "error" in result:
            await ctx.send(f"Error: {result['error']}")
            return

        updated_xp = result.get("newXp", new_xp)
        await ctx.send(f"Successfully set {username}'s XP to {updated_xp}.")

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error updating XP: {e}")

# Optional: custom error message if user lacks roles
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("You do not have permission to use this command.")
    else:
        raise error

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No Discord bot token provided!")
bot.run(TOKEN)
