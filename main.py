import requests
import time
import os
import re
import openai
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Configuration\ nTELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


def send_telegram_message(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        r = requests.post(url, data=data, timeout=10)
        print(f"📡 Telegram: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print("❌ Telegram error:", e)
        return False


def scrape_real_earnings_data():
    # ... (existing implementation) ...
    pass

# (other helper functions: filter_stocks_by_market_cap, get_stock_price_data,
#  ai_analyze_earnings, parse_ai_analysis, calculate_trading_score,
#  generate_trading_signal, run_corrected_analysis)


def scheduled_job():
    print(f"⏰ Running analysis at {datetime.now()}")
    run_corrected_analysis()

if __name__ == "__main__":
    # QUICK SMOKE TEST — run once immediately on startup
    scheduled_job()

    # Then start scheduler for daily runs
    scheduler = BlockingScheduler()
    trigger = CronTrigger(
        day_of_week='mon-fri',
        hour=14,
        minute=10,
        timezone='Europe/London'
    )
    scheduler.add_job(scheduled_job, trigger, id="earnings_analysis")
    print("🔧 Scheduler started – runs Mon–Fri at 14:10 London time")
    scheduler.start()
