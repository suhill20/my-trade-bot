import os
import logging
import asyncio
import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# تفعيل البروكسي تلقائياً داخل الكود لتجنب خطأ 503
os.environ['HTTPS_PROXY'] = 'http://proxy.server:3128'
os.environ['HTTP_PROXY'] = 'http://proxy.server:3128'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8882103752:AAGYE3RDTIzx5otBxoDBtp5vRXYlQ7u8kVw"

# أزواج العملات الأساسية في منصة Pocket Option
PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "USD/CHF": "USDCHF=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "AUD/JPY": "AUDJPY=X",
    "CAD/JPY": "CADJPY=X",
    "EUR/AUD": "EURAUD=X",
    "GBP/CAD": "GBPCAD=X"
}

def analyze_market(symbol):
    ticker = PAIRS.get(symbol)
    if not ticker:
        return "⚠️ الزوج غير مدعوم حالياً."
    try:
        df = yf.download(ticker, period="2d", interval="1m", progress=False)
        if df.empty or len(df) < 30:
            df = yf.download(ticker, period="5d", interval="5m", progress=False)
            
        if df.empty or len(df) < 20:
            return f"❌ عذراً، تعذر جلب بيانات الحركة السعرية لـ {symbol}."

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        
        # استراتيجية صفقات Pocket Option: EMA 9 & 21 + RSI + MACD
        ema9 = EMAIndicator(close, window=9).ema_indicator().iloc[-1]
        ema21 = EMAIndicator(close, window=21).ema_indicator().iloc[-1]
        rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
        
        macd_obj = MACD(close)
        macd_line = macd_obj.macd().iloc[-1]
        macd_signal = macd_obj.macd_signal().iloc[-1]
        
        current_price = close.iloc[-1]

        # تحديد اتجاه الصفقة
        if ema9 > ema21 and rsi < 68 and macd_line > macd_signal:
            signal = "🟢 شراء قوي (CALL) ⬆️"
            recommendation = "صفقة صعود (1 - 3 دقائق)"
        elif ema9 < ema21 and rsi > 32 and macd_line < macd_signal:
            signal = "🔴 بيع قوي (PUT) ⬇️"
            recommendation = "صفقة هبوط (1 - 3 دقائق)"
        else:
            signal = "⚖️ محايد / انتظار (NO TRADE)"
            recommendation = "السوق في حالة تذبذب، انتظر الإشارة القادمة"

        report = (
            f"🎯 **تحليل Pocket Option: {symbol}**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 **السعر الحالي:** `{current_price:.5f}`\n\n"
            f"📊 **المؤشرات الفنية:**\n"
            f"• EMA 9 / 21: `{ema9:.5f}` / `{ema21:.5f}`\n"
            f"• RSI (14): `{rsi:.1f}`\n"
            f"• MACD: `{'إيجابي 🟢' if macd_line > macd_signal else 'سلبي 🔴'}`\n\n"
            f"🔥 **الإشارة:** {signal}\n"
            f"💡 **التوصية:** {recommendation}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        return report
    except Exception as e:
        return f"⚠️ حدث خطأ أثناء التحليل: {str(e)}"

def get_pairs_keyboard():
    keyboard = []
    keys = list(PAIRS.keys())
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(keys[i], callback_data=f"analyze_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(keys[i+1], callback_data=f"analyze_{keys[i+1]}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def get_analysis_keyboard(symbol):
    keyboard = [
        [InlineKeyboardButton("🔄 تحليل مرة أخرى", callback_data=f"analyze_{symbol}")],
        [InlineKeyboardButton("🔙 رجوع لقائمة الأزواج", callback_data="show_pairs")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "مرحباً بك في بوت تحليل صفقات Pocket Option! 📈\nاختر زوج العملات للتحليل المباشر:"
    if update.message:
        await update.message.reply_text(msg, reply_markup=get_pairs_keyboard())
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=get_pairs_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_pairs":
        await query.edit_message_text(
            "اختر زوج العملات للتحليل المباشر:",
            reply_markup=get_pairs_keyboard()
        )
    elif query.data.startswith("analyze_"):
        symbol = query.data.replace("analyze_", "")
        await query.edit_message_text(f"⏳ جاري تحليل {symbol} باستراتيجية المؤشرات...")
        
        report = analyze_market(symbol)
        await query.edit_message_text(
            report,
            parse_mode="Markdown",
            reply_markup=get_analysis_keyboard(symbol)
        )

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
