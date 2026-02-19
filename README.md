# Job Alert Bot (Telegram) — All India Tech Jobs 🇮🇳

A **Python + Telegram bot** that sends **job alerts across India** from multiple job providers (API-based).  
Configure keywords, location, sources, and alert interval directly from Telegram.

✅ Works with **Adzuna**, **Jooble**, and **Remotive** (remote jobs).  
✅ Supports **multiple tech keywords** (React, Java, DevOps, ML, etc.)  
✅ Deduplicates jobs using SQLite so you don’t get repeats.

---

## ✨ Features

- 🔔 **Telegram job alerts** (scheduled + manual)
- 🇮🇳 **Location: All over India** (`location=India`)
- 🧠 **Multi-tech search**: `python, java, react, node, flutter, devops...`
- 🧾 **Deduplication** (no duplicate alerts)
- ⏱️ **Interval based alerts** (e.g., every 30 minutes)
- 🧰 Simple commands: `/start`, `/set`, `/status`, `/now`, `/sources`, `/ping`

---

## 🗂️ Project Structure

Job_alert_bot/
-bot.py
-requirements.txt
-.env.example
-gitignore
-jobs.db (auto created, not committed)


---

## ✅ Requirements

- Python **3.10+**
- Telegram Bot token from **@BotFather**
- API keys (optional but recommended):
  - Adzuna (APP_ID + APP_KEY)
  - Jooble (API_KEY)

---

## ⚙️ Setup

### 1) Clone repo
```bash
git clone https://github.com/rishirajdas05/Job_alert_bot.git
cd Job_alert_bot

2) Install dependencies
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

3) Create .env
cp .env.example .env
Fill it like:

TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

ADZUNA_APP_ID=YOUR_ADZUNA_APP_ID
ADZUNA_APP_KEY=YOUR_ADZUNA_APP_KEY
ADZUNA_COUNTRY=in

JOOBLE_API_KEY=YOUR_JOOBLE_API_KEY


▶️ Run the Bot
python bot.py


When you see:
Bot is running. Open Telegram and type /start

Go to your bot chat on Telegram.

🤖 Telegram Commands
/start

Initialize bot + show help.

/set

Configure alerts.

✅ All India Tech Jobs (Recommended)

/set keyword=python,java,javascript,react,node,flutter,android,ios,devops,aws,data,ml,qa location=India sources=adzuna,jooble interval=30


✅ Remote + India

/set keyword=python,react,node,devops,data,ml location=India sources=remotive,adzuna,jooble interval=30


✅ All roles (very broad)

/set keyword=all location=India sources=adzuna,jooble interval=30

/now

Fetch immediately (manual trigger).

/status

Show your current configuration.

/sources

Show sources available based on keys in .env.

/ping

Health check (bot replies “alive”).
