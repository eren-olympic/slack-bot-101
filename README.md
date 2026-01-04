# Slack Bot 101 + Dify

使用 Python + Bolt SDK + Socket Mode 的 Slack Bot，整合 Dify 作為 LLM 聊天後端。

## 專案結構

```
slack-bot-101/
├── .env.example     # 環境變數範本
├── .env             # 你的實際環境變數（不會進 git）
├── .gitignore
├── app.py           # Bot 主程式
├── dify_client.py   # Dify API 客戶端
├── requirements.txt
└── README.md
```

## 功能

| 指令 / 動作 | 說明 |
|------------|------|
| `/hello [訊息]` | Slash command 打招呼 |
| `/ask [問題]` | 直接問 Dify（單次對話，不保留上下文） |
| `@bot [問題]` | 開始 Dify 對話，在 thread 中延續上下文 |
| `ping` | 回應 pong |

### 對話上下文機制

```
用戶: @bot 你好，我叫小明
Bot: 你好小明！有什麼可以幫你的？
        │
        └── 在這個 thread 中繼續對話 ──┐
                                        │
用戶: 我剛才說我叫什麼？                │
Bot: 你說你叫小明。  ◀─────────────────┘
     （Dify 記得上下文）
```

---

## 設定步驟

### Part 1：Slack App 設定

#### Step 1：建立 Slack App

1. 前往 [Slack API: Your Apps](https://api.slack.com/apps)
2. 點擊 **Create New App** > **From scratch**
3. 輸入 App Name，選擇 Workspace
4. 點擊 **Create App**

#### Step 2：啟用 Socket Mode

1. 左側選單 **Socket Mode**
2. 開啟 **Enable Socket Mode**
3. 建立 App-Level Token：
   - Token Name：`socket-token`
   - Scope：`connections:write`
4. **複製 Token**（`xapp-...`）→ 這是 `SLACK_APP_TOKEN`

#### Step 3：設定 Bot Token Scopes

1. 左側選單 **OAuth & Permissions**
2. **Bot Token Scopes** 加入：

| Scope | 用途 |
|-------|------|
| `chat:write` | 發送訊息 |
| `commands` | Slash Commands |
| `app_mentions:read` | 讀取 @mention |
| `channels:history` | 讀取公開頻道訊息 |
| `groups:history` | 讀取私人頻道訊息（可選） |
| `im:history` | 讀取私訊（可選） |

#### Step 4：安裝 App

1. **OAuth & Permissions** 頁面上方
2. 點擊 **Install to Workspace**
3. 授權後，**複製 Bot User OAuth Token**（`xoxb-...`）→ 這是 `SLACK_BOT_TOKEN`

#### Step 5：建立 Slash Commands

1. 左側選單 **Slash Commands**
2. **Create New Command**：

| Command | Description | Usage Hint |
|---------|-------------|------------|
| `/hello` | 打招呼 | `[訊息]` |
| `/ask` | 問 AI | `[問題]` |

#### Step 6：訂閱 Events

1. 左側選單 **Event Subscriptions**
2. 開啟 **Enable Events**
3. **Subscribe to bot events** 加入：
   - `app_mention`
   - `message.channels`
   - `message.groups`（可選）
   - `message.im`（可選）
4. **Save Changes**

---

### Part 2：Dify 設定

#### Step 1：建立 Dify App

1. 登入 [Dify](https://dify.ai) 或你的自架實例
2. 建立一個 **Chat App**（聊天助手）
3. 設定好 Prompt、模型等

#### Step 2：取得 API Key

1. 進入你的 App
2. 左側選單 **API Access**（或 **發布** > **API**）
3. 複製 **API Key**（`app-...`）→ 這是 `DIFY_API_KEY`

#### Step 3：確認 Base URL

- **Dify Cloud**: `https://api.dify.ai/v1`（預設，不用改）
- **自架 Dify**: 填入你的 API URL，例如 `https://your-dify.com/v1`

---

### Part 3：本地設定

```bash
# 1. Clone 專案（或下載檔案）
cd slack-bot-101

# 2. 複製環境變數範本
cp .env.example .env

# 3. 編輯 .env，填入 Token
#    SLACK_BOT_TOKEN=xoxb-...
#    SLACK_APP_TOKEN=xapp-...
#    DIFY_API_KEY=app-...
#    DIFY_BASE_URL=https://api.dify.ai/v1  （如果是自架 Dify）

# 4. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 5. 安裝依賴
pip install -r requirements.txt

# 6. 啟動 Bot
python app.py
```

---

### Part 4：測試

1. 看到終端顯示 `⚡ Slack Bot 啟動中...`
2. 到 Slack：
   - `/invite @你的bot` 邀請進頻道
   - `/hello` 測試基本功能
   - `/ask 什麼是 Python？` 測試單次 Dify 對話
   - `@你的bot 你好` 測試持續對話（在 thread 中繼續聊）

---

## 常見問題

### Bot 沒有回應？

1. **確認 Bot 在頻道中**：`/invite @botname`
2. **確認 Token 正確**：檢查 `.env` 三個 Token
3. **確認 Dify App 已發布**：Draft 狀態的 App 可能無法呼叫

### `DIFY_API_KEY is required` 錯誤？

`.env` 檔案中沒有設定 `DIFY_API_KEY`，或檔案沒有正確載入。

### Dify 回應很慢？

1. 可能是模型本身的回應時間
2. 檢查 Dify App 的模型設定
3. 考慮使用更快的模型（如 GPT-3.5 vs GPT-4）

### Thread 對話沒有上下文？

確認：
1. 是從 `@bot` 開始的對話
2. Bot 有回應過（建立了 conversation_id）
3. 後續訊息在同一個 thread 中

### 如何清除對話上下文？

目前對話上下文存在記憶體中，重啟 Bot 就會清除。
正式環境建議用 Redis 儲存，並加入 `/reset` 指令。

---

## 架構說明

```
┌─────────────────────────────────────────────────────────┐
│                        Slack                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ /hello   │  │ /ask     │  │ @bot (thread 對話)   │  │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘  │
└───────┼─────────────┼───────────────────┼──────────────┘
        │             │                   │
        ▼             ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│                    Slack Bot (app.py)                   │
│                                                         │
│  • Socket Mode 連線                                     │
│  • 事件處理（mention, message, command）                │
│  • Thread → Conversation ID 對應                        │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Dify Client (dify_client.py)           │
│                                                         │
│  • Streaming / Blocking 模式                            │
│  • 對話上下文管理 (conversation_id)                     │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      Dify API                           │
│                                                         │
│  POST /chat-messages                                    │
│  • query, user, conversation_id                         │
│  • response_mode: streaming                             │
└─────────────────────────────────────────────────────────┘
```

---

## 下一步

- [ ] 加入「正在輸入」狀態提示
- [ ] 用 Redis 持久化 conversation mapping
- [ ] 加入 `/reset` 指令清除對話
- [ ] 支援檔案上傳到 Dify
- [ ] 使用 Block Kit 美化回應
- [ ] 加入錯誤重試機制
- [ ] 部署到雲端（Railway / Cloud Run）

---

## 參考資源

- [Slack Bolt for Python](https://slack.dev/bolt-python/)
- [Dify API 文件](https://docs.dify.ai/)
- [Block Kit Builder](https://app.slack.com/block-kit-builder)
