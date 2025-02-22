# discord_bot.py
import os
import discord
from discord.ext import commands
import requests

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

# Replace with your live API endpoint
API_BASE_URL = "https://xp-api.onrender.com"

# Example main group ID
MAIN_GROUP_ID = 7444608

# Example other kingdoms
OTHER_KINGDOM_IDS = {
    11592051: "Artic's Kingdom",
    4561896:  "Kavra's Kingdom",
    16132358: "Vinay's Kingdom"
}

def get_headshot(user_id):
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

def get_group_rank(user_id, group_id):
    """Fetch the user's role name in a single group."""
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
    """
    Fetch the user's roles in multiple groups in one request.
    Returns a dict: { group_id: "Role Name" }
    """
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
    Shows XP, offense data, userId, and group ranks if desired.
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    # 1) GET from /get_user_data
    url = f"{API_BASE_URL}/get_user_data?username={username}"
    try:
        response = requests.get(url)
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

        # Get main group rank
        main_group_rank = get_group_rank(user_id, MAIN_GROUP_ID)

        # Get other kingdoms
        other_ranks = get_all_group_ranks(user_id, OTHER_KINGDOM_IDS.keys())
        kingdoms_text = []
        for gid, kingdom_name in OTHER_KINGDOM_IDS.items():
            role = other_ranks[gid]
            kingdoms_text.append(f"**{kingdom_name}:** {role}")
        kingdoms_info = "\n".join(kingdoms_text)

        # Build offense text
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
async def setxp(ctx, platform: str, username: str, new_xp: int):
    """
    Usage: -setxp roblox <username> <newXP>
    Looks up the user's userId, then calls /set_xp to change their XP.
    """
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return

    # 1) Look up the user to get userId
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

# Run your bot
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No Discord bot token provided!")
bot.run(TOKEN)
