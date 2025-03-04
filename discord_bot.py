import os
import discord
from discord.ext import commands
import requests
import datetime
import uuid  # For generating unique verification codes

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
# Replace with the actual badge id awarded upon first join.
GAME_BADGE_ID = 123456789

def format_timestamp(ts):
    """Convert an ISO timestamp into a human-friendly format."""
    try:
        if ts.endswith("Z"):
            ts = ts[:-1]
        dt = datetime.datetime.fromisoformat(ts)
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return ts

def get_headshot(user_id):
    """
    Uses Roblox's Thumbnails API to retrieve a headshot.
    Falls back to the old URL if needed.
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
    except Exception:
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
    except Exception:
        return None

def get_last_online(user_id):
    """
    Retrieves the last online timestamp for the user.
    """
    url = "https://presence.roblox.com/v1/presence/last-online"
    payload = {"userIds": [user_id]}
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("lastOnline", "N/A")
        return "N/A"
    except Exception:
        return "N/A"

def get_presence_status(user_id):
    """
    Retrieves the current presence status of the user.
    Returns:
      - "Online", "In Game", "In Studio", or if offline, the formatted last online time.
    """
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [user_id]}
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            status_num = data["data"][0].get("userPresenceType", 0)
            if status_num == 0:
                lo = get_last_online(user_id)
                if lo != "N/A":
                    return f"Offline (Last Online: {format_timestamp(lo)})"
                else:
                    return "Offline"
            elif status_num == 1:
                return "Online"
            elif status_num == 2:
                return "In Game"
            elif status_num == 3:
                return "In Studio"
            else:
                return "Unknown"
        return "Unknown"
    except Exception:
        return "Unknown"

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
    except Exception:
        return "Error"

def get_friends_count(user_id):
    """
    Retrieves the friend count for the user.
    """
    url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("count", "N/A")
    except Exception:
        return "N/A"

def get_roblox_user_id(username):
    """
    Retrieves a Roblox user ID from a given username using the current endpoint.
    """
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data") and len(data["data"]) > 0:
            return data["data"][0].get("id")
        return None
    except Exception as e:
        print("Error in get_roblox_user_id:", e)
        return None

# ---------------------- Commands ----------------------

@bot.command()
async def data(ctx, platform: str, username: str):
    """
    Usage: -data roblox <username>
    Fetches the player's data from your API and enriches it with additional details from Roblox:
      - Account Creation Date
      - Presence (online/offline/in game)
      - Game Join Date (via badge award)
      - Display Name and Friend Count
      - Offense Data (with strike counts and jail data, if applicable)
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

    profile = get_roblox_profile(user_id)
    display_name = profile.get("displayName") if profile and "displayName" in profile else username
    account_created = format_timestamp(profile.get("created")) if profile and "created" in profile else "N/A"
    presence_status = get_presence_status(user_id)
    game_join_date_raw = get_game_join_date(user_id)
    game_join_date = format_timestamp(game_join_date_raw) if game_join_date_raw not in ["Not Awarded", "Error", "N/A"] else game_join_date_raw
    friends_count = get_friends_count(user_id)

    main_group_rank = get_group_rank(user_id, MAIN_GROUP_ID)
    other_ranks = get_all_group_ranks(user_id, OTHER_KINGDOM_IDS.keys())
    kingdoms_text = "\n".join([f"**{OTHER_KINGDOM_IDS[gid]}:** {other_ranks[gid]}" for gid in OTHER_KINGDOM_IDS])

    if offense_data and isinstance(offense_data, dict):
        offense_lines = []
        jail_info = None
        for key, value in offense_data.items():
            if key == "JailData":
                if isinstance(value, dict):
                    jail_info = f"Jail Data: EndTime {value.get('endTime', 'N/A')}, Rule {value.get('strikeNumber', 'N/A')}"
            else:
                offense_lines.append(f"Rule {key}: {value} strikes")
        offense_text = "\n".join(offense_lines) if offense_lines else "None"
        if jail_info:
            offense_text += "\n" + jail_info
    else:
        offense_text = "None"

    headshot_url = get_headshot(user_id)

    embed = discord.Embed(
        title=f"{username}'s Roblox Data",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=headshot_url)
    embed.add_field(name="Display Name", value=display_name, inline=True)
    embed.add_field(name="XP", value=xp, inline=True)
    embed.add_field(name="Last Updated", value=(format_timestamp(last_updated) if last_updated != "Unknown" else last_updated), inline=True)
    embed.add_field(name="Account Created", value=account_created, inline=True)
    embed.add_field(name="Presence", value=presence_status, inline=True)
    embed.add_field(name="Game Join Date", value=game_join_date, inline=True)
    embed.add_field(name="Friends", value=friends_count, inline=True)
    embed.add_field(name="Main Group Rank", value=main_group_rank, inline=True)
    embed.add_field(name="Offense Data", value=offense_text, inline=False)
    embed.add_field(name="Other Kingdom Ranks", value=kingdoms_text, inline=False)
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

# ---------------- Verification Commands ----------------

pending_verifications = {}  # Key: roblox_username.lower(), Value: { "discord_id": int, "code": str, "timestamp": str }
verified_accounts = {}      # Key: roblox_username.lower(), Value: { "discord_id": int, "roblox_user_id": int, "timestamp": str }

@bot.command()
async def verify(ctx, roblox_username: str):
    """
    Usage: -verify <roblox_username>
    Generates a unique code and instructs the user to add it to their Roblox profile description.
    """
    key = roblox_username.lower()
    code = str(uuid.uuid4()).split("-")[0]
    pending_verifications[key] = {
        "discord_id": ctx.author.id,
        "code": code,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    await ctx.send(
        f"{ctx.author.mention}, to verify your Roblox account **{roblox_username}**, please add the following code to your Roblox profile description:\n\n"
        f"`{code}`\n\n"
        "After updating your description, run `-confirm " + roblox_username + "` to complete verification."
    )

@bot.command()
async def confirm(ctx, roblox_username: str):
    """
    Usage: -confirm <roblox_username>
    Checks the Roblox profile description for the verification code and, if found,
    verifies the Roblox account and updates the member's nickname to display as:
    RobloxDisplayName (@RobloxUsername)
    """
    key = roblox_username.lower()
    pending = pending_verifications.get(key)
    if not pending:
        await ctx.send("No pending verification found for that username. Please run `-verify <roblox_username>` first.")
        return

    if pending["discord_id"] != ctx.author.id:
        await ctx.send("You do not have permission to confirm this verification. It was initiated by another user.")
        return

    roblox_user_id = get_roblox_user_id(roblox_username)
    if not roblox_user_id:
        await ctx.send("Could not find that Roblox username.")
        return

    profile = get_roblox_profile(roblox_user_id)
    if not profile:
        await ctx.send("Error fetching Roblox profile.")
        return

    description = profile.get("description", "")
    verification_code = pending["code"]

    if verification_code in description:
        verified_accounts[key] = {
            "discord_id": ctx.author.id,
            "roblox_user_id": roblox_user_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        del pending_verifications[key]

        if ctx.guild:
            try:
                roblox_display_name = profile.get("displayName", roblox_username)
                new_nickname = f"{roblox_display_name} (@{roblox_username})"
                member = ctx.guild.get_member(ctx.author.id)
                if member:
                    await member.edit(nick=new_nickname)
                    await ctx.send(f"Successfully verified Roblox account **{roblox_username}** and updated your nickname to `{new_nickname}`.")
                else:
                    await ctx.send("Verification successful, but I couldn't fetch your Discord member profile to update your nickname.")
            except Exception as e:
                await ctx.send("Verification successful, but I was unable to update your nickname. Please check my permissions.")
        else:
            await ctx.send(f"Successfully verified Roblox account **{roblox_username}**, but nickname updates are only possible in servers.")
    else:
        await ctx.send(
            "Verification code not found in your Roblox profile description. Please ensure you have updated your description to include:\n"
            f"`{verification_code}`\nThen try running the command again."
        )

@bot.command()
async def verified(ctx, roblox_username: str):
    """
    Usage: -verified <roblox_username>
    Displays the verification status of the given Roblox username.
    """
    key = roblox_username.lower()
    if key in verified_accounts:
        info = verified_accounts[key]
        await ctx.send(f"Roblox account **{roblox_username}** is verified with Discord ID {info['discord_id']} (verified at {info['timestamp']}).")
    else:
        await ctx.send(f"No verification found for **{roblox_username}**.")

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
