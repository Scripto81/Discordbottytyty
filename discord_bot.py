import os
import discord
from discord.ext import commands, tasks
import requests
import datetime
import uuid
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename='discord_bot.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix='-', intents=intents)

# API base URL from environment
API_BASE_URL = os.getenv("API_BASE_URL", "https://xp-api.onrender.com")

# Group IDs
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
    except Exception as e:
        logger.error(f"Error formatting timestamp: {str(e)}")
        return ts

def get_headshot(user_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["data"][0].get("imageUrl", f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png")
    except requests.RequestException as e:
        logger.error(f"Error fetching headshot for user {user_id}: {str(e)}")
        return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

def get_group_rank(user_id, group_id):
    url = f"{API_BASE_URL}/get_group_rank?userId={user_id}&groupId={group_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('rank', 'Not in group')
    except requests.RequestException as e:
        logger.error(f"Error fetching group rank for user {user_id}, group {group_id}: {str(e)}")
        return 'Not in group'

def get_all_group_ranks(user_id, group_ids):
    return {gid: get_group_rank(user_id, gid) for gid in group_ids}

def get_roblox_profile(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching Roblox profile for user {user_id}: {str(e)}")
        return None

def get_last_online(user_id):
    url = "https://presence.roblox.com/v1/presence/last-online"
    payload = {"userIds": [user_id]}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0].get("lastOnline", "N/A") if data.get("data") else "N/A"
    except requests.RequestException as e:
        logger.error(f"Error fetching last online for user {user_id}: {str(e)}")
        return "N/A"

def get_presence_status(user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [user_id]}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        status_num = data["data"][0].get("userPresenceType", 0) if data.get("data") else 0
        if status_num == 0:
            lo = get_last_online(user_id)
            return f"Offline (Last Online: {format_timestamp(lo)})" if lo != "N/A" else "Offline"
        elif status_num == 1:
            return "Online"
        elif status_num == 2:
            return "In Game"
        elif status_num == 3:
            return "In Studio"
        return "Unknown"
    except requests.RequestException as e:
        logger.error(f"Error fetching presence status for user {user_id}: {str(e)}")
        return "Unknown"

def get_game_join_date(user_id, badge_id=GAME_BADGE_ID):
    url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates?badgeIds={badge_id}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0].get("awardedDate", "N/A") if data.get("data") else "Not Awarded"
    except requests.RequestException as e:
        logger.error(f"Error fetching game join date for user {user_id}: {str(e)}")
        return "Error"

def get_friends_count(user_id):
    url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("count", "N/A")
    except requests.RequestException as e:
        logger.error(f"Error fetching friends count for user {user_id}: {str(e)}")
        return "N/A"

def get_roblox_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0].get("id") if data.get("data") else None
    except requests.RequestException as e:
        logger.error(f"Error fetching user ID for username {username}: {str(e)}")
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
        user_id = result.get("userId")
        if not user_id:
            await ctx.send("User data does not include a userId.")
            return
        xp = result.get("xp", "Unknown")
        offense_data = result.get("offenseData", {})
        last_updated = result.get("last_updated", "Unknown")

        profile = get_roblox_profile(user_id)
        display_name = profile.get("displayName", username) if profile else username
        account_created = format_timestamp(profile.get("created")) if profile else "N/A"
        presence_status = get_presence_status(user_id)
        game_join_date = format_timestamp(get_game_join_date(user_id)) if get_game_join_date(user_id) not in ["Not Awarded", "Error", "N/A"] else "N/A"
        friends_count = get_friends_count(user_id)
        main_group_rank = get_group_rank(user_id, MAIN_GROUP_ID)
        other_ranks = get_all_group_ranks(user_id, OTHER_KINGDOM_IDS.keys())
        kingdoms_text = "\n".join([f"**{OTHER_KINGDOM_IDS[gid]}:** {rank}" for gid, rank in other_ranks.items()])
        offense_text = "\n".join([f"Rule {k}: {v} strikes" for k, v in offense_data.items()]) if offense_data else "None"

        embed = discord.Embed(title=f"{username}'s Roblox Data", color=discord.Color.blue())
        embed.set_thumbnail(url=get_headshot(user_id))
        embed.add_field(name="Display Name", value=display_name, inline=True)
        embed.add_field(name="XP", value=xp, inline=True)
        embed.add_field(name="Last Updated", value=format_timestamp(last_updated) if last_updated != "Unknown" else last_updated, inline=True)
        embed.add_field(name="Account Created", value=account_created, inline=True)
        embed.add_field(name="Presence", value=presence_status, inline=True)
        embed.add_field(name="Game Join Date", value=game_join_date, inline=True)
        embed.add_field(name="Friends", value=friends_count, inline=True)
        embed.add_field(name="Main Group Rank", value=main_group_rank, inline=True)
        embed.add_field(name="Offense Data", value=offense_text, inline=False)
        embed.add_field(name="Other Kingdom Ranks", value=kingdoms_text, inline=False)
        embed.add_field(name="Profile", value=f"[View Roblox Profile](https://www.roblox.com/users/{user_id}/profile)", inline=False)
        await ctx.send(embed=embed)
    except requests.RequestException as e:
        logger.error(f"Error fetching data for {username}: {str(e)}")
        await ctx.send("Failed to fetch user data. Please try again later.")

@bot.command()
@commands.has_any_role("Proxy", "Head Proxy", "Vortex", "Noob", "Alaska's Father", "Alaska", "The Queen", "Bacon", "Role Updater")
async def setxp(ctx, platform: str, username: str, new_xp: int):
    if platform.lower() != "roblox":
        await ctx.send("Unsupported platform. Please use 'roblox'.")
        return
    if new_xp < 0:
        await ctx.send("XP must be a non-negative integer.")
        return
    try:
        user_id = get_roblox_user_id(username)
        if not user_id:
            await ctx.send(f"Could not find Roblox user {username}.")
            return
        url = f"{API_BASE_URL}/set_xp"
        payload = {"userId": user_id, "xp": new_xp}
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            await ctx.send(f"Error: {result['error']}")
            return
        await ctx.send(f"Successfully set {username}'s XP to {result.get('newXp', new_xp)}.")
    except requests.RequestException as e:
        logger.error(f"Error setting XP for {username}: {str(e)}")
        await ctx.send("Failed to update XP. Please try again later.")

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
        embed = discord.Embed(title="Roblox XP Leaderboard", description="Top players by XP", color=discord.Color.gold())
        for i, player in enumerate(top_players, 1):
            embed.add_field(name=f"#{i} - {player['username']}", value=f"XP: {player['xp']}", inline=False)
        await ctx.send(embed=embed)
    except requests.RequestException as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        await ctx.send("Failed to fetch leaderboard. Please try again later.")

pending_verifications = {}

async def handle_ticket(channel, interaction):
    max_retries = 3

    def check(m):
        return m.author == interaction.user and m.channel == channel

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
                await channel.send(f"Invalid username. {retries} retries left.")
                if retries == 0:
                    await channel.send("Max retries reached. Please start a new ticket.")
                    return None, None
                continue
            break
        except asyncio.TimeoutError:
            await channel.send("Timed out waiting for username.")
            return None, None

    verification_code = str(uuid.uuid4()).split("-")[0]
    pending_verifications[username.lower()] = {
        "discord_id": interaction.user.id,
        "code": verification_code,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    await channel.send(f"Add this code to your Roblox bio: `{verification_code}`\nReply with 'confirm' when done.")

    retries = max_retries
    while retries > 0:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            if msg.content.lower() != "confirm":
                retries -= 1
                await channel.send(f"Please reply with 'confirm'. {retries} retries left.")
                if retries == 0:
                    await channel.send("Max retries reached. Please start a new ticket.")
                    return None, None
                continue
            profile = get_roblox_profile(user_id)
            if not profile or verification_code not in profile.get("description", ""):
                retries -= 1
                await channel.send(f"Code not found in bio. {retries} retries left.")
                if retries == 0:
                    await channel.send("Max retries reached. Please start a new ticket.")
                    return None, None
                continue
            break
        except asyncio.TimeoutError:
            await channel.send("Timed out waiting for confirmation.")
            return None, None

    del pending_verifications[username.lower()]
    await channel.send("Verification successful! Checking your ranks...")

    group_ids = [MAIN_GROUP_ID] + list(OTHER_KINGDOM_IDS.keys())
    ranks = get_all_group_ranks(user_id, group_ids)
    ranks_text = "Your ranks:\n" + "\n".join(
        [f"{i}: {OTHER_KINGDOM_IDS.get(gid, 'Main Group')} - {rank}" for i, (gid, rank) in enumerate(ranks.items(), 1)]
    ) + "\nWhich group to transfer from? (Reply with number)"
    await channel.send(ranks_text)

    retries = max_retries
    while retries > 0:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            choice = int(msg.content.strip())
            group_list = list(ranks.keys())
            if 1 <= choice <= len(group_list):
                source_group_id = group_list[choice - 1]
                source_rank = ranks[source_group_id]
                if source_group_id == MAIN_GROUP_ID:
                    await channel.send("Cannot transfer from Main Group. Choose another.")
                    continue
                if source_rank == "Not in group":
                    await channel.send("You’re not in the selected group. Please join and retry.")
                    return None, None
                await channel.send(f"Transferring rank '{source_rank}' from {OTHER_KINGDOM_IDS.get(source_group_id, 'Unknown')} to Main Group...")
                url = f"{API_BASE_URL}/get_role_id?groupId={MAIN_GROUP_ID}&rankName={source_rank}"
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if "roleId" not in data:
                    await channel.send(f"Rank '{source_rank}' not found in Main Group.")
                    return None, None
                target_role_id = data["roleId"]
                payload = {"userId": user_id, "groupId": MAIN_GROUP_ID, "roleId": target_role_id}
                resp = requests.post(f"{API_BASE_URL}/set_group_rank", json=payload, timeout=10)
                resp.raise_for_status()
                result = resp.json()
                if result.get("status") == "success":
                    await channel.send(f"Successfully transferred rank '{source_rank}' to Main Group!")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    error_details = result.get('details', 'No details provided')
                    await channel.send(f"Failed to transfer rank: {error_msg} - {error_details}")
                return user_id, source_rank
            retries -= 1
            await channel.send(f"Invalid choice. {retries} retries left.")
            if retries == 0:
                await channel.send("Max retries reached. Please start a new ticket.")
                return None, None
        except ValueError:
            retries -= 1
            await channel.send(f"Invalid input. Please enter a number. {retries} retries left.")
            if retries == 0:
                await channel.send("Max retries reached. Please start a new ticket.")
            return None, None
        except asyncio.TimeoutError:
            retries -= 1
            await channel.send(f"Timed out waiting for choice. {retries} retries left.")
            if retries == 0:
                await channel.send("Max retries reached. Please start a new ticket.")
            return None, None
        except requests.RequestException as e:
            retries -= 1
            error_msg = "Failed to set rank"
            if e.response:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', 'Unknown error')
                    error_details = error_data.get('details', 'No details provided')
                    error_msg = f"{error_msg} - {error_details}"
                except ValueError:
                    error_msg = f"{e.response.status_code} - {e.response.text}"
            await channel.send(f"API error: {error_msg}. {retries} retries left.")
            logger.error(f"Error setting group rank: {str(e)}")
            if retries == 0:
                await channel.send("Max retries reached. Please start a new ticket.")
            return None, None
    return None, None

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            category = discord.utils.get(guild.categories, name="Tickets") or await guild.create_category("Tickets")
            channel = await guild.create_text_channel(
                name=f"rank-transfer-{interaction.user.name}",
                category=category,
                overwrites=overwrites
            )
            await interaction.response.send_message("Ticket created!", ephemeral=True)
            await handle_ticket(channel, interaction)
        except Exception as e:
            logger.error(f"Error opening ticket: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Failed to create ticket.", ephemeral=True)
            else:
                await interaction.followup.send("Failed to create ticket after initial response.", ephemeral=True)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message("Closing ticket...", ephemeral=True)
            await interaction.channel.delete()
        except Exception as e:
            logger.error(f"Error closing ticket: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Failed to close ticket.", ephemeral=True)
            else:
                await interaction.followup.send("Failed to close ticket.", ephemeral=True)

@bot.command()
async def ranktransfer(ctx):
    try:
        view = TicketView()
        await ctx.send("Make a ticket for a rank transfer!", view=view)
    except Exception as e:
        logger.error(f"Error in ranktransfer command: {str(e)}")
        await ctx.send("Failed to initiate rank transfer.")

@tasks.loop(minutes=30)
async def clean_verifications():
    try:
        now = datetime.datetime.utcnow()
        expired = [k for k, v in pending_verifications.items() if (now - datetime.datetime.fromisoformat(v["timestamp"])).total_seconds() > 3600]
        for k in expired:
            del pending_verifications[k]
    except Exception as e:
        logger.error(f"Error cleaning verifications: {str(e)}")

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user}")
    clean_verifications.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("You don’t have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command '{error.command_name}' not found.")
    else:
        logger.error(f"Command error: {str(error)}")
        await ctx.send("An error occurred. Please try again.")
        raise error

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables.")
        raise ValueError("DISCORD_BOT_TOKEN not set!")
    bot.run(TOKEN)
