import os
import re
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dify_client import DifyClient

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 載入 .env 環境變數
load_dotenv()

# 初始化 Slack App
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# 初始化 Dify Client
dify = DifyClient()

# 儲存對話 ID 的對應
# Key: "dm:{user_id}" 或 "thread:{channel}:{thread_ts}"
# Value: Dify conversation_id
# 正式環境建議用 Redis 或資料庫
conversations: dict[str, str] = {}

# Emoji 對應的動作
# 注意：Slack emoji 名稱可能因 workspace 而異
EMOJI_ACTIONS = {
    # 📝 摘要
    "memo": {
        "action": "summarize",
        "prompt": "請摘要以下內容，用繁體中文回覆：\n\n{text}",
    },
    # 🇺🇸 翻英文（多種可能的名稱）
    "flag-us": {
        "action": "translate",
        "prompt": "請將以下內容翻譯成英文：\n\n{text}",
    },
    "us": {
        "action": "translate",
        "prompt": "請將以下內容翻譯成英文：\n\n{text}",
    },
    # 🇯🇵 翻日文
    "flag-jp": {
        "action": "translate",
        "prompt": "請將以下內容翻譯成日文：\n\n{text}",
    },
    "jp": {
        "action": "translate",
        "prompt": "請將以下內容翻譯成日文：\n\n{text}",
    },
    # 🇹🇼 翻繁中
    "flag-tw": {
        "action": "translate",
        "prompt": "請將以下內容翻譯成繁體中文：\n\n{text}",
    },
    "tw": {
        "action": "translate",
        "prompt": "請將以下內容翻譯成繁體中文：\n\n{text}",
    },
    # ❓ 解釋
    "question": {
        "action": "explain",
        "prompt": "請解釋以下內容，用繁體中文回覆：\n\n{text}",
    },
}


def get_dm_key(user_id: str) -> str:
    """產生 DM 對話的 key"""
    return f"dm:{user_id}"


def get_thread_key(channel: str, thread_ts: str) -> str:
    """產生 thread 對話的 key"""
    return f"thread:{channel}:{thread_ts}"


def clean_mention(text: str, bot_user_id: str) -> str:
    """移除訊息中的 @bot mention"""
    cleaned = re.sub(rf"<@{bot_user_id}>", "", text)
    return cleaned.strip()


def get_bot_user_id(client) -> str:
    """取得 Bot 的 user_id"""
    auth_response = client.auth_test()
    return auth_response["user_id"]


# ============================================
# Slash Command: /help
# ============================================
@app.command("/help")
def handle_help_command(ack, respond):
    """顯示所有可用指令"""
    ack()

    help_text = """
*🤖 Slack Bot 指令說明*

*對話指令*
• `/ask [問題]` - 公開問 AI（所有人可見）
• `/ask-private [問題]` - 私密問 AI（只有你看得到）
• `/reset` - 清除對話歷史

*使用方式*
• *私訊 Bot*：直接傳訊息給我，支援多輪對話
• *在頻道 @Bot*：`@Bot 你的問題` 會公開回覆

*Emoji 快捷鍵*
對任何訊息加上以下 emoji，Bot 會自動處理：
• 📝 `:memo:` - 摘要內容
• 🇺🇸 `:flag-us:` - 翻譯成英文
• 🇯🇵 `:flag-jp:` - 翻譯成日文
• 🇹🇼 `:flag-tw:` - 翻譯成繁體中文
• ❓ `:question:` - 解釋內容

*小提示*
• 使用 Slack Assistant 模式時，每個 thread 是獨立對話
• 開新 thread 即可開始全新對話
• 同一個 thread 內會記住上下文
"""

    respond(help_text)


# ============================================
# Slash Command: /ask（公開）
# ============================================
@app.command("/ask")
def handle_ask_command(ack, command, client, respond):
    """
    公開問 AI - 問題和回答都會顯示在頻道中
    在 DM 中使用時改用 respond
    """
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]
    query = command.get("text", "").strip()

    if not query:
        respond("請輸入問題，例如：`/ask 什麼是機器學習？`")
        return

    try:
        # 嘗試發送到頻道（公開）
        try:
            question_msg = client.chat_postMessage(
                channel=channel_id,
                text=f"*<@{user_id}> 問：*\n{query}",
            )

            responding_msg = client.chat_postMessage(
                channel=channel_id,
                text="_responding..._",
            )

            answer, _ = dify.chat_complete(
                query=query,
                user=user_id,
                stream=True,
            )

            client.chat_update(
                channel=channel_id,
                ts=responding_msg["ts"],
                text=answer,
            )

        except Exception as channel_error:
            # 如果頻道發送失敗（例如在 DM 中），改用 respond
            if "channel_not_found" in str(channel_error):
                answer, _ = dify.chat_complete(
                    query=query,
                    user=user_id,
                    stream=True,
                )
                respond(f"*問題：* {query}\n\n{answer}")
            else:
                raise channel_error

    except Exception as e:
        respond(f"❌ 發生錯誤：{str(e)}")


# ============================================
# Slash Command: /ask-private（私密）
# ============================================
@app.command("/ask-private")
def handle_ask_private_command(ack, command, respond):
    """
    私密問 AI - 只有自己看得到
    """
    ack()

    user_id = command["user_id"]
    query = command.get("text", "").strip()

    if not query:
        respond("請輸入問題，例如：`/ask-private 什麼是機器學習？`")
        return

    try:
        answer, _ = dify.chat_complete(
            query=query,
            user=user_id,
            stream=True,
        )

        respond(f"*問題：* {query}\n\n{answer}")

    except Exception as e:
        respond(f"❌ 發生錯誤：{str(e)}")


# ============================================
# Slash Command: /reset
# ============================================
@app.command("/reset")
def handle_reset_command(ack, command, respond):
    """清除 DM 對話歷史"""
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]
    dm_key = get_dm_key(user_id)

    # 清除一般 DM 對話
    cleared_count = 0
    if dm_key in conversations:
        del conversations[dm_key]
        cleared_count += 1

    # 清除該 channel 下所有 assistant thread 的對話
    assistant_keys = [k for k in conversations.keys() if k.startswith(f"assistant:{channel_id}:")]
    for key in assistant_keys:
        del conversations[key]
        cleared_count += 1

    if cleared_count > 0:
        respond(f"✅ 已清除 {cleared_count} 個對話歷史！\n💡 提示：在 Slack Assistant 模式下，開新 thread 即可開始全新對話。")
    else:
        respond("目前沒有進行中的對話。")


# ============================================
# Slash Command: /hello（保留）
# ============================================
@app.command("/hello")
def handle_hello_command(ack, command, respond):
    """打招呼"""
    ack()

    user_id = command["user_id"]
    text = command.get("text", "").strip()

    if text:
        respond(f"👋 <@{user_id}> 說：{text}")
    else:
        respond(f"👋 哈囉 <@{user_id}>！輸入 `/help` 查看所有指令")


# ============================================
# 監聽 @mention - 公開問答
# ============================================
@app.event("app_mention")
def handle_mention(event, say, client):
    """
    當有人 @bot 時，公開回覆（類似 /ask）
    在 thread 中會保持上下文
    """
    user_id = event["user"]
    channel = event["channel"]
    text = event.get("text", "")
    message_ts = event["ts"]

    # 判斷是否在 thread 中
    thread_ts = event.get("thread_ts", message_ts)

    # 清理訊息
    bot_user_id = get_bot_user_id(client)
    query = clean_mention(text, bot_user_id)

    if not query:
        say(text="請告訴我你想問什麼 🤔", thread_ts=thread_ts)
        return

    # 查找 thread 對話
    thread_key = get_thread_key(channel, thread_ts)
    conversation_id = conversations.get(thread_key)

    try:
        # 顯示 responding 狀態
        responding_msg = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="_responding..._",
        )

        answer, new_conversation_id = dify.chat_complete(
            query=query,
            user=user_id,
            conversation_id=conversation_id,
            stream=True,
        )

        if new_conversation_id:
            conversations[thread_key] = new_conversation_id

        # 更新回答
        client.chat_update(
            channel=channel,
            ts=responding_msg["ts"],
            text=answer,
        )

    except Exception as e:
        say(text=f"❌ 抱歉，發生錯誤：{str(e)}", thread_ts=thread_ts)


# ============================================
# DM 多輪對話
# ============================================
@app.event("message")
def handle_message(event, say, client, logger):
    """
    處理訊息事件：
    1. DM 直接對話（多輪）
    2. Thread 中延續對話
    """
    # Debug: 印出收到的事件
    print(f"\n📨 Message event: channel_type={event.get('channel_type')}, subtype={event.get('subtype')}, bot_id={event.get('bot_id')}")

    # 忽略 bot 訊息、子類型訊息
    if event.get("bot_id") or event.get("subtype"):
        return

    channel_type = event.get("channel_type", "")
    channel = event["channel"]
    user_id = event["user"]
    text = event.get("text", "").strip()

    if not text:
        return

    # ---- DM 對話 ----
    if channel_type == "im":
        # Slack Assistant 模式會自動建立 thread
        # 用 thread_ts 來追蹤每個 assistant thread 的對話
        thread_ts = event.get("thread_ts")
        
        if thread_ts:
            # Assistant thread 模式：用 thread_ts 作為 key
            conv_key = f"assistant:{channel}:{thread_ts}"
            print(f"💬 Assistant thread from user {user_id}: {text[:50]}...")
        else:
            # 一般 DM 模式：用 user_id 作為 key
            conv_key = get_dm_key(user_id)
            print(f"💬 DM received from user {user_id}: {text[:50]}...")
        
        conversation_id = conversations.get(conv_key)
        print(f"   Conv key: {conv_key}, existing conversation: {conversation_id}")

        try:
            # 顯示 responding 狀態
            # Assistant 模式下要回覆到 thread
            msg_kwargs = {"channel": channel, "text": "_responding..._"}
            if thread_ts:
                msg_kwargs["thread_ts"] = thread_ts
            
            responding_msg = client.chat_postMessage(**msg_kwargs)

            answer, new_conversation_id = dify.chat_complete(
                query=text,
                user=user_id,
                conversation_id=conversation_id,
                stream=True,
            )

            if new_conversation_id:
                conversations[conv_key] = new_conversation_id
                print(f"   ✅ Updated conversation_id: {new_conversation_id}")

            # 更新回答
            client.chat_update(
                channel=channel,
                ts=responding_msg["ts"],
                text=answer,
            )

        except Exception as e:
            print(f"   ❌ DM Dify error: {e}")
            logger.error(f"DM Dify error: {e}")
            error_kwargs = {"text": f"❌ 抱歉，發生錯誤：{str(e)}"}
            if thread_ts:
                error_kwargs["thread_ts"] = thread_ts
            say(**error_kwargs)

        return

    # ---- Thread 延續對話 ----
    thread_ts = event.get("thread_ts")
    if not thread_ts:
        return

    thread_key = get_thread_key(channel, thread_ts)
    conversation_id = conversations.get(thread_key)

    if not conversation_id:
        return

    # 清理 mention
    bot_user_id = get_bot_user_id(client)
    query = clean_mention(text, bot_user_id)

    if not query:
        return

    try:
        # 顯示 responding 狀態
        responding_msg = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="_responding..._",
        )

        answer, new_conversation_id = dify.chat_complete(
            query=query,
            user=user_id,
            conversation_id=conversation_id,
            stream=True,
        )

        if new_conversation_id:
            conversations[thread_key] = new_conversation_id

        # 更新回答
        client.chat_update(
            channel=channel,
            ts=responding_msg["ts"],
            text=answer,
        )

    except Exception as e:
        print(f"   ❌ Thread Dify error: {e}")
        logger.error(f"Thread Dify error: {e}")
        say(text=f"❌ 抱歉，發生錯誤：{str(e)}", thread_ts=thread_ts)


# ============================================
# Emoji Reaction 觸發
# ============================================
@app.event("reaction_added")
def handle_reaction(event, client, logger):
    """
    處理 Emoji 觸發：
    📝 摘要、🇺🇸 翻英、🇯🇵 翻日、🇹🇼 翻繁中、❓ 解釋
    """
    reaction = event.get("reaction", "")
    user_id = event.get("user", "")
    item = event.get("item", {})

    # Debug: 印出收到的 emoji 名稱
    print(f"\n😀 Reaction received: '{reaction}'")

    # 檢查是否為支援的 emoji
    if reaction not in EMOJI_ACTIONS:
        print(f"   ⏭️ Reaction '{reaction}' not in supported list, ignoring")
        return

    # 取得訊息資訊
    channel = item.get("channel", "")
    message_ts = item.get("ts", "")

    if not channel or not message_ts:
        return

    try:
        # 取得原始訊息內容
        result = client.conversations_history(
            channel=channel,
            latest=message_ts,
            limit=1,
            inclusive=True,
        )

        messages = result.get("messages", [])
        if not messages:
            return

        original_text = messages[0].get("text", "")
        if not original_text:
            return

        # 組合 prompt
        action_config = EMOJI_ACTIONS[reaction]
        prompt = action_config["prompt"].format(text=original_text)

        # 顯示 responding 狀態
        responding_msg = client.chat_postMessage(
            channel=channel,
            thread_ts=message_ts,
            text="_responding..._",
        )

        # 發送到 Dify
        answer, _ = dify.chat_complete(
            query=prompt,
            user=user_id,
            stream=True,
        )

        # 更新回答
        client.chat_update(
            channel=channel,
            ts=responding_msg["ts"],
            text=answer,
        )

    except Exception as e:
        print(f"   ❌ Reaction handler error: {e}")
        logger.error(f"Reaction handler error: {e}")
        # 發送錯誤訊息給觸發的用戶
        try:
            client.chat_postEphemeral(
                channel=channel,
                user=user_id,
                text=f"❌ 處理 emoji 時發生錯誤：{str(e)}",
            )
        except:
            pass


# ============================================
# 監聽關鍵字（保留原有功能）
# ============================================
@app.message("ping")
def handle_ping(message, say):
    """當訊息包含 ping 時回應 pong"""
    say("pong 🏓")


# ============================================
# 啟動 Bot
# ============================================
if __name__ == "__main__":
    print("⚡ Slack Bot v2 啟動中...")
    print("=" * 50)
    print("📝 Commands:")
    print("   /help              - 顯示指令說明")
    print("   /ask [問題]        - 公開問 AI")
    print("   /ask-private [問題] - 私密問 AI")
    print("   /reset             - 清除 DM 對話歷史")
    print()
    print("💬 對話方式:")
    print("   - DM Bot 直接聊天（多輪對話）")
    print("   - @Bot 在頻道公開提問")
    print("   - Thread 中延續對話")
    print()
    print("😀 Emoji 觸發:")
    print("   📝 摘要 | 🇺🇸 翻英 | 🇯🇵 翻日 | 🇹🇼 翻繁中 | ❓ 解釋")
    print("=" * 50)
    print(f"🔗 Dify API: {dify.base_url}")
    print("=" * 50)

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
