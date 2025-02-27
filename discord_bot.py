import os
import discord
from discord.ext import commands
import requests

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

API_BASE_URL = "https://xp-api.onrender.com"  # Your internal API URL

# Roblox group IDs (unchanged)
MAIN_GROUP_ID = 7444608  # Example "main" group
OTHER_KINGDOM_IDS = {
    11592051: "Artic's Kingdom",
    4561896:  "Kavra's Kingdom",
    16132358: "Vinay's Kingdom"
}

# Placeholder badge ID for determining when a user first joined game 84416791344548.
# Replace with the actual badge id that is awarded upon first join.
GAME_BADGE_ID = 123456789  

def get_headshot(user_id):
    """
    Uses Roblox's Thumbnails API to retrieve a headshot.
    Fallback to the old URL if anything fails.
    """
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("imageUrl", f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png")
        else:
            return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"
    except Exception as e:
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

def get_roblox_profile(user_id):
    """
    Fetches Roblox profile data including account creation date,
    display name, and description.
    """
    url = f"https://users.roblox.com/v1/users/{user_id}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None

def get_last_online(user_id):
    """
    Retrieves the last online timestamp for the user.
    The API returns the date when the user was last seen.
    """
    url = "https://presence.roblox.com/v1/presence/last-online"
    payload = {"userIds": [user_id]}
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            # Returns a timestamp string (ISO format) if available.
            return data["data"][0].get("lastOnline", "N/A")
        return "N/A"
    except Exception as e:
        return "N/A"

def get_game_join_date(user_id, badge_id=GAME_BADGE_ID):
    """
    Checks the awarded date for a specific badge (assumed to be awarded upon first join)
    for the game with id 84416791344548.
    """
    url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates?badgeIds={badge_id}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("awardedDate", "N/A")
        else:
            return "Not Awarded"
    except Exception as e:
        return "Error"

@bot.command()
async def data(ctx, platform: str, username: str):
    """
    Usage: -data roblox <username>
    Fetches the player's data from your API and then enriches it with additional
    details from Roblox (account creation, last online, game join date, etc.).
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    # 1. Get the player's stored data (XP, offense, etc.) from your API.
    api_url = f"{API_BASE_URL}/get_user_data?username={username}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            await ctx.send(f"Error: {result['error']}")
            return
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching data: {e}")
        return

    xp = result.get("xp", "Unknown")
    offense_data = result.get("offenseData", {})
    user_id = result.get("userId")
    last_updated = result.get("last_updated", "Unknown")

    if user_id is None:
        await ctx.send("User data does not include a userId.")
        return

    # 2. Retrieve extra details from Roblox's official APIs.
    profile = get_roblox_profile(user_id)
    account_created = profile.get("created") if profile and "created" in profile else "N/A"
    
    last_online = get_last_online(user_id)
    game_join_date = get_game_join_date(user_id)  # via badge award date

    # 3. Get group ranks (main group and others).
    main_group_rank = get_group_rank(user_id, MAIN_GROUP_ID)
    other_ranks = get_all_group_ranks(user_id, OTHER_KINGDOM_IDS.keys())
    kingdoms_text = []
    for gid, kingdom_name in OTHER_KINGDOM_IDS.items():
        role = other_ranks[gid]
        kingdoms_text.append(f"**{kingdom_name}:** {role}")
    kingdoms_info = "\n".join(kingdoms_text)

    # 4. Format offense data.
    if offense_data and isinstance(offense_data, dict):
        offense_lines = [f"Rule {rule}: {count} strikes" for rule, count in offense_data.items()]
        offense_text = "\n".join(offense_lines)
    else:
        offense_text = "None"

    # 5. Retrieve headshot image.
    headshot_url = get_headshot(user_id)

    # 6. Construct the embed with all the details.
    description = (
        f"**XP:** {xp}\n"
        f"**Last Updated:** {last_updated}\n"
        f"**Account Created:** {account_created}\n"
        f"**Last Online:** {last_online}\n"
        f"**Game Join Date:** {game_join_date}\n"
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
    embed.add_field(name="Profile", value=f"[View Roblox Profile](https://www.roblox.com/users/{user_id}/profile)", inline=False)

    await ctx.send(embed=embed)

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
    Updates the player's XP in your API.
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    # Get user data to find userId
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

        # Update XP via the API
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

@bot.command()
async def leaderboard(ctx, platform: str):
    """
    Usage: -leaderboard roblox
    Fetches the top 10 players by XP from the API and displays them.
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    try:
        response = requests.get(f"{API_BASE_URL}/leaderboard")
        response.raise_for_status()
        top_players = response.json()
        if not top_players:
            await ctx.send("No leaderboard data available.")
            return

        embed = discord.Embed(
            title="Roblox XP Leaderboard",
            description="Top 10 players by XP",
            color=discord.Color.gold()
        )
        for index, player in enumerate(top_players, start=1):
            embed.add_field(
                name=f"#{index} - {player.get('username', 'Unknown')}",
                value=f"XP: {player.get('xp', 0)}",
                inline=False
            )
        await ctx.send(embed=embed)
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching leaderboard: {e}")

@bot.command()
async def register(ctx, platform: str, username: str, roblox_user_id: int, xp: int = 0):
    """
    Usage: -register roblox <username> <roblox_user_id> [xp]
    Registers a new user in the API with optional starting XP.
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    payload = {
        "userId": roblox_user_id,
        "username": username,
        "xp": xp,
        "offenseData": {}
    }
    try:
        response = requests.post(f"{API_BASE_URL}/update_xp", json=payload)
        response.raise_for_status()
        result = response.json()
        if result.get("status") == "success":
            await ctx.send(f"Successfully registered {username} (ID: {roblox_user_id}) with XP {xp}.")
        else:
            await ctx.send(f"Error: {result.get('error', 'Unknown error')}")
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error registering user: {e}")

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
