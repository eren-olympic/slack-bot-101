# Slack Bot 101 + Dify

Slack Bot 整合 Dify 作為 LLM 聊天後端。

## 功能總覽

### Commands

| Command | 說明 | 可見性 |
|---------|------|--------|
| `/ask [問題]` | 公開問 AI | 全頻道 |
| `/ask-private [問題]` | 私密問 AI | 只有自己 |
| `/reset` | 清除 DM 對話歷史 | 只有自己 |
| `/help` | 顯示指令說明 | 只有自己 |

### 對話方式

| 方式 | 說明 | 多輪對話 |
|------|------|----------|
| DM 私訊 Bot | 直接傳訊息，最自然 | ✅ |
| @Bot 在頻道 | 公開提問 | ✅（Thread 內） |
| Thread 回覆 | 延續既有對話 | ✅ |

### Emoji 快捷觸發

對任何訊息加上 emoji，Bot 自動處理並回覆在 thread：

| Emoji | 動作 |
|-------|------|
| 📝 `:memo:` | 摘要 |
| 🇺🇸 `:flag-us:` | 翻譯成英文 |
| 🇯🇵 `:flag-jp:` | 翻譯成日文 |
| 🇹🇼 `:flag-tw:` | 翻譯成繁體中文 |
| ❓ `:question:` | 解釋內容 |

---

## Slack App 設定

### Step 1：建立 App & Socket Mode

1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. 左側 **App Home** → 設定 **App Display Name**（必填！）
3. 左側 **Socket Mode** → 啟用 → 建立 App-Level Token（scope: `connections:write`）
4. 複製 `xapp-...` token → `SLACK_APP_TOKEN`

### Step 2：Bot Token Scopes

左側 **OAuth & Permissions** → **Bot Token Scopes** 加入：

```
chat:write          # 發送訊息
commands            # Slash Commands
app_mentions:read   # 讀取 @mention
channels:history    # 讀取頻道訊息（Emoji 觸發需要）
groups:history      # 讀取私人頻道訊息
im:history          # 讀取 DM 訊息
im:write            # 發送 DM
reactions:read      # 讀取 emoji reactions
```

### Step 3：安裝 App

**OAuth & Permissions** → **Install to Workspace** → 複製 `xoxb-...` token → `SLACK_BOT_TOKEN`

### Step 4：建立 Slash Commands

左側 **Slash Commands** → 建立以下指令：

| Command | Description | Usage Hint |
|---------|-------------|------------|
| `/ask` | 公開問 AI | `[問題]` |
| `/ask-private` | 私密問 AI | `[問題]` |
| `/reset` | 清除對話歷史 | |
| `/help` | 顯示指令說明 | |
| `/hello` | 打招呼 | `[訊息]` |

### Step 5：訂閱 Events

左側 **Event Subscriptions** → 啟用 → **Subscribe to bot events** 加入：

```
app_mention         # @Bot 觸發
message.channels    # 頻道訊息（Thread 延續）
message.groups      # 私人頻道訊息
message.im          # DM 訊息（多輪對話）
reaction_added      # Emoji 觸發
```

→ **Save Changes**

---

## Dify 設定

1. 建立 Chat App
2. **API Access** → 複製 `app-...` API Key → `DIFY_API_KEY`

---

## 本地執行

```bash
# 切到專案目錄
cd slack-bot-101

# 複製環境變數
cp .env.example .env

# 編輯 .env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
DIFY_API_KEY=app-...

# 安裝依賴
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 啟動
python app.py
```

---

## 測試 Checklist

```
□ /help                    → 顯示指令說明
□ /ask 你好                → 頻道公開顯示問答
□ /ask-private 你好        → 只有自己看到
□ DM Bot「你好」           → Bot 回覆
□ DM Bot「我叫小明」       → Bot 記住
□ DM Bot「我叫什麼？」     → Bot 回答「小明」
□ /reset                   → 清除 DM 對話
□ @Bot 你好                → Thread 回覆
□ 任意訊息加 📝            → Bot 在 Thread 回覆摘要
□ 任意訊息加 🇺🇸            → Bot 翻譯成英文
```

---

## 專案結構

```
slack-bot-101/
├── app.py           # Bot 主程式
├── dify_client.py   # Dify API 客戶端
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 常見問題

### Emoji 觸發沒反應？

1. 確認有 `reactions:read` scope
2. 確認有訂閱 `reaction_added` event
3. 確認有 `channels:history` scope（要讀取訊息內容）
4. 改完 scope 要 **Reinstall App**

### DM 沒反應？

1. 確認有 `im:history` 和 `im:write` scope
2. 確認有訂閱 `message.im` event

### Bot 忘記對話內容？

- DM 對話：用 `/reset` 清除後會重新開始
- Thread 對話：重啟 Bot 會清除（記憶體儲存）
- 正式環境建議用 Redis 持久化

---

## 下一步

- [ ] Redis 持久化對話
- [ ] 「思考中...」狀態提示
- [ ] Block Kit 美化訊息
- [ ] 更多 Emoji 動作
- [ ] 部署到雲端

---

## Changelog

### feat/v2-dm-reactions

- 新增 `/ask-private` 私密問答
- 新增 `/reset` 清除 DM 對話歷史
- 新增 `/help` 指令說明
- 新增 DM 多輪對話
- 新增 Emoji 觸發（📝 🇺🇸 🇯🇵 🇹🇼 ❓）
- `/ask` 改為公開顯示問題和回答
- 所有回覆加上 `responding...` 狀態提示
- 支援 Slack Assistant 模式（每個 thread 獨立追蹤對話上下文）
