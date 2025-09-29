import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os
import threading
import os
from flask import Flask

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = int(os.getenv("GUILD_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

voice_sessions = {}  # user_id: {"join_time": datetime, "topic": str, "channel_name": str}

@bot.event
async def on_ready():
    print(f"已登入：{bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Slash 指令同步成功: {len(synced)} 個指令")
    except Exception as e:
        print(f"同步失敗: {e}")

@bot.tree.command(name="record", description="設定本次語音學習主題", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(topic="你想紀錄的主題，例如：微積分")
async def record(interaction: discord.Interaction, topic: str):
    user_id = interaction.user.id
    if user_id in voice_sessions:
        voice_sessions[user_id]["topic"] = topic
        await interaction.response.send_message(f"✅ 已設定主題為：{topic}", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 語音頻道偵測不到您，請重新加入再設定主題。", ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = member.id

    if before.channel is None and after.channel is not None:
        voice_sessions[user_id] = {
            "join_time": datetime.datetime.utcnow(),
            "topic": None,  
            "channel_name": after.channel.name  
        }

    elif before.channel is not None and after.channel is None:
        if user_id in voice_sessions:
            join_time = voice_sessions[user_id]["join_time"]
            topic = voice_sessions[user_id]["topic"]
            channel_name = voice_sessions[user_id]["channel_name"]

            duration = datetime.datetime.utcnow() - join_time
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            time_parts = []
            if hours > 0:
                time_parts.append(f"{hours}h")
            if minutes > 0:
                time_parts.append(f"{minutes}m")
            if seconds > 0 or not time_parts: 
                time_parts.append(f"{seconds}s")
            time_str = ''.join(time_parts)

            log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                if topic:
                    await log_channel.send(f"🕐   {member.display_name} 在 {channel_name} 研讀ㄌ **{topic}** {time_str}    好耶 !")
                else:
                    await log_channel.send(f"🕐   {member.display_name} 在 {channel_name} 獨自升級 {time_str}    好耶 !")

            del voice_sessions[user_id]



# === Fake web server ===
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()



bot.run(TOKEN)

