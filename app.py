import os
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dify_client import DifyClient

# 載入 .env 環境變數
load_dotenv()

# 初始化 Slack App
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# 初始化 Dify Client
dify = DifyClient()

# 儲存 Slack thread -> Dify conversation_id 的對應
# 正式環境建議用 Redis 或資料庫
thread_conversations: dict[str, str] = {}


def get_thread_key(channel: str, thread_ts: str) -> str:
    """產生 thread 唯一 key"""
    return f"{channel}:{thread_ts}"


def clean_mention(text: str, bot_user_id: str) -> str:
    """移除訊息中的 @bot mention"""
    # 移除 <@U12345> 格式的 mention
    cleaned = re.sub(rf"<@{bot_user_id}>", "", text)
    return cleaned.strip()


# ============================================
# Slash Command: /hello
# ============================================
@app.command("/hello")
def handle_hello_command(ack, command, respond):
    """
    處理 /hello 指令
    """
    ack()

    user_id = command["user_id"]
    text = command.get("text", "").strip()

    if text:
        respond(f"👋 <@{user_id}> 說：{text}")
    else:
        respond(f"👋 哈囉 <@{user_id}>！歡迎使用 Slack Bot 101")


# ============================================
# Slash Command: /ask - 直接問 Dify
# ============================================
@app.command("/ask")
def handle_ask_command(ack, command, respond, client):
    """
    處理 /ask 指令 - 發送問題給 Dify
    """
    ack()

    user_id = command["user_id"]
    query = command.get("text", "").strip()

    if not query:
        respond("請輸入問題，例如：`/ask 什麼是機器學習？`")
        return

    try:
        # 發送到 Dify（不帶 conversation_id，每次都是新對話）
        answer, _ = dify.chat_complete(
            query=query,
            user=user_id,
            stream=True,
        )

        respond(f"*問題：* {query}\n\n{answer}")

    except Exception as e:
        respond(f"❌ 發生錯誤：{str(e)}")


# ============================================
# 監聽 @mention - 主要聊天入口
# ============================================
@app.event("app_mention")
def handle_mention(event, say, client):
    """
    當有人 @bot 時，將訊息發送到 Dify 並回覆
    使用 thread 來維持對話上下文
    """
    user_id = event["user"]
    channel = event["channel"]
    text = event.get("text", "")
    message_ts = event["ts"]

    # 判斷是否在 thread 中
    thread_ts = event.get("thread_ts", message_ts)

    # 取得 bot 的 user_id 來清理 mention
    auth_response = client.auth_test()
    bot_user_id = auth_response["user_id"]

    # 清理訊息，移除 @mention
    query = clean_mention(text, bot_user_id)

    if not query:
        say(
            text="請告訴我你想問什麼 🤔",
            thread_ts=thread_ts,
        )
        return

    # 查找是否有既存的 Dify conversation
    thread_key = get_thread_key(channel, thread_ts)
    conversation_id = thread_conversations.get(thread_key)

    try:
        # 顯示「正在輸入」狀態（可選）
        # client.chat_postMessage(channel=channel, thread_ts=thread_ts, text="思考中...")

        # 發送到 Dify
        answer, new_conversation_id = dify.chat_complete(
            query=query,
            user=user_id,
            conversation_id=conversation_id,
            stream=True,
        )

        # 儲存 conversation_id 供後續使用
        if new_conversation_id:
            thread_conversations[thread_key] = new_conversation_id

        # 回覆到同一個 thread
        say(
            text=answer,
            thread_ts=thread_ts,
        )

    except Exception as e:
        say(
            text=f"❌ 抱歉，發生錯誤：{str(e)}",
            thread_ts=thread_ts,
        )


# ============================================
# 監聽 thread 回覆（延續對話）
# ============================================
@app.event("message")
def handle_message(event, say, client, logger):
    """
    監聽訊息事件
    - 如果是在有 Dify 對話的 thread 中，自動回覆
    - 忽略 bot 自己的訊息
    """
    # 忽略 bot 訊息、子類型訊息（如 message_changed）
    if event.get("bot_id") or event.get("subtype"):
        return

    # 只處理 thread 回覆
    thread_ts = event.get("thread_ts")
    if not thread_ts:
        return

    channel = event["channel"]
    user_id = event["user"]
    text = event.get("text", "").strip()

    # 檢查這個 thread 是否有對應的 Dify 對話
    thread_key = get_thread_key(channel, thread_ts)
    conversation_id = thread_conversations.get(thread_key)

    if not conversation_id:
        # 沒有對應的對話，忽略
        return

    # 取得 bot user_id
    auth_response = client.auth_test()
    bot_user_id = auth_response["user_id"]

    # 清理 mention（如果有的話）
    query = clean_mention(text, bot_user_id)

    if not query:
        return

    try:
        # 發送到 Dify，延續對話
        answer, new_conversation_id = dify.chat_complete(
            query=query,
            user=user_id,
            conversation_id=conversation_id,
            stream=True,
        )

        # 更新 conversation_id（通常不變）
        if new_conversation_id:
            thread_conversations[thread_key] = new_conversation_id

        say(
            text=answer,
            thread_ts=thread_ts,
        )

    except Exception as e:
        logger.error(f"Dify error: {e}")
        say(
            text=f"❌ 抱歉，發生錯誤：{str(e)}",
            thread_ts=thread_ts,
        )


# ============================================
# 監聽關鍵字（保留原有功能）
# ============================================
@app.message("ping")
def handle_ping(message, say):
    """當訊息包含 "ping" 時回應 "pong"（不走 Dify）"""
    say("pong 🏓")


# ============================================
# 啟動 Bot
# ============================================
if __name__ == "__main__":
    print("⚡ Slack Bot 啟動中...")
    print("📝 已註冊功能：")
    print("   - /hello [訊息] - 打招呼指令")
    print("   - /ask [問題] - 直接問 Dify（單次對話）")
    print("   - @bot [問題] - 開始 Dify 對話（thread 中可延續）")
    print("   - ping - 回應 pong")
    print("-" * 40)
    print(f"🔗 Dify API: {dify.base_url}")
    print("-" * 40)

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
