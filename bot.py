# bot.py
import os
import time
import sqlite3
import asyncio
import logging
import shlex
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

import httpx
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# -----------------------
# LOGGING
# -----------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("jobbot")

# Reduce noisy logs (and avoid long request logs)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# -----------------------
# ENV
# -----------------------
load_dotenv()

DB_PATH = "jobs.db"

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()

ADZUNA_APP_ID = (os.getenv("ADZUNA_APP_ID") or "").strip()
ADZUNA_APP_KEY = (os.getenv("ADZUNA_APP_KEY") or "").strip()
ADZUNA_COUNTRY = (os.getenv("ADZUNA_COUNTRY") or "in").strip()

JOOBLE_API_KEY = (os.getenv("JOOBLE_API_KEY") or "").strip()

# Defaults
DEFAULT_KEYWORDS = "python"
DEFAULT_LOCATION = ""
DEFAULT_SOURCES = "remotive,adzuna"  # jooble auto-available if key set
DEFAULT_INTERVAL_MIN = 30

# Scheduling
POLL_EVERY_SECONDS = 60  # internal tick; user interval enforced in DB

# Limits
MAX_SEND_PER_RUN = 8
MAX_KEYWORDS_PER_RUN = 10
RESULTS_PER_PROVIDER = 25

# Keep dedupe memory for this many days in DB
KEEP_SENT_DAYS = 30


# -----------------------
# DB Helpers + Migration
# -----------------------
def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]  # column name is index 1


def init_db() -> None:
    """
    Creates tables if missing.
    If tables exist with wrong schema (older versions), it drops and recreates them safely.
    """
    conn = _connect_db()

    # USERS table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          chat_id INTEGER PRIMARY KEY,
          keywords TEXT NOT NULL,
          location TEXT,
          sources TEXT NOT NULL,
          interval_min INTEGER NOT NULL DEFAULT 60,
          last_run INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # SENT_JOBS table (with sent_at for cleanup)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_jobs (
          chat_id INTEGER NOT NULL,
          job_uid TEXT NOT NULL,
          sent_at INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (chat_id, job_uid)
        )
        """
    )
    conn.commit()

    # Migration checks: ensure columns exist
    try:
        cols = set(_table_columns(conn, "sent_jobs"))
        expected = {"chat_id", "job_uid", "sent_at"}
        if not expected.issubset(cols):
            logger.warning("Old sent_jobs schema detected. Recreating sent_jobs table...")
            conn.execute("DROP TABLE IF EXISTS sent_jobs")
            conn.execute(
                """
                CREATE TABLE sent_jobs (
                  chat_id INTEGER NOT NULL,
                  job_uid TEXT NOT NULL,
                  sent_at INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY (chat_id, job_uid)
                )
                """
            )
            conn.commit()
    except Exception as e:
        logger.warning("DB migration check failed (sent_jobs): %r", e)

    try:
        cols = set(_table_columns(conn, "users"))
        expected = {"chat_id", "keywords", "location", "sources", "interval_min", "last_run"}
        if not expected.issubset(cols):
            logger.warning("Old users schema detected. Recreating users table (data will be lost)...")
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute(
                """
                CREATE TABLE users (
                  chat_id INTEGER PRIMARY KEY,
                  keywords TEXT NOT NULL,
                  location TEXT,
                  sources TEXT NOT NULL,
                  interval_min INTEGER NOT NULL DEFAULT 60,
                  last_run INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()
    except Exception as e:
        logger.warning("DB migration check failed (users): %r", e)

    conn.close()


def cleanup_sent_jobs() -> None:
    """Keep sent_jobs small by removing entries older than KEEP_SENT_DAYS."""
    cutoff = int(time.time()) - KEEP_SENT_DAYS * 24 * 3600
    conn = _connect_db()
    conn.execute("DELETE FROM sent_jobs WHERE sent_at < ?", (cutoff,))
    conn.commit()
    conn.close()


def upsert_user(chat_id: int, keywords: str, location: str, sources: str, interval_min: int) -> None:
    conn = _connect_db()
    conn.execute(
        """
        INSERT INTO users(chat_id, keywords, location, sources, interval_min, last_run)
        VALUES (?, ?, ?, ?, ?, 0)
        ON CONFLICT(chat_id) DO UPDATE SET
          keywords=excluded.keywords,
          location=excluded.location,
          sources=excluded.sources,
          interval_min=excluded.interval_min
        """,
        (chat_id, keywords, location, sources, interval_min),
    )
    conn.commit()
    conn.close()


def get_user(chat_id: int) -> Optional[Tuple[int, str, str, str, int, int]]:
    conn = _connect_db()
    cur = conn.execute(
        "SELECT chat_id, keywords, location, sources, interval_min, last_run FROM users WHERE chat_id=?",
        (chat_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def list_users() -> List[Tuple[int, str, str, str, int, int]]:
    conn = _connect_db()
    cur = conn.execute("SELECT chat_id, keywords, location, sources, interval_min, last_run FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_last_run(chat_id: int, ts: int) -> None:
    conn = _connect_db()
    conn.execute("UPDATE users SET last_run=? WHERE chat_id=?", (ts, chat_id))
    conn.commit()
    conn.close()


def already_sent(chat_id: int, job_uid: str) -> bool:
    conn = _connect_db()
    cur = conn.execute("SELECT 1 FROM sent_jobs WHERE chat_id=? AND job_uid=?", (chat_id, job_uid))
    ok = cur.fetchone() is not None
    conn.close()
    return ok


def remember_sent(chat_id: int, job_uid: str) -> None:
    conn = _connect_db()
    conn.execute(
        "INSERT OR IGNORE INTO sent_jobs(chat_id, job_uid, sent_at) VALUES (?, ?, ?)",
        (chat_id, job_uid, int(time.time())),
    )
    conn.commit()
    conn.close()


# -----------------------
# Model
# -----------------------
@dataclass
class Job:
    uid: str
    title: str
    company: str
    location: str
    url: str
    source: str
    created_at: Optional[str] = None


# -----------------------
# Providers
# -----------------------
async def fetch_remotive(client: httpx.AsyncClient, keyword: str) -> List[Job]:
    url = "https://remotive.com/api/remote-jobs"
    params = {"search": keyword.strip()} if keyword.strip() else {}
    r = await client.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    jobs: List[Job] = []
    for j in data.get("jobs", [])[:RESULTS_PER_PROVIDER]:
        jobs.append(
            Job(
                uid=f"remotive:{j.get('id')}",
                title=(j.get("title") or "").strip(),
                company=(j.get("company_name") or "").strip(),
                location=(j.get("candidate_required_location") or "Remote/Unspecified").strip(),
                url=(j.get("url") or "").strip(),
                source="Remotive",
                created_at=j.get("publication_date"),
            )
        )
    return jobs


async def fetch_adzuna(client: httpx.AsyncClient, keyword: str, where: str) -> List[Job]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    base = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    params: Dict[str, Any] = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": RESULTS_PER_PROVIDER,
        "content-type": "application/json",
        "sort_by": "date",  # fresher jobs
    }
    if keyword.strip():
        params["what"] = keyword.strip()
    if where.strip():
        params["where"] = where.strip()

    r = await client.get(base, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    jobs: List[Job] = []
    for j in data.get("results", [])[:RESULTS_PER_PROVIDER]:
        company = (j.get("company") or {}).get("display_name", "") or ""
        loc = (j.get("location") or {}).get("display_name", "") or ""
        jobs.append(
            Job(
                uid=f"adzuna:{j.get('id')}",
                title=(j.get("title") or "").strip(),
                company=company.strip(),
                location=(loc.strip() or where.strip() or "Unspecified"),
                url=(j.get("redirect_url") or "").strip(),
                source="Adzuna",
                created_at=j.get("created"),
            )
        )
    return jobs


async def fetch_jooble(client: httpx.AsyncClient, keyword: str, location: str) -> List[Job]:
    if not JOOBLE_API_KEY:
        return []

    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    payload = {
        "keywords": keyword.strip(),
        "location": location.strip(),
        "page": "1",
    }
    r = await client.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    jobs: List[Job] = []
    for j in data.get("jobs", [])[:RESULTS_PER_PROVIDER]:
        jobs.append(
            Job(
                uid=f"jooble:{j.get('id')}",
                title=(j.get("title") or "").strip(),
                company=(j.get("company") or "").strip(),
                location=(j.get("location") or "").strip(),
                url=(j.get("link") or "").strip(),
                source=f"Jooble ({j.get('source','')})".strip(),
                created_at=j.get("updated"),
            )
        )
    return jobs


# -----------------------
# Utils
# -----------------------
def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_job(job: Job) -> str:
    created = f"\n🕒 <i>{esc(job.created_at)}</i>" if job.created_at else ""
    return (
        f"💼 <b>{esc(job.title)}</b>\n"
        f"🏢 {esc(job.company or 'Unknown')}\n"
        f"📍 {esc(job.location or 'Unspecified')}{created}\n"
        f"🔗 <a href=\"{job.url}\">Apply / View</a>\n"
        f"🏷️ <i>Source: {esc(job.source)}</i>"
    )


def available_sources() -> List[str]:
    s = ["remotive"]
    if ADZUNA_APP_ID and ADZUNA_APP_KEY:
        s.append("adzuna")
    if JOOBLE_API_KEY:
        s.append("jooble")
    return s


def parse_set_args(text: str) -> Dict[str, str]:
    """
    Supports:
    /set keyword=python,java location=Bangalore sources=remotive,adzuna interval=30
    Also supports quotes:
    /set location="New Delhi"
    """
    parts = shlex.split(text)
    out: Dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def normalize_sources(sources_csv: str) -> str:
    allowed = set(available_sources())
    srcs = [s.strip().lower() for s in sources_csv.split(",") if s.strip().lower() in allowed]
    if not srcs:
        # fallback
        srcs = [s for s in DEFAULT_SOURCES.split(",") if s in allowed] or ["remotive"]
    return ",".join(srcs)


def parse_keywords_csv(keywords_csv: str) -> List[str]:
    kws = [k.strip() for k in (keywords_csv or "").split(",") if k.strip()]
    # if user wrote "all" or empty -> broad search
    if not kws or (len(kws) == 1 and kws[0].lower() in {"all", "*"}):
        return [""]
    return kws[:MAX_KEYWORDS_PER_RUN]


def keyword_match_any(job: Job, keywords_csv: str) -> bool:
    kws = [k.strip().lower() for k in (keywords_csv or "").split(",") if k.strip()]
    if not kws:
        return True
    hay = f"{job.title} {job.company} {job.location}".lower()
    return any(k in hay for k in kws)


# -----------------------
# Telegram Commands
# -----------------------
HELP_TEXT = (
    "✅ <b>Job Alert Bot</b>\n\n"
    "<b>Commands</b>\n"
    "• /set keyword=python,java,react location=Bangalore sources=remotive,adzuna interval=30\n"
    "• /status\n"
    "• /now\n"
    "• /ping\n"
    "• /sources\n\n"
    "<b>Tips</b>\n"
    "• Multiple tech: keyword=python,java,react,node,flutter,devops\n"
    "• All tech (broad): keyword=all\n"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not get_user(chat_id):
        upsert_user(chat_id, DEFAULT_KEYWORDS, DEFAULT_LOCATION, normalize_sources(DEFAULT_SOURCES), DEFAULT_INTERVAL_MIN)

    await update.message.reply_text(
        HELP_TEXT + f"\nAvailable sources: <b>{', '.join(available_sources())}</b>",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ Bot is alive!")


async def sources_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Available sources: <b>{', '.join(available_sources())}</b>",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    row = get_user(chat_id)
    if not row:
        await update.message.reply_text("Run /start first.")
        return

    _, keywords, location, sources, interval_min, last_run = row
    last_run_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_run)) if last_run else "Never"

    await update.message.reply_text(
        (
            "🧾 <b>Your settings</b>\n"
            f"• keywords: <code>{esc(keywords)}</code>\n"
            f"• location: <code>{esc(location)}</code>\n"
            f"• sources: <code>{esc(sources)}</code>\n"
            f"• interval: <code>{interval_min}</code> min\n"
            f"• last run: <code>{last_run_str}</code>"
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    args = parse_set_args(update.message.text or "")

    keywords = args.get("keyword") or args.get("keywords") or DEFAULT_KEYWORDS
    location = args.get("location") or DEFAULT_LOCATION
    sources = normalize_sources(args.get("sources") or DEFAULT_SOURCES)

    interval_raw = args.get("interval") or str(DEFAULT_INTERVAL_MIN)
    try:
        interval_min = max(5, min(720, int(interval_raw)))
    except ValueError:
        interval_min = DEFAULT_INTERVAL_MIN

    upsert_user(chat_id, keywords, location, sources, interval_min)
    await update.message.reply_text("✅ Saved! Now run /now", disable_web_page_preview=True)


async def now_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    row = get_user(chat_id)
    if not row:
        await update.message.reply_text("Run /start first.")
        return

    await update.message.reply_text("🔎 Fetching jobs...", disable_web_page_preview=True)
    try:
        await fetch_and_send_for_user(context, row, force=True)
    except Exception as e:
        logger.exception("Error in /now: %r", e)
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Handler error: %r", context.error)


# -----------------------
# Scheduler / Fetch
# -----------------------
async def poll_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    cleanup_sent_jobs()
    users = list_users()
    for row in users:
        try:
            await fetch_and_send_for_user(context, row, force=False)
        except Exception as e:
            logger.warning("poll_job error for user: %r", e)


async def fetch_and_send_for_user(context: ContextTypes.DEFAULT_TYPE, row, force: bool) -> None:
    chat_id, keywords_csv, location, sources_csv, interval_min, last_run = row
    now = int(time.time())

    if not force and now - int(last_run) < int(interval_min) * 60:
        return

    sources_list = [s.strip().lower() for s in (sources_csv or "").split(",") if s.strip()]
    keywords_list = parse_keywords_csv(keywords_csv)

    jobs: List[Job] = []

    async with httpx.AsyncClient(headers={"User-Agent": "JobAlertBot/1.0"}) as client:
        tasks = []

        for kw in keywords_list:
            # Search each keyword separately (better results vs all words combined)
            if "remotive" in sources_list:
                tasks.append(fetch_remotive(client, kw))
            if "adzuna" in sources_list:
                tasks.append(fetch_adzuna(client, kw, location))
            if "jooble" in sources_list:
                tasks.append(fetch_jooble(client, kw, location))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                logger.warning("Provider error: %r", res)
                continue
            jobs.extend(res)

    # Deduplicate within run
    uniq: Dict[str, Job] = {}
    for j in jobs:
        if not j.url:
            continue
        uniq[j.uid] = j
    jobs = list(uniq.values())

    # Filter (if keywords specified)
    # If user set keyword=all -> keywords_list = [""] so we skip strict filter and allow all
    if keywords_list != [""]:
        jobs = [j for j in jobs if keyword_match_any(j, keywords_csv)]

    # Only send new ones
    new_jobs: List[Job] = []
    for j in jobs:
        if already_sent(chat_id, j.uid):
            continue
        new_jobs.append(j)

    if not new_jobs:
        if force:
            await context.bot.send_message(chat_id=chat_id, text="No new matching jobs right now 🙂")
        mark_last_run(chat_id, now)
        return

    # Send limited jobs per run to avoid spam
    sent_count = 0
    for j in new_jobs[:MAX_SEND_PER_RUN]:
        await context.bot.send_message(
            chat_id=chat_id,
            text=fmt_job(j),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        remember_sent(chat_id, j.uid)
        sent_count += 1

    mark_last_run(chat_id, now)

    if force:
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Sent {sent_count} jobs.")


# -----------------------
# Main
# -----------------------
def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("❌ Missing TELEGRAM_BOT_TOKEN in .env")

    init_db()

    logger.info("Starting bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("sources", sources_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("set", set_cmd))
    app.add_handler(CommandHandler("now", now_cmd))

    app.add_error_handler(on_error)

    # Scheduler
    app.job_queue.run_repeating(poll_job, interval=POLL_EVERY_SECONDS, first=5)

    logger.info("Bot is running. Open Telegram and type /start")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
