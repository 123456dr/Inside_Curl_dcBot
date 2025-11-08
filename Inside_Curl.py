# Claude
# =========================
# Inside_Curl.py (修正版)
# Discord Bot + FastAPI + 健康檢查
# =========================
import os
import threading
import datetime
import time
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# =========================
# FastAPI 初始化
# =========================
app = FastAPI(title="Inside_Curl Discord Bot")

# 全域變數：追蹤 bot 狀態
bot_status = {
    "is_ready": False,
    "last_check": datetime.datetime.utcnow(),
    "uptime": 0,
    "active_sessions": 0
}

@app.get("/")
def home():
    """首頁 - 基本資訊"""
    return {
        "status": "ok",
        "service": "Inside_Curl Discord Bot",
        "message": "🎧 Discord bot is running smoothly!",
        "bot_ready": bot_status["is_ready"],
        "active_voice_sessions": bot_status["active_sessions"],
        "uptime_seconds": bot_status["uptime"]
    }

@app.get("/health")
def health():
    """健康檢查端點 - 給 UptimeRobot 用"""
    bot_status["last_check"] = datetime.datetime.utcnow()
    
    # 計算運行時間
    if bot_status["is_ready"]:
        bot_status["uptime"] = int((datetime.datetime.utcnow() - bot_start_time).total_seconds())
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "bot_ready": bot_status["is_ready"],
            "active_voice_sessions": bot_status["active_sessions"],
            "uptime_seconds": bot_status["uptime"],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )

@app.get("/ping")
def ping():
    """簡單的 ping 端點"""
    return {"ping": "pong", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/status")
def status():
    """詳細狀態 - 用於監控"""
    return {
        "bot_status": "online" if bot_status["is_ready"] else "starting",
        "active_voice_sessions": bot_status["active_sessions"],
        "session_details": len(voice_sessions),
        "uptime_seconds": bot_status["uptime"],
        "last_health_check": bot_status["last_check"].isoformat()
    }

def run_web():
    """啟動 FastAPI Web Service"""
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 FastAPI 啟動於 Port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

# =========================
# Discord Bot 設定
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
voice_sessions = {}
bot_start_time = None

# =========================
# Discord 事件處理
# =========================
@bot.event
async def on_ready():
    global bot_start_time
    bot_start_time = datetime.datetime.utcnow()
    
    print(f"✅ 已登入：{bot.user}")
    print(f"📡 伺服器 ID: {GUILD_ID}")
    print(f"📝 記錄頻道 ID: {LOG_CHANNEL_ID}")
    
    # 檢查啟動時已在語音頻道的用戶（不發送訊息）
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"🔍 檢查伺服器「{guild.name}」")
        user_count = 0
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:
                if not member.bot and member.id not in voice_sessions:
                    voice_sessions[member.id] = {
                        "join_time": datetime.datetime.utcnow(),
                        "topic": None,
                        "channel_name": voice_channel.name
                    }
                    print(f"   👤 {member.display_name} 在 {voice_channel.name}")
                    user_count += 1
        
        bot_status["active_sessions"] = len(voice_sessions)
        
        if user_count == 0:
            print("   ℹ️  目前無人在語音頻道")
        else:
            print(f"   ✅ 追蹤 {user_count} 位用戶")
    
    # 同步 Slash 指令（關鍵修正）
    print("\n🔄 同步指令中...")
    try:
        # 方法 1：同步到特定伺服器（立即生效）
        guild_obj = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ 同步成功: {len(synced)} 個指令")
        
        # 如果沒有同步到任何指令，嘗試全域同步
        if len(synced) == 0:
            print("⚠️  伺服器同步失敗，嘗試全域同步...")
            synced = await bot.tree.sync()
            print(f"✅ 全域同步: {len(synced)} 個指令")
            
    except discord.HTTPException as e:
        print(f"❌ HTTP錯誤: {e.status} - {e.text}")
        # 如果伺服器同步失敗，嘗試全域同步
        try:
            synced = await bot.tree.sync()
            print(f"✅ 全域同步成功: {len(synced)} 個指令")
        except Exception as e2:
            print(f"❌ 全域同步也失敗: {e2}")
    except Exception as e:
        print(f"❌ 同步失敗: {e}")
    
    bot_status["is_ready"] = True
    print("✨ 機器人就緒！\n")

# 修正：使用 None 作為 guild 參數，或者完全移除
@bot.tree.command(name="record", description="設定本次語音學習主題")
@app_commands.describe(topic="你想紀錄的主題，例如：微積分")
@app_commands.guild_only()
async def record(interaction: discord.Interaction, topic: str):
    user_id = interaction.user.id
    
    if user_id in voice_sessions:
        voice_sessions[user_id]["topic"] = topic
        channel_name = voice_sessions[user_id]["channel_name"]
        await interaction.response.send_message(
            f"✅ 已設定主題為：**{topic}**\n📍 頻道：{channel_name}",
            ephemeral=True
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
    
    if not log_channel:
        print(f"❌ 找不到記錄頻道")
        return

    # 加入語音頻道
    if before.channel is None and after.channel is not None:
        voice_sessions[user_id] = {
            "join_time": datetime.datetime.utcnow(),
            "topic": None,
            "channel_name": after.channel.name
        }
        bot_status["active_sessions"] = len(voice_sessions)
        
        print(f"➕ {member.display_name} 加入 {after.channel.name}")
        
        try:
            await log_channel.send(
                f"⚠️ 注意！ **{member.display_name}** 已加入語音室 `{after.channel.name}`",
                silent=False
            )
        except Exception as e:
            print(f"❌ 發送加入通知失敗: {e}")

    # 離開語音頻道
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
            
            print(f"➖ {member.display_name} 離開 {channel_name} ({time_str})")
            
            try:
                if topic:
                    await log_channel.send(
                        f"🕐 {member.display_name} 在 {channel_name} **{topic}** {time_str}    好耶 !",
                        silent=True
                    )
                else:
                    await log_channel.send(
                        f"🕐 {member.display_name} 在 {channel_name} 獨自升級 {time_str}    好耶 !",
                        silent=True
                    )
            except Exception as e:
                print(f"❌ 發送離開紀錄失敗: {e}")
            
            del voice_sessions[user_id]
            bot_status["active_sessions"] = len(voice_sessions)
    
    # 切換語音頻道
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        print(f"🔄 {member.display_name}: {before.channel.name} → {after.channel.name}")
        if user_id in voice_sessions:
            voice_sessions[user_id]["channel_name"] = after.channel.name

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ 錯誤: {event}")
    import traceback
    traceback.print_exc()

# =========================
# 主程式啟動
# =========================
if __name__ == "__main__":
    print("🚀 Inside_Curl Discord Bot 啟動中...\n")
    
    # 啟動 FastAPI (背景執行)
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    time.sleep(1.5)
    
    # 啟動 Discord Bot (主執行緒)
    try:
        print("🤖 連接 Discord...\n")
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ 登入失敗：TOKEN 無效")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        import traceback
        traceback.print_exc()

