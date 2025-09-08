import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from alpha_vantage import fetch_fx
from rsi import rsi_signals  # يبقى موجود لو حبيت ترجع للوضع البسيط
from pro_strategy import pro_signal_for_pair  # استراتيجية البرو

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── إعدادات من Environment (تقدر تعدلها من Render → Environment) ──
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_IDS = [c for c in os.getenv("ADMIN_CHAT_IDS", "").split(",") if c.strip()]
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "5"))

# إعدادات نسخة البرو
TIMEFRAME = os.getenv("TIMEFRAME", "60min")   # 60min أقوى من 5min
RSI_LOW = float(os.getenv("RSI_LOW", "25"))   # تشبع أعمق
RSI_HIGH = float(os.getenv("RSI_HIGH", "75"))
ATR_MULT = float(os.getenv("ATR_MULT", "1.5"))
RR_RATIO = float(os.getenv("RR_RATIO", "2.0"))

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
        return True
    return str(chat_id) in ADMIN_CHAT_IDS


async def send_signal_text(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)


# ── مهمة التشييك الدورية (نسخة البرو) ──
async def check_signals_job(context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    pairs = subs.get("pairs", [])
    chats = subs.get("chats", [])
    if not chats or not pairs:
        return

    for symbol in pairs:
        try:
            df = fetch_fx(symbol, interval=TIMEFRAME)  # يستخدم الفريم من الإعدادات
            sig = pro_signal_for_pair(
                df,
                rsi_low=RSI_LOW,
                rsi_high=RSI_HIGH,
                atr_mult=ATR_MULT,
                rr_ratio=RR_RATIO
            )
            if sig:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                direction = "BUY ✅" if sig["direction"] == "BUY" else "SELL ❌"
                body = (
                    f"📢 *Pro Signal* | {symbol} ({TIMEFRAME})\n"
                    f"{ts}\n\n"
                    f"🔸 اتجاه: *{direction}*\n"
                    f"RSI={sig['rsi']} | MACD hist {sig['macd_hist_prev']}→{sig['macd_hist']} | EMA200={sig['ema200']}\n\n"
                    f"Entry: `{sig['entry']}`\n"
                    f"SL: `{sig['sl']}`  (ATR×{ATR_MULT})\n"
                    f"TP: `{sig['tp']}`  (R:R≈{sig['rr']})"
                )
                for chat_id in chats:
                    await send_signal_text(context, chat_id, body)
        except Exception as e:
            logger.exception(f"Error on {symbol}: {e}")


# ── أوامر تيليغرام ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً! هذا بوت إشارات *Pro* (RSI + MACD + EMA200 + ATR)\n"
        "الأوامر:\n"
        "/subscribe — اشترك بالاشعارات\n"
        "/unsubscribe — إلغاء الاشتراك\n"
        "/pairs — عرض/تعديل الأزواج (مثال: /pairs EURUSD XAUUSD)\n"
        "/status — الحالة الحالية\n"
        "/test — إرسال إشارة تجريبية (فقط رسالة تجربة)"
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
        pairs_list = [p.upper() for p in context.args]
        subs["pairs"] = pairs_list
        save_subs(subs)
        return await update.message.reply_text(f"تم التحديث. الأزواج: {', '.join(pairs_list)}")
    await update.message.reply_text(f"الأزواج الحالية: {', '.join(subs.get('pairs', []))}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    info = {
        "pairs": subs.get("pairs", []),
        "timeframe": TIMEFRAME,
        "interval_minutes": INTERVAL_MINUTES,
        "subscribers": len(subs.get("chats", [])),
        "RSI_LOW": RSI_LOW,
        "RSI_HIGH": RSI_HIGH,
        "ATR_MULT": ATR_MULT,
        "RR_RATIO": RR_RATIO,
    }
    await update.message.reply_text(f"الحالة: {info}")


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # رسالة برو تجريبية (لا تتعلق ببيانات السوق)
    body = (
        "📢 *Pro Signal* | EURUSD (Demo)\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "🔸 اتجاه: *BUY ✅*\n"
        "RSI=24.7 | MACD hist -0.002→0.001 | EMA200=1.08500\n\n"
        "Entry: `1.08620`\n"
        "SL: `1.08440`  (ATR×1.5)\n"
        "TP: `1.08980`  (R:R≈2.0)"
    )
    await update.message.reply_text(body, parse_mode=ParseMode.MARKDOWN)


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

    # جدولة التشييك الدوري (PTB v21)
    app.job_queue.run_repeating(
        check_signals_job,
        interval=timedelta(minutes=INTERVAL_MINUTES),
        first=10,
        name="fx_pro_checker",
    )

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
