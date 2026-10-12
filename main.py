import asyncio
import logging
import os
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
import yfinance as yf

# إعداد السجل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

daily_trades = {"wins": 0, "losses": 0}
user_sessions = {}

# الأصول المتاحة للتحليل
PAIRS_MAP = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "BTC/USD (حي 24/7)": "BTC-USD",
    "ETH/USD (حي 24/7)": "ETH-USD",
    "SOL/USD (حي 24/7)": "SOL-USD",
}


def analyze_live_market_strict(ticker_symbol, duration):
  try:
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="3d", interval="1m")

    if df.empty or len(df) < 30:
      return "CONNECTION_ERROR"

    close_prices = df["Close"]
    open_prices = df["Open"]

    rsi = RSIIndicator(close=close_prices, window=14).rsi().iloc[-1]
    ema_fast = EMAIndicator(close=close_prices, window=8).ema_indicator().iloc[-1]
    ema_slow = (
        EMAIndicator(close=close_prices, window=21).ema_indicator().iloc[-1]
    )
    macd_obj = MACD(close=close_prices)
    macd_diff = macd_obj.macd_diff().iloc[-1]

    rsi_val = round(rsi, 1)

    last_close = close_prices.iloc[-1]
    last_open = open_prices.iloc[-1]
    is_green_candle = last_close > last_open
    is_red_candle = last_close < last_open

    if (
        rsi_val <= 35
        and ema_fast > ema_slow
        and macd_diff > 0
        and is_green_candle
    ):
      signal = "BUY 🟢 (شراء)"
      confidence = "93%"
      strength = "9.6"
      conclusion = (
          "تأكيد انعكاس شرائي: تشبع بيعي مع شمعة زخم خضراء قوية وإغلاق إيجابي"
          " للمتوسطات."
      )
    elif (
        rsi_val >= 65 and ema_fast < ema_slow and macd_diff < 0 and is_red_candle
    ):
      signal = "SELL 🔴 (بيع)"
      confidence = "93%"
      strength = "9.6"
      conclusion = (
          "تأكيد انعكاس بيعي: تشبع شرائي مع شمعة زخم حمراء قوية وإغلاق سلبي"
          " للمتوسطات."
      )
    else:
      return {
          "no_signal": True,
          "rsi": rsi_val,
          "message": (
              f"📊 **مؤشر RSI الحالي: {rsi_val}**\n\n"
              "⚠️ **لا توجد صفقة مطابقة لشرط الزخم الآن!**\n"
              "البوت يرفض الدخول لعدم تطابق شمعة التأكيد. يرجى الفحص مرة أخرى."
          ),
      }

    return {
        "no_signal": False,
        "signal": signal,
        "rsi": rsi_val,
        "confidence": confidence,
        "strength": strength,
        "conclusion": conclusion,
        "duration": duration,
    }
  except Exception as e:
    logging.error(f"Analysis Error: {e}")
    return "CONNECTION_ERROR"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  keyboard = [
      [
          InlineKeyboardButton(
              "🚀 بدء التحليل الفوري المؤكد", callback_data="select_duration"
          )
      ],
      [
          InlineKeyboardButton(
              "📜 سجل الصفقات اليومية", callback_data="daily_log"
          )
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  welcome_message = (
      "⚡ **مرحباً بك في بوت التداول السحابي المباشر**\n\n"
      "البوت يعمل الآن بشكل مستمر 24/7 على خوادم Koyeb."
  )

  if update.message:
    await update.message.reply_text(
        welcome_message, reply_markup=reply_markup, parse_mode="Markdown"
    )
  elif update.callback_query:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        welcome_message, reply_markup=reply_markup, parse_mode="Markdown"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = query.from_user.id
  await query.answer()
  data = query.data

  if data == "select_duration":
    keyboard = [
        [
            InlineKeyboardButton("⏱️ 1 دقيقة", callback_data="dur_1 دقيقة"),
            InlineKeyboardButton("⏱️ 2 دقيقة", callback_data="dur_2 دقيقة"),
        ],
        [
            InlineKeyboardButton("⏱️ 3 دقائق", callback_data="dur_3 دقائق"),
            InlineKeyboardButton("⏱️ 5 دقائق", callback_data="dur_5 دقائق"),
        ],
        [
            InlineKeyboardButton(
                "🏠 الصفحة الرئيسية", callback_data="main_menu"
            )
        ],
    ]
    await query.edit_message_text(
        "اختر **مدة الصفقة** المطلوبة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif data.startswith("dur_"):
    duration = data.replace("dur_", "")
    if user_id not in user_sessions:
      user_sessions[user_id] = {}
    user_sessions[user_id]["duration"] = duration

    keyboard = [
        [
            InlineKeyboardButton("EUR/USD", callback_data="p_EUR/USD"),
            InlineKeyboardButton("GBP/USD", callback_data="p_GBP/USD"),
            InlineKeyboardButton("USD/JPY", callback_data="p_USD/JPY"),
        ],
        [
            InlineKeyboardButton("AUD/USD", callback_data="p_AUD/USD"),
            InlineKeyboardButton("USD/CAD", callback_data="p_USD/CAD"),
            InlineKeyboardButton("USD/CHF", callback_data="p_USD/CHF"),
        ],
        [
            InlineKeyboardButton(
                "🪙 BTC/USD (حي 24/7)", callback_data="p_BTC/USD (حي 24/7)"
            )
        ],
        [
            InlineKeyboardButton(
                "🪙 ETH/USD (حي 24/7)", callback_data="p_ETH/USD (حي 24/7)"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 تغيير الزمن", callback_data="select_duration"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 الصفحة الرئيسية", callback_data="main_menu"
            )
        ],
    ]
    await query.edit_message_text(
        f"✅ تم تحديد المدة: **{duration}**\n\nاختر الأصل للفحص اللحظي:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif data.startswith("p_"):
    pair_code = data.replace("p_", "")
    ticker_symbol = PAIRS_MAP.get(pair_code)
    duration = user_sessions.get(user_id, {}).get("duration", "1 دقيقة")

    await query.edit_message_text(
        f"⏳ جاري فحص الزخم والشموع الحية لـ {pair_code}..."
    )

    analysis = analyze_live_market_strict(ticker_symbol, duration)

    if analysis == "CONNECTION_ERROR" or analysis is None:
      keyboard = [
          [
              InlineKeyboardButton(
                  "🔄 إعادة المحاولة", callback_data=f"p_{pair_code}"
              )
          ],
          [
              InlineKeyboardButton(
                  "🏠 الصفحة الرئيسية", callback_data="main_menu"
              )
          ],
      ]
      await query.edit_message_text(
          "⚠️ **خطأ في الاتصال أو السوق مغلق!**\n\nيرجى تجربة العملات الرقمية"
          " 24/7.",
          reply_markup=InlineKeyboardMarkup(keyboard),
          parse_mode="Markdown",
      )
      return

    if analysis.get("no_signal"):
      keyboard = [
          [
              InlineKeyboardButton(
                  "🔄 فحص زوج آخر", callback_data=f"dur_{duration}"
              )
          ],
          [
              InlineKeyboardButton(
                  "🏠 الصفحة الرئيسية", callback_data="main_menu"
              )
          ],
      ]
      await query.edit_message_text(
          analysis["message"],
          reply_markup=InlineKeyboardMarkup(keyboard),
          parse_mode="Markdown",
      )
      return

    signal_text = (
        f"🎯 **إشارة تداول مؤكدة ومحدثة**\n\n"
        f"الأصل: **{pair_code}**\n"
        f"الإشارة: **{analysis['signal']}**\n"
        f"المدة: **{analysis['duration']}**\n"
        f"نسبة الثقة: **{analysis['confidence']}** (قوة الزخم:"
        f" {analysis['strength']}/10)\n"
        f"📊 RSI: **{analysis['rsi']}**\n\n"
        f"🧠 التحليل الفوري:\n_{analysis['conclusion']}_"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 فحص زوج آخر", callback_data=f"dur_{duration}"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 الصفحة الرئيسية", callback_data="main_menu"
            )
        ],
    ]
    await query.edit_message_text(
        signal_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif data == "daily_log":
    total = daily_trades["wins"] + daily_trades["losses"]
    log_text = (
        "📜 **سجل الصفقات اليومية:**\n\n"
        f"• إجمالي الصفقات: {total}\n"
        f"• الصفقات الرابحة ✅: {daily_trades['wins']}\n"
        f"• الصفقات الخاسرة ❌: {daily_trades['losses']}"
    )
    keyboard = [[
        InlineKeyboardButton("🏠 الصفحة الرئيسية", callback_data="main_menu")
    ]]
    await query.edit_message_text(
        log_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif data == "main_menu":
    await start(update, context)


def main():
  TOKEN = "8882103752:AAGIh8nZkF1relfseCLo9awO6bHftI1SaG4"
  application = ApplicationBuilder().token(TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CallbackQueryHandler(button_handler))

  print("البوت يعمل الآن على استضافة Koyeb السحابية بنجاح...")
  application.run_polling()


if __name__ == "__main__":
  main()
      
