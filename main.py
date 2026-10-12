import os
import logging
import asyncio
import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# إعداد السجل (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# التوكن الجديد الخاص بك
TOKEN = "8882103752:AAGYE3RDTIzx5otBxoDBtp5vRXYlQ7u8kVw"

# قائمة الأصول المالية المدعومة
SYMBOLS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "EURUSD": "EURUSD=X",
    "GOLD": "GC=F"
}

def analyze_market(symbol_key):
    ticker = SYMBOLS.get(symbol_key, "BTC-USD")
    try:
        # جلب البيانات التاريخية
        df = yf.download(ticker, period="5d", interval="1h", progress=False)
        if df.empty or len(df) < 50:
            return f"عذراً، البيانات غيرเพียงية لتحليل {symbol_key} حالياً."

        # تسوية أعمدة البيانات إذا كانت متعددة المستويات
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']

        # حساب المؤشرات الفنية
        ema9 = EMAIndicator(close, window=9).ema_indicator().iloc[-1]
        ema21 = EMAIndicator(close, window=21).ema_indicator().iloc[-1]
        rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
        
        current_price = close.iloc[-1]

        # استراتيجية إشارة بسيطة وواضحة
        signal = "حيادي ⚖️"
        if ema9 > ema21 and rsi < 70:
            signal = "صعود 🟢 (شراء)"
        elif ema9 < ema21 and rsi > 30:
            signal = "هبوط 🔴 (بيع)"

        report = (
            f"📊 **تقرير التحليل الفني لـ {symbol_key}**\n\n"
            f"💰 السعر الحالي: `{current_price:.4f}`\n"
            f"📈 مؤشر EMA 9: `{ema9:.4f}`\n"
            f"📉 مؤشر EMA 21: `{ema21:.4f}`\n"
            f"⚡ مؤشر القوة النسبية RSI: `{rsi:.2f}`\n\n"
            f"💡 **الإشارة المتوقعة:** {signal}"
        )
        return report
    except Exception as e:
        return f"حدث خطأ أثناء جلب تحليل {symbol_key}: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحباً بك في بوت التداول والتحليل الفني الخاص بك! 🚀\n\n"
        "الأوامر المتاحة:\n"
        "/btc - تحليل البيتكوين\n"
        "/eth - تحليل الإيثريوم\n"
        "/eurusd - تحليل اليورو مقابل الدولار\n"
        "/gold - تحليل الذهب"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def get_crypto_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    symbol_map = {
        "/btc": "BTC",
        "/eth": "ETH",
        "/eurusd": "EURUSD",
        "/gold": "GOLD"
    }
    
    for cmd, sym in symbol_map.items():
        if cmd in text:
            await update.message.reply_text(f"جاري جلب التحليل لـ {sym}، يرجى الانتظار...", parse_mode="Markdown")
            report = analyze_market(sym)
            await update.message.reply_text(report, parse_mode="Markdown")
            return

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.COMMAND & (~filters.UpdateType.EDITED_MESSAGE), get_crypto_signal))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
