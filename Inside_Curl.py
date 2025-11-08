# GPT
# =========================
# Inside_Curl.py (FastAPI + Discord Bot + /health)
# =========================
import os
import threading
import datetime
import time
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI
import uvicorn

# =========================
# FastAPI 初始化（給 Render 用）
# =========================
app = FastAPI()

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "🎧 Discord bot is running smoothly!",
        "author": "Rae's FastAPI wrapper"
    }

@app.get("/health")
def health():
    """健康檢查路徑，用於 Render 健康檢測"""
    return {"status": "ok", "bot_status": "running"}

def run_web():
    """啟動 FastAPI Web Service"""
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# =========================
# Discord Bot 主體（完全保留原邏輯）
# =========================
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv("GUILD_ID", 0))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

if not TOKEN or GUILD_ID == 0 or LOG_CHANNEL_ID == 0:
    print("❌ 錯誤：請設定 DISCORD_BOT_TOKEN、GUILD_ID 和 LOG_CHANNEL_ID")
    exit(1)

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

voice_sessions = {}  # user_id: {"join_time": datetime, "topic": str, "channel_name": str}

# =========================
# Discord 事件 & 指令
# =========================
@bot.event
async def on_ready():
    print(f"✅ 已登入：{bot.user}")
    print(f"📡 伺服器 ID: {GUILD_ID}")
    print(f"📝 記錄頻道 ID: {LOG_CHANNEL_ID}")
    
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"🔍 正在檢查伺服器「{guild.name}」的語音頻道...")
        user_count = 0
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:
                if member.id not in voice_sessions:
                    voice_sessions[member.id] = {
                        "join_time": datetime.datetime.utcnow(),
                        "topic": None,
                        "channel_name": voice_channel.name
                    }
                    print(f"   👤 偵測到 {member.display_name} 已在 {voice_channel.name}")
                    user_count += 1
        if user_count == 0:
            print("   ℹ️ 目前沒有人在語音頻道")
    else:
        print(f"⚠️ 找不到伺服器 ID: {GUILD_ID}，請檢查設定")
    
    print("\n🔄 正在同步 Slash 指令...")
    try:
        guild_obj = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ 伺服器指令同步成功: {len(synced)} 個指令")
        for cmd in synced:
            print(f"   - /{cmd.name}: {cmd.description}")
    except discord.HTTPException as e:
        print(f"❌ 同步失敗 (HTTP錯誤): {e}")
    except Exception as e:
        print(f"❌ 同步失敗: {e}")
    
    print("\n✨ 機器人已就緒！")


@bot.tree.command(
    name="record",
    description="設定本次語音學習主題",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(topic="你想紀錄的主題，例如：微積分")
async def record(interaction: discord.Interaction, topic: str):
    user_id = interaction.user.id
    if user_id in voice_sessions:
        voice_sessions[user_id]["topic"] = topic
        channel_name = voice_sessions[user_id]["channel_name"]
        await interaction.response.send_message(
            f"✅ 已設定主題為：**{topic}**\n📍 頻道：{channel_name}",
            ephemeral=True,
            silent=True
        )
        print(f"📝 {interaction.user.display_name} 設定主題: {topic}")
    else:
        await interaction.response.send_message(
            "⚠️ 偵測不到您在語音頻道中\n請先加入語音頻道再設定主題",
            ephemeral=True
        )


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    user_id = member.id
    log_channel = member.guild.get_channel(LOG_CHANNEL_ID)

    # 加入語音
    if before.channel is None and after.channel is not None:
        voice_sessions[user_id] = {
            "join_time": datetime.datetime.utcnow(),
            "topic": None,
            "channel_name": after.channel.name
        }
        print(f"➕ {member.display_name} 加入 {after.channel.name}")
        if log_channel:
            try:
                await log_channel.send(
                    f"⚠️ 注意！ **{member.display_name}** 已加入語音室 `{after.channel.name}`"
                )
            except Exception as e:
                print(f"❌ 無法發送加入通知: {e}")

    # 離開語音
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

            print(f"➖ {member.display_name} 離開 {channel_name} (時長: {time_str})")
            if log_channel:
                try:
                    if topic:
                        await log_channel.send(
                            f"🕐 {member.display_name} 在 {channel_name} 研讀ㄌ **{topic}** {time_str}    好耶 !",
                            silent=True
                        )
                    else:
                        await log_channel.send(
                            f"🕐 {member.display_name} 在 {channel_name} 獨自升級 {time_str}    好耶 !",
                            silent=True
                        )
                except Exception as e:
                    print(f"❌ 無法發送離開紀錄: {e}")
            del voice_sessions[user_id]

    # 切換語音頻道
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        print(f"🔄 {member.display_name} 從 {before.channel.name} 移動到 {after.channel.name}")


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ 發生錯誤: {event}")
    import traceback
    traceback.print_exc()


# =========================
# 啟動（FastAPI + Discord）
# =========================
if __name__ == "__main__":
    # 啟動 FastAPI 伺服器（背景執行）
    threading.Thread(target=run_web, daemon=True).start()
    
    # 等 1 秒讓 Web Server 完全啟動
    time.sleep(1)
    
    # 啟動 Discord Bot（保持原邏輯）
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ 登入失敗：TOKEN 無效")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")




'''
# claude 
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = int(os.getenv("GUILD_ID")) 
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))


# 如果不想用環境變數，可以直接填寫（不建議，容易洩漏）
# TOKEN = "你的機器人TOKEN"
# GUILD_ID = 你的伺服器ID
# LOG_CHANNEL_ID = 記錄頻道ID

# 啟動時檢查設定
if not TOKEN or GUILD_ID == 0 or LOG_CHANNEL_ID == 0:
    print("❌ 錯誤：請設定 DISCORD_BOT_TOKEN、GUILD_ID 和 LOG_CHANNEL_ID")
    print("方法 1: 設定環境變數")
    print("方法 2: 直接在程式碼中填寫（第 9-11 行）")
    exit(1)

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True  # 加入這個可以消除警告

bot = commands.Bot(command_prefix="!", intents=intents)

voice_sessions = {}  # user_id: {"join_time": datetime, "topic": str, "channel_name": str}

@bot.event
async def on_ready():
    print(f"✅ 已登入：{bot.user}")
    print(f"📡 伺服器 ID: {GUILD_ID}")
    print(f"📝 記錄頻道 ID: {LOG_CHANNEL_ID}")
    
    # 檢查啟動時已經在語音頻道的用戶
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"🔍 正在檢查伺服器「{guild.name}」的語音頻道...")
        user_count = 0
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:
                # 如果該用戶還沒有記錄，就開始計時
                if member.id not in voice_sessions:
                    voice_sessions[member.id] = {
                        "join_time": datetime.datetime.utcnow(),
                        "topic": None,
                        "channel_name": voice_channel.name
                    }
                    print(f"   👤 偵測到 {member.display_name} 已在 {voice_channel.name}")
                    user_count += 1
        
        if user_count == 0:
            print("   ℹ️  目前沒有人在語音頻道")
    else:
        print(f"⚠️  找不到伺服器 ID: {GUILD_ID}，請檢查設定")
    
    # 同步 Slash 指令到指定伺服器（立即生效）
    print("\n🔄 正在同步 Slash 指令...")
    try:
        guild_obj = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ 伺服器指令同步成功: {len(synced)} 個指令")
        for cmd in synced:
            print(f"   - /{cmd.name}: {cmd.description}")
    except discord.HTTPException as e:
        print(f"❌ 同步失敗 (HTTP錯誤): {e}")
        print("   可能原因：機器人沒有 applications.commands 權限")
    except Exception as e:
        print(f"❌ 同步失敗: {e}")
    
    print("\n✨ 機器人已就緒！")

@bot.tree.command(
    name="record", 
    description="設定本次語音學習主題", 
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(topic="你想紀錄的主題，例如：微積分")
async def record(interaction: discord.Interaction, topic: str):
    user_id = interaction.user.id
    
    # 檢查用戶是否在語音頻道
    if user_id in voice_sessions:
        voice_sessions[user_id]["topic"] = topic
        channel_name = voice_sessions[user_id]["channel_name"]
        await interaction.response.send_message(
            f"✅ 已設定主題為：**{topic}**\n📍 頻道：{channel_name}", 
            ephemeral=True, # 私人看到
            silent=True
        )
        print(f"📝 {interaction.user.display_name} 設定主題: {topic}")
    else:
        await interaction.response.send_message(
            "⚠️ 偵測不到您在語音頻道中\n請先加入語音頻道再設定主題", 
            ephemeral=True
        )

@bot.event
async def on_voice_state_update(member, before, after):
    # 忽略機器人自己
    if member.bot:
        return
    
    user_id = member.id
    log_channel = member.guild.get_channel(LOG_CHANNEL_ID)

    # 當用戶加入語音頻道
    if before.channel is None and after.channel is not None:
        # 開始計時
        voice_sessions[user_id] = {
            "join_time": datetime.datetime.utcnow(),
            "topic": None,  
            "channel_name": after.channel.name  
        }
        
        print(f"➕ {member.display_name} 加入 {after.channel.name}")
        
        # 發送加入通知
        if log_channel:
            try:
                await log_channel.send(
                    f"⚠️ 注意！ **{member.display_name}** 已加入語音室 `{after.channel.name}`"
                )
            except Exception as e:
                print(f"❌ 無法發送加入通知: {e}")

    # 當用戶離開語音頻道
    elif before.channel is not None and after.channel is None:
        if user_id in voice_sessions:
            join_time = voice_sessions[user_id]["join_time"]
            topic = voice_sessions[user_id]["topic"]
            channel_name = voice_sessions[user_id]["channel_name"]

            # 計算時長
            duration = datetime.datetime.utcnow() - join_time
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            # 格式化時間字串
            time_parts = []
            if hours > 0:
                time_parts.append(f"{hours}h")
            if minutes > 0:
                time_parts.append(f"{minutes}m")
            if seconds > 0 or not time_parts: 
                time_parts.append(f"{seconds}s")
            time_str = ''.join(time_parts)

            print(f"➖ {member.display_name} 離開 {channel_name} (時長: {time_str})")

            # 發送離開紀錄
            if log_channel:
                try:
                    if topic:
                        await log_channel.send(
                            f"🕐   {member.display_name} 在 {channel_name} 研讀ㄌ **{topic}** {time_str}    好耶 !",
                            silent=True
                        )
                    else:
                        await log_channel.send(
                            f"🕐   {member.display_name} 在 {channel_name} 獨自升級 {time_str}    好耶 !",
                            silent=True
                        )
                except Exception as e:
                    print(f"❌ 無法發送離開紀錄: {e}")

            # 刪除該用戶的計時記錄
            del voice_sessions[user_id]
    
    # 當用戶切換語音頻道（可選功能）
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        print(f"🔄 {member.display_name} 從 {before.channel.name} 移動到 {after.channel.name}")
        # 如果需要，可以在這裡重置計時或保持計時

# 錯誤處理
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ 發生錯誤: {event}")
    import traceback
    traceback.print_exc()

# 啟動機器人
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ 登入失敗：TOKEN 無效")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
'''

''' GPT
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os

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

bot.run(TOKEN)
'''