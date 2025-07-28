import requests
import yfinance as yf
import schedule
import time
import pytz
import os
from datetime import datetime, timedelta
import re
from urllib.parse import quote

# Get tokens from environment variables (for security)
FINNHUB_TOKEN = os.getenv("FINNHUB_TOKEN", "d1ehal1r01qjssrk4fu0d1ehal1r01qjssrk4fug")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7626751011:AAHHWa7ItXmjaP4-icgw8Aiy6_SdvhMdVK4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1001002605954379")

# MAJOR US EXCHANGES - Filter to only these
MAJOR_EXCHANGES = ['NASDAQ', 'NYSE', 'NYSEARCA', 'BATS']

# Only include stocks with market cap > $500M and average volume > 1M
MIN_MARKET_CAP = 500000000  # $500M
MIN_AVG_VOLUME = 1000000    # 1M shares

# Risk keywords for news analysis
NEGATIVE_KEYWORDS = [
    'investigation', 'lawsuit', 'sued', 'probe', 'scandal', 'fraud',
    'disappointing', 'miss', 'guidance cut', 'lowered outlook', 'warning',
    'concern', 'worry', 'decline', 'drop', 'fall', 'weak', 'poor',
    'regulatory', 'fine', 'penalty', 'violation', 'breach', 'bankruptcy'
]

POSITIVE_KEYWORDS = [
    'beat', 'exceed', 'strong', 'growth', 'raised outlook', 'upgrade',
    'bullish', 'optimistic', 'positive', 'outperform', 'record',
    'impressive', 'solid', 'robust', 'momentum'
]

def test_telegram_connection():
    """Test Telegram bot connection and permissions"""
    print("🔧 Testing Telegram connection...")
    
    # Test 1: Bot info
    try:
        bot_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(bot_url, timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Bot connected: @{bot_info['result']['username']}")
        else:
            print(f"❌ Bot connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bot test error: {e}")
        return False
    
    # Test 2: Channel access
    try:
        test_msg = f"🔧 Test message from bot at {datetime.now().strftime('%H:%M:%S')}"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': test_msg}
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            print("✅ Test message sent successfully!")
            return True
        else:
            print(f"❌ Test message failed: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Try alternative chat ID format
            alt_chat_id = TELEGRAM_CHAT_ID.replace('-100', '@')
            if alt_chat_id != TELEGRAM_CHAT_ID:
                print(f"🔄 Trying alternative chat ID: {alt_chat_id}")
                data['chat_id'] = alt_chat_id
                alt_response = requests.post(url, data=data, timeout=10)
                if alt_response.status_code == 200:
                    print("✅ Alternative chat ID worked!")
                    return True
            
            return False
    except Exception as e:
        print(f"❌ Channel test error: {e}")
        return False

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("📡 Channel broadcast sent!")
            return True
        else:
            print(f"❌ Channel broadcast failed: {response.status_code}")
            print(f"Response: {response.text}")
            # Try without HTML formatting
            data_plain = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            fallback = requests.post(url, data=data_plain, timeout=10)
            if fallback.status_code == 200:
                print("📡 Channel broadcast sent (plain text fallback)")
                return True
            print(f"❌ Plain text fallback also failed: {fallback.status_code}")
            return False
    except Exception as e:
        print(f"❌ Channel broadcast error: {e}")
        return False

def is_major_us_stock(symbol):
    """Check if stock is from a major US exchange with sufficient size"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Check exchange
        exchange = info.get('exchange', '')
        if exchange not in MAJOR_EXCHANGES:
            print(f"    ❌ {symbol}: Not major US exchange ({exchange})")
            return False
        
        # Check market cap
        market_cap = info.get('marketCap', 0)
        if market_cap < MIN_MARKET_CAP:
            print(f"    ❌ {symbol}: Market cap too small (${market_cap/1000000:.0f}M)")
            return False
            
        # Check average volume
        avg_volume = info.get('averageVolume', 0)
        if avg_volume < MIN_AVG_VOLUME:
            print(f"    ❌ {symbol}: Volume too low ({avg_volume:,})")
            return False
            
        print(f"    ✅ {symbol}: Major stock (${market_cap/1000000:.0f}M cap, {avg_volume:,} vol)")
        return True
        
    except Exception as e:
        print(f"    ❌ {symbol}: Error checking stock info: {e}")
        return False

def get_earnings_calendar():
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={today}&token={FINNHUB_TOKEN}"
    try:
        print("🔍 Fetching earnings calendar...")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            earnings = response.json()
            
            print(f"📊 Raw earnings data: {len(earnings.get('earningsCalendar', []))} total")
            
            bmo_earnings = []
            amc_earnings = []
            
            # Filter earnings data
            for stock in earnings.get('earningsCalendar', []):
                symbol = stock.get('symbol')
                if not symbol:
                    continue
                    
                # Check if it's a major US stock
                if not is_major_us_stock(symbol):
                    continue
                
                if stock.get('hour') == 'bmo':
                    bmo_earnings.append(stock)
                elif stock.get('hour') == 'amc':
                    amc_earnings.append(stock)
            
            print(f"✅ Filtered to {len(bmo_earnings)} BMO + {len(amc_earnings)} AMC major US stocks")
            return bmo_earnings, amc_earnings
        else:
            print(f"❌ Earnings API failed: {response.status_code}")
            return [], []
    except requests.exceptions.Timeout:
        print("❌ Earnings API timeout")
        return [], []
    except Exception as e:
        print(f"❌ Earnings API error: {e}")
        return [], []

def get_free_news_sentiment(symbol):
    """Analyze news sentiment using free sources"""
    try:
        print(f"    🔍 Checking news sentiment for {symbol}...")
        
        stock = yf.Ticker(symbol)
        news = stock.news
        
        if not news:
            return {'sentiment': 'NEUTRAL', 'risk_flags': [], 'confidence': 0.4}
        
        recent_news = []
        
        for article in news[:5]:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            text = f"{title} {summary}"
            recent_news.append(text)
        
        negative_score = 0
        positive_score = 0
        risk_flags = []
        
        for text in recent_news:
            for keyword in NEGATIVE_KEYWORDS:
                if keyword in text:
                    negative_score += 1
                    risk_flags.append(keyword)
            
            for keyword in POSITIVE_KEYWORDS:
                if keyword in text:
                    positive_score += 1
        
        if negative_score > positive_score + 1:
            sentiment = 'NEGATIVE'
            confidence = min(0.8, 0.5 + (negative_score - positive_score) * 0.1)
        elif positive_score > negative_score:
            sentiment = 'POSITIVE'
            confidence = min(0.8, 0.5 + (positive_score - negative_score) * 0.1)
        else:
            sentiment = 'NEUTRAL'
            confidence = 0.5
        
        print(f"    📰 News sentiment: {sentiment} (confidence: {confidence:.1f})")
        if risk_flags:
            print(f"    ⚠️ Risk flags: {', '.join(set(risk_flags))}")
        
        return {
            'sentiment': sentiment,
            'risk_flags': list(set(risk_flags)),
            'confidence': confidence,
            'negative_score': negative_score,
            'positive_score': positive_score
        }
        
    except Exception as e:
        print(f"    ❌ News analysis error for {symbol}: {e}")
        return {'sentiment': 'NEUTRAL', 'risk_flags': [], 'confidence': 0.4}

def get_earnings_results(symbol):
    try:
        url = f"https://finnhub.io/api/v1/stock/earnings?symbol={symbol}&token={FINNHUB_TOKEN}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            earnings_data = response.json()
            if earnings_data and len(earnings_data) > 0:
                latest = earnings_data[0]
                actual_eps = latest.get('actual')
                estimate_eps = latest.get('estimate')
                if actual_eps is not None and estimate_eps is not None:
                    return {
                        'actual_eps': actual_eps,
                        'estimate_eps': estimate_eps,
                        'eps_surprise': actual_eps - estimate_eps
                    }
    except Exception as e:
        print(f"    ❌ Earnings data error for {symbol}: {e}")
    return None

def analyze_stock_gap(symbol):
    try:
        print(f"  📊 Getting price data for {symbol}...")
        stock = yf.Ticker(symbol)
        
        hist = stock.history(period="5d")
        if len(hist) < 2:
            print(f"    ❌ Insufficient price data for {symbol}")
            return None
        
        yesterday_close = hist['Close'].iloc[-2]
        current_price = hist['Close'].iloc[-1]
        gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
        
        recent_volume = hist['Volume'].iloc[-1]
        avg_volume_5d = hist['Volume'].mean()
        volume_surge = recent_volume / avg_volume_5d if avg_volume_5d > 0 else 1
        
        print(f"    💰 {symbol}: ${yesterday_close:.2f} → ${current_price:.2f} ({gap_percent:+.1f}%)")
        print(f"    📊 Volume surge: {volume_surge:.1f}x")
        
        try:
            info = stock.info
            market_cap = info.get('marketCap', 0)
            avg_volume = info.get('averageVolume', 0)
            company_name = info.get('shortName', symbol)
            sector = info.get('sector', 'Unknown')
        except:
            print(f"    ⚠️ Could not get company info for {symbol}")
            market_cap = 0
            avg_volume = 0
            company_name = symbol
            sector = 'Unknown'
        
        return {
            'symbol': symbol,
            'company_name': company_name,
            'sector': sector,
            'yesterday_close': yesterday_close,
            'current_price': current_price,
            'gap_percent': gap_percent,
            'market_cap': market_cap,
            'avg_volume': avg_volume,
            'volume_surge': volume_surge,
            'recent_volume': recent_volume
        }
    except Exception as e:
        print(f"    ❌ Failed to analyze {symbol}: {e}")
        return None

def generate_trading_signal(stock_data, earnings_data, news_sentiment, earnings_type):
    gap = stock_data['gap_percent']
    symbol = stock_data['symbol']
    
    # Stricter thresholds for major stocks only
    if earnings_type == 'BMO':
        min_gap = 2.0
        max_gap = 8.0
    else:  # AMC
        min_gap = 2.5
        max_gap = 10.0
    
    # Check for strong signals only
    if abs(gap) >= min_gap and abs(gap) <= max_gap:
        if earnings_data:
            eps_surprise = earnings_data.get('eps_surprise', 0)
            if eps_surprise > 0 and gap > 0:
                return f"🚀 STRONG BUY - Beat + {gap:.1f}% gap [{earnings_type}]"
            elif eps_surprise < 0 and gap < 0:
                return f"📉 STRONG SHORT - Miss + {gap:.1f}% gap [{earnings_type}]"
        
        # Gap-only signal for major stocks
        direction = "BUY" if gap > 0 else "SHORT"
        return f"🟡 {direction} - {gap:.1f}% gap [{earnings_type}]"
    
    return None  # No signal

def main_earnings_scan():
    print("🚨 EARNINGS SCALP SCAN - MAJOR US STOCKS ONLY 🚨")
    print("=" * 60)
    
    # Test Telegram first
    if not test_telegram_connection():
        print("❌ Telegram test failed - bot may not work properly")
    
    bmo_earnings, amc_earnings = get_earnings_calendar()
    total_earnings = len(bmo_earnings) + len(amc_earnings)
    
    if total_earnings == 0:
        no_earnings_msg = "📭 No major US earnings today"
        print(no_earnings_msg)
        send_telegram_message(no_earnings_msg)
        return
    
    print(f"📊 Analyzing {len(bmo_earnings)} BMO + {len(amc_earnings)} AMC major US stocks...")
    
    trading_opportunities = []
    
    # Process BMO earnings
    for earnings_item in bmo_earnings:
        symbol = earnings_item.get('symbol')
        print(f"[BMO] Analyzing {symbol}...")
        
        stock_data = analyze_stock_gap(symbol)
        if not stock_data:
            continue
        
        news_sentiment = get_free_news_sentiment(symbol)
        earnings_results = get_earnings_results(symbol)
        signal = generate_trading_signal(stock_data, earnings_results, news_sentiment, 'BMO')
        
        if signal:
            stock_data['signal'] = signal
            stock_data['earnings_type'] = 'BMO'
            trading_opportunities.append(stock_data)
            print(f"    🎯 {signal}")
        else:
            print(f"    ❌ No strong signal")
        print()
    
    # Process AMC earnings
    for earnings_item in amc_earnings:
        symbol = earnings_item.get('symbol')
        print(f"[AMC] Analyzing {symbol}...")
        
        stock_data = analyze_stock_gap(symbol)
        if not stock_data:
            continue
        
        news_sentiment = get_free_news_sentiment(symbol)
        earnings_results = get_earnings_results(symbol)
        signal = generate_trading_signal(stock_data, earnings_results, news_sentiment, 'AMC')
        
        if signal:
            stock_data['signal'] = signal
            stock_data['earnings_type'] = 'AMC'
            trading_opportunities.append(stock_data)
            print(f"    🎯 {signal}")
        else:
            print(f"    ❌ No strong signal")
        print()
    
    print("=" * 60)
    
    # Send results
    if trading_opportunities:
        uk_tz = pytz.timezone('Europe/London')
        current_time = datetime.now(uk_tz)
        
        channel_msg = f"🚨 EARNINGS SCALP ALERTS 🚨\n"
        channel_msg += f"📅 {current_time.strftime('%b %d, %Y at %H:%M UK')}\n\n"
        
        for opp in trading_opportunities:
            channel_msg += f"📈 {opp['symbol']} [{opp['earnings_type']}]\n"
            channel_msg += f"Gap: {opp['gap_percent']:+.1f}%\n"
            channel_msg += f"${opp['yesterday_close']:.2f} → ${opp['current_price']:.2f}\n"
            channel_msg += f"{opp['signal']}\n\n"
        
        channel_msg += "🎯 Major US stocks only!\n"
        channel_msg += "📝 Trade with caution!"
        
        print("🎯 TRADING OPPORTUNITIES FOUND:")
        for opp in trading_opportunities:
            print(f"📈 {opp['symbol']}: {opp['signal']}")
        
        if send_telegram_message(channel_msg):
            print("✅ Alert sent to Telegram!")
        else:
            print("❌ Failed to send Telegram alert")
        
    else:
        no_trades_msg = f"📭 No trading opportunities in major US stocks today"
        print(no_trades_msg)
        send_telegram_message(no_trades_msg)

def send_startup_message():
    """Send a message when the bot starts up"""
    uk_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_tz)
    startup_msg = f"🤖 EARNINGS SCALP BOT ONLINE\n"
    startup_msg += f"📅 Started: {current_time.strftime('%A, %B %d, %Y at %H:%M UK')}\n"
    startup_msg += f"🚀 Running 24/7 on Railway\n"
    startup_msg += f"📊 Filtering to major US stocks only\n"
    startup_msg += f"⏰ Daily scans at 2:15 PM UK\n\n"
    startup_msg += f"✅ All systems operational!"
    
    if send_telegram_message(startup_msg):
        print("✅ Startup message sent!")
    else:
        print("❌ Failed to send startup message")

if __name__ == "__main__":
    print("🤖 EARNINGS SCALP BOT - MAJOR US STOCKS ONLY")
    print("📊 Filtering: Market cap >$500M, Volume >1M, Major exchanges only")
    print("🔧 Enhanced Telegram debugging")
    
    # Send startup notification
    send_startup_message()
    
    # Schedule the daily scan
    schedule.every().day.at("14:15").do(main_earnings_scan)
    
    print("📅 Scheduled for 2:15 PM UK time daily")
    print("🔄 Running initial scan...")
    
    # Run initial scan
    main_earnings_scan()
    
    print("\n⏳ Bot waiting for next scheduled scan...")
    print("🎯 Running 24/7 on Railway!")
    
    # Keep the bot running
    while True:
        schedule.run_pending()
        time.sleep(60)
