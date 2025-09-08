import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from services.alpha_vantage import fetch_fx
from strategies.rsi import rsi_signals

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_IDS = [c for c in os.getenv("ADMIN_CHAT_IDS", "").split(",") if c.strip()]
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "5"))
RSI_LOW = float(os.getenv("RSI_LOW", "30"))
RSI_HIGH = float(os.getenv("RSI_HIGH", "70"))

SUBS_FILE = "subscriptions.json"

def load_subs():
    if not os.path.exists(SUBS_FILE):
        return {"pairs": ["EURUSD", "GBPUSD", "USDJPY"], "interval": "5min", "chats": []}
    with open(SUBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_subs(data):
    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(chat_id: int) -> bool:
    if not ADMIN_CHAT_IDS:
        return True  # open access if not set
    return str(chat_id) in ADMIN_CHAT_IDS

async def send_signal(context: ContextTypes.DEFAULT_TYPE, chat_id: int, symbol: str, text: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"📣 *Signal* | {symbol}\n{ts}\n{text}"
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.MARKDOWN)

async def check_signals_job(context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    pairs = subs.get("pairs", [])
    interval = subs.get("interval", "5min")
    chats = subs.get("chats", [])

    if not chats:
        return

    for symbol in pairs:
        try:
            df = fetch_fx(symbol, interval=interval)
            signal = rsi_signals(df, low=RSI_LOW, high=RSI_HIGH)
            if signal:
                for chat_id in chats:
                    await send_signal(context, chat_id, symbol, signal)
        except Exception as e:
            logger.exception(f"Error on {symbol}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً! هذا بوت إشارات فوركس بالـ RSI.\n"
        "أوامر متاحة:\n"
        "/subscribe — اشترك بالاشعارات\n"
        "/unsubscribe — إلغاء الاشتراك\n"
        "/pairs — عرض/تعديل الأزواج\n"
        "/status — الحالة الحالية\n"
        "/test — إرسال إشارة تجريبية"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        return await update.message.reply_text("غير مصرح. اطلب الإضافة من الأدمن.")
    subs = load_subs()
    if chat_id not in subs["chats"]:
        subs["chats"].append(chat_id)
        save_subs(subs)
    await update.message.reply_text("تم الاشتراك ✅")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_subs()
    if chat_id in subs["chats"]:
        subs["chats"].remove(chat_id)
        save_subs(subs)
    await update.message.reply_text("تم إلغاء الاشتراك ✅")

async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    if context.args:
        chat_id = update.effective_chat.id
        if not is_admin(chat_id):
            return await update.message.reply_text("غير مصرح بتعديل الأزواج.")
        pairs = [p.upper() for p in context.args]
        subs["pairs"] = pairs
        save_subs(subs)
        return await update.message.reply_text(f"تم التحديث. الأزواج: {', '.join(pairs)}")
    await update.message.reply_text(f"الأزواج الحالية: {', '.join(subs.get('pairs', []))}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    info = {
        "pairs": subs.get("pairs", []),
        "interval": subs.get("interval", "5min"),
        "subscribers": len(subs.get("chats", [])),
        "RSI_LOW": RSI_LOW,
        "RSI_HIGH": RSI_HIGH,
        "interval_minutes": INTERVAL_MINUTES,
    }
    await update.message.reply_text(f"الحالة: {info}")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    for chat_id in subs.get("chats", []):
        await send_signal(context, chat_id, "EURUSD", "اختبار إشارة ✅")
    await update.message.reply_text("تم إرسال اختبار.")

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("pairs", pairs))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("test", test))

    # JobQueue for periodic checks
    app.job_queue.run_repeating(check_signals_job, interval=INTERVAL_MINUTES * 60, first=10)

    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
