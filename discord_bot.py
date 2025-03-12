import os
import discord
from discord.ext import commands, tasks
import requests
import datetime
import uuid
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='-', intents=intents)

API_BASE_URL = "https://xp-api.onrender.com"

MAIN_GROUP_ID = 7444608
OTHER_KINGDOM_IDS = {
    11592051: "Artic's Kingdom",
    4561896: "Kavra's Kingdom",
    16132358: "Vinay's Kingdom"
}

GAME_BADGE_ID = 123456789

def format_timestamp(ts):
    try:
        if isinstance(ts, str) and ts.endswith("Z"):
            ts = ts[:-1]
        dt = datetime.datetime.fromisoformat(ts)
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return ts

def get_headshot(user_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("imageUrl", f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png")
        else:
            return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"
    except Exception:
        return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

def get_group_rank(user_id, group_id):
    url = f"{API_BASE_URL}/get_group_rank?userId={user_id}&groupId={group_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'error' not in data:
            return data.get('rank', 'Not in group')
        return 'Not in group'
    except Exception:
        return 'Not in group'

def get_all_group_ranks(user_id, group_ids):
    ranks = {gid: get_group_rank(user_id, gid) for gid in group_ids}
    return ranks

def get_roblox_profile(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

def get_last_online(user_id):
    url = "https://presence.roblox.com/v1/presence/last-online"
    payload = {"userIds": [user_id]}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("lastOnline", "N/A")
        return "N/A"
    except Exception:
        return "N/A"

def get_presence_status(user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [user_id]}
    try:
        resp = requests.post(url, json=payload, timeout=10)
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
    url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates?badgeIds={badge_id}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("awardedDate", "N/A")
        else:
            return "Not Awarded"
    except Exception:
        return "Error"

def get_friends_count(user_id):
    url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("count", "N/A")
    except Exception:
        return "N/A"

def get_roblox_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data") and len(data["data"]) > 0:
            return data["data"][0].get("id")
        return None
    except Exception:
        return None

@bot.command()
async def data(ctx, platform: str, username: str):
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return
    api_url = f"{API_BASE_URL}/get_user_data?username={username}"
    try:
        response = requests.get(api_url, timeout=10)
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
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return
    if new_xp < 0:
        await ctx.send("XP must be a non-negative integer.")
        return
    get_url = f"{API_BASE_URL}/get_user_data?username={username}"
    try:
        get_resp = requests.get(get_url, timeout=10)
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
        post_resp = requests.post(post_url, json=payload, timeout=10)
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
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return
    try:
        response = requests.get(f"{API_BASE_URL}/leaderboard", timeout=10)
        response.raise_for_status()
        data = response.json()
        top_players = data.get('leaderboard', [])
        if not top_players:
            await ctx.send("No leaderboard data available.")
            return
        embed = discord.Embed(
            title="Roblox XP Leaderboard",
            description="Top players by XP",
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
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return
    if xp < 0:
        await ctx.send("XP must be a non-negative integer.")
        return
    payload = {
        "userId": roblox_user_id,
        "username": username,
        "xp": xp,
        "offenseData": {}
    }
    try:
        response = requests.post(f"{API_BASE_URL}/update_xp", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("status") == "success":
            await ctx.send(f"Successfully registered {username} (ID: {roblox_user_id}) with XP {xp}.")
        else:
            await ctx.send(f"Error: {result.get('error', 'Unknown error')}")
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error registering user: {e}")

@bot.command()
async def xphistory(ctx, platform: str, username: str):
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return
    try:
        user_id = get_roblox_user_id(username)
        if not user_id:
            await ctx.send(f"Could not find Roblox user {username}.")
            return
        response = requests.get(f"{API_BASE_URL}/user_stats?userId={user_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
        history = data.get('xp_history', [])
        if not history:
            await ctx.send(f"No XP history found for {username}.")
            return
        embed = discord.Embed(
            title=f"{username}'s XP History",
            color=discord.Color.green()
        )
        for entry in history[:10]:
            embed.add_field(
                name=format_timestamp(entry['timestamp']),
                value=f"XP Change: {entry['xp_change']}",
                inline=False
            )
        await ctx.send(embed=embed)
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching XP history: {e}")

# Dictionary to store pending verifications
pending_verifications = {}

# Separate handler for the ticket conversation
async def handle_ticket(channel, interaction):
    max_retries = 3

    def check(m):
        return m.author == interaction.user and m.channel == channel

    # Ask for Roblox username
    await channel.send(f"{interaction.user.mention}, please provide your Roblox username.")
    retries = max_retries
    username = None
    user_id = None
    while retries > 0:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            username = msg.content.strip()
            user_id = get_roblox_user_id(username)
            if not user_id:
                retries -= 1
                await channel.send(f"That name is incorrect, try again. ({retries} retries left)")
                if retries == 0:
                    await channel.send("Max retries reached. Please start a new ticket with `-ranktransfer`.")
                    return
                continue
            break
        except asyncio.TimeoutError:
            await channel.send("Timed out waiting for your username. Please try again.")
            return

    verification_code = str(uuid.uuid4()).split("-")[0]
    pending_verifications[username.lower()] = {
        "discord_id": interaction.user.id,
        "code": verification_code,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    await channel.send(
        f"Please add this code to your Roblox profile description: `{verification_code}`\n"
        "Then reply with 'confirm' in this channel."
    )

    retries = max_retries
    while retries > 0:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            if msg.content.lower() != "confirm":
                retries -= 1
                await channel.send(f"Please reply with 'confirm' to verify. ({retries} retries left)")
                if retries == 0:
                    await channel.send("Max retries reached. Please start a new ticket with `-ranktransfer`.")
                    return
                continue
            profile = get_roblox_profile(user_id)
            if not profile or verification_code not in profile.get("description", ""):
                retries -= 1
                await channel.send(f"Verification code not found in your Roblox bio. Please add it and try 'confirm' again. ({retries} retries left)")
                if retries == 0:
                    await channel.send("Max retries reached. Please start a new ticket with `-ranktransfer`.")
                    return
                continue
            break
        except asyncio.TimeoutError:
            await channel.send("Timed out waiting for confirmation. Please try again.")
            return

    del pending_verifications[username.lower()]
    await channel.send("Verification successful! Proceeding with rank transfer.")

    group_ids = [MAIN_GROUP_ID] + list(OTHER_KINGDOM_IDS.keys())
    ranks = {gid: get_group_rank(user_id, gid) for gid in group_ids}
    ranks_text = "Your ranks:\n"
    for i, (gid, rank) in enumerate(ranks.items(), start=1):
        kingdom = "Main Group" if gid == MAIN_GROUP_ID else OTHER_KINGDOM_IDS.get(gid, "Unknown")
        ranks_text += f"{i}: {kingdom} - {rank}\n"
    ranks_text += "Which group would you like to transfer from? (Reply with the corresponding number)"
    await channel.send(ranks_text)

    retries = max_retries
    while retries > 0:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            choice = msg.content.strip()
            group_list = list(ranks.keys())
            if 1 <= int(choice) <= len(group_list):
                source_group_id = group_list[int(choice) - 1]
                source_rank = ranks[source_group_id]
                if source_group_id == MAIN_GROUP_ID:
                    await channel.send("You cannot transfer from the Main Group. Please select another group.")
                    continue
                await channel.send(f"Selected group: {OTHER_KINGDOM_IDS.get(source_group_id, 'Unknown')} with rank {source_rank}. Transferring to Main Group...")
                if source_rank == "Not in group":
                    await channel.send(f"You are not a member of {OTHER_KINGDOM_IDS.get(source_group_id, 'Unknown')}. Please join the group and try again.")
                    return
                # Get corresponding role id in the main group for the rank name
                url = f"{API_BASE_URL}/get_role_id?groupId={MAIN_GROUP_ID}&rankName={source_rank}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'roleId' in data:
                        target_role_id = data['roleId']
                        payload = {
                            "userId": user_id,
                            "groupId": MAIN_GROUP_ID,
                            "roleId": target_role_id
                        }
                        response = requests.post(f"{API_BASE_URL}/set_group_rank", json=payload, timeout=10)
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('status') == 'success':
                                await channel.send(f"Successfully transferred rank '{source_rank}' to Main Group!")
                            else:
                                await channel.send(f"Failed to transfer rank to Main Group: {result.get('error', 'Unknown error')}")
                        else:
                            await channel.send(f"Failed to transfer rank to Main Group: HTTP {response.status_code}")
                    else:
                        await channel.send(f"Rank '{source_rank}' not found in Main Group.")
                else:
                    await channel.send(f"Error fetching role ID: HTTP {response.status_code}")
                break
            else:
                retries -= 1
                await channel.send(f"Invalid choice. Please reply with a valid number. ({retries} retries left)")
                if retries == 0:
                    await channel.send("Max retries reached. Please start a new ticket with `-ranktransfer`.")
                    return
                continue
        except (asyncio.TimeoutError, ValueError):
            retries -= 1
            await channel.send(f"Invalid input or timed out. Please try again. ({retries} retries left)")
            if retries == 0:
                await channel.send("Max retries reached. Please start a new ticket with `-ranktransfer`.")
                return

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Open Ticket button clicked by {interaction.user} (ID: {interaction.user.id})")
        try:
            guild = interaction.guild
            allowed_roles = ["Jester", "Proxy", "Head Proxy", "Vortex", "Noob", "Alaska's Father", "Alaska", "The Queen", "Bacon", "Role Updater"]
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
            }
            for role_name in allowed_roles:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
            category = discord.utils.get(guild.categories, name="Tickets")
            if not category:
                category = await guild.create_category("Tickets")
            channel = await guild.create_text_channel(
                name=f"rank-transfer-{interaction.user.name}",
                category=category,
                overwrites=overwrites,
                reason="Rank transfer request"
            )
            await channel.send("Creating your ticket...")
            await handle_ticket(channel, interaction)
        except Exception as e:
            logger.error(f"Error in open_ticket: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Close Ticket button clicked by {interaction.user} (ID: {interaction.user.id})")
        await interaction.response.send_message("Closing ticket...")
        await interaction.channel.delete()

@bot.command()
async def ranktransfer(ctx):
    view = TicketView()
    await ctx.send("Make a ticket for a rank transfer!", view=view)

@tasks.loop(minutes=30)
async def clean_verifications():
    now = datetime.datetime.utcnow()
    expired = [k for k, v in pending_verifications.items()
               if (now - datetime.datetime.fromisoformat(v['timestamp'])).total_seconds() > 3600]
    for k in expired:
        del pending_verifications[k]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    clean_verifications.start()

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
