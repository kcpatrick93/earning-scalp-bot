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
            data_plain = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            fallback = requests.post(url, data=data_plain, timeout=10)
            if fallback.status_code == 200:
                print("📡 Channel broadcast sent (plain text fallback)")
                return True
            return False
    except Exception as e:
        print(f"❌ Channel broadcast error: {e}")
        return False

def get_earnings_calendar():
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={today}&token={FINNHUB_TOKEN}"
    try:
        print("🔍 Fetching earnings calendar...")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            earnings = response.json()
            bmo_earnings = []
            amc_earnings = []
            
            for stock in earnings.get('earningsCalendar', []):
                if stock.get('hour') == 'bmo':
                    bmo_earnings.append(stock)
                elif stock.get('hour') == 'amc':
                    amc_earnings.append(stock)
            
            print(f"✅ Found {len(bmo_earnings)} BMO + {len(amc_earnings)} AMC earnings")
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
        now = datetime.now()
        
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
        
        # More lenient sentiment scoring
        if negative_score > positive_score + 1:  # Need clear negative bias
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
    except requests.exceptions.Timeout:
        print(f"    ⏰ Earnings data timeout for {symbol}")
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

def calculate_risk_score(stock_data, earnings_data, news_sentiment, earnings_type):
    """Calculate risk score from 1 (lowest risk) to 10 (highest risk)"""
    risk_score = 1
    risk_factors = []
    
    gap = abs(stock_data['gap_percent'])
    market_cap = stock_data['market_cap']
    volume_surge = stock_data['volume_surge']
    
    # Base risk for earnings type
    if earnings_type == 'AMC':
        risk_score += 1  # Reduced from 2
        risk_factors.append("AMC overnight risk")
    
    # Gap size risk (more lenient)
    if gap > 10:
        risk_score += 2
        risk_factors.append("Very large gap >10%")
    elif gap > 7:
        risk_score += 1
        risk_factors.append("Large gap >7%")
    
    # Market cap risk (more lenient)
    if market_cap < 100000000:  # < $100M
        risk_score += 2
        risk_factors.append("Micro cap")
    elif market_cap < 500000000:  # < $500M
        risk_score += 1
        risk_factors.append("Small cap")
    
    # Volume risk (more lenient)
    if volume_surge < 0.8:
        risk_score += 1
        risk_factors.append("Low volume surge")
    
    # News sentiment risk (less strict)
    if news_sentiment['sentiment'] == 'NEGATIVE' and news_sentiment['confidence'] > 0.7:
        risk_score += 2
        risk_factors.append("Strong negative news")
    elif news_sentiment['risk_flags'] and len(news_sentiment['risk_flags']) > 2:
        risk_score += 1
        risk_factors.append("Multiple news risk flags")
    
    # Earnings surprise risk
    if earnings_data and earnings_data.get('eps_surprise', 0) < -0.05:  # Significant miss
        risk_score += 1
        risk_factors.append("Large earnings miss")
    
    risk_score = min(10, risk_score)
    
    return risk_score, risk_factors

def generate_enhanced_signal(stock_data, earnings_data, earnings_calendar_item, news_sentiment, earnings_type):
    gap = stock_data['gap_percent']
    market_cap = stock_data['market_cap']
    volume = stock_data['avg_volume']
    symbol = stock_data['symbol']
    
    # LOOSENED THRESHOLDS FOR TESTING
    if earnings_type == 'BMO':
        min_gap = 1.5          # Was 2.0 - Lower threshold
        max_gap = 10.0         # Was 8.0 - Higher threshold  
        min_volume = 300000    # Was 500000 - Much lower
        min_market_cap = 200000000  # Was 500M - Now $200M
    else:  # AMC
        min_gap = 2.0          # Was 3.0 - Lower threshold
        max_gap = 12.0         # Was 10.0 - Higher threshold
        min_volume = 250000    # Was 750000 - Much lower
        min_market_cap = 150000000  # Was 1B - Now $150M
    
    # Basic filters (much more lenient)
    if market_cap < min_market_cap and market_cap > 0:
        return f"❌ SKIP - Too small cap (${market_cap/1000000:.0f}M for {earnings_type})"
    
    if volume < min_volume and volume > 0:
        return f"❌ SKIP - Low volume ({volume:,} for {earnings_type})"
    
    # Much more lenient news sentiment filter
    if earnings_type == 'AMC' and news_sentiment['sentiment'] == 'NEGATIVE' and news_sentiment['confidence'] > 0.8:
        return f"❌ SKIP - Strong negative news sentiment (AMC risk)"
    
    # Calculate risk score
    risk_score, risk_factors = calculate_risk_score(stock_data, earnings_data, news_sentiment, earnings_type)
    
    # Company size label
    if market_cap >= 10000000000:
        size_label = "Large-cap"
    elif market_cap >= 2000000000:
        size_label = "Mid-cap"
    elif market_cap >= 500000000:
        size_label = "Small-cap"
    else:
        size_label = "Micro-cap"
    
    eps_estimate = earnings_calendar_item.get('epsEstimate')
    earnings_surprise = earnings_data.get('eps_surprise') if earnings_data else None
    
    print(f"    📈 {symbol} [{earnings_type}] ({size_label}): Gap {gap:.1f}%, Risk: {risk_score}/10")
    
    # More lenient signal generation
    if earnings_surprise is not None:
        if earnings_surprise > 0 and gap > min_gap:
            if gap <= max_gap and risk_score <= 8:  # Was 6, now 8
                return f"🚀 STRONG BUY - Earnings beat + {gap:.1f}% gap [{earnings_type}] (Risk: {risk_score}/10)"
            elif gap <= max_gap:
                return f"⚠️ CAUTION BUY - Earnings beat + {gap:.1f}% gap [{earnings_type}] (Risk: {risk_score}/10)"
            else:
                return f"❌ SKIP - Gap too high {gap:.1f}% [{earnings_type}]"
        elif earnings_surprise > 0 and gap < 0:
            if abs(gap) >= min_gap and risk_score <= 8:
                return f"🤔 MIXED - Earnings beat but negative gap {gap:.1f}% [{earnings_type}] (Risk: {risk_score}/10)"
        elif earnings_surprise < 0 and gap < -min_gap:
            if gap >= -max_gap and risk_score <= 8:
                return f"📉 STRONG SHORT - Earnings miss + {gap:.1f}% gap [{earnings_type}] (Risk: {risk_score}/10)"
            else:
                return f"⚠️ CAUTION SHORT - Earnings miss + {gap:.1f}% gap [{earnings_type}] (Risk: {risk_score}/10)"
        elif earnings_surprise < 0 and gap > 0:
            return f"🤔 MIXED - Earnings miss but positive gap {gap:.1f}% [{earnings_type}] (Risk: {risk_score}/10)"
    
    # Gap-only signals (much more lenient)
    if min_gap <= abs(gap) <= max_gap and risk_score <= 8:  # Accept both positive and negative gaps
        direction = "BUY" if gap > 0 else "SHORT"
        return f"🟡 {direction} - Good gap {gap:.1f}% [{earnings_type}] (Risk: {risk_score}/10, no earnings data yet)"
    elif abs(gap) > max_gap:
        return f"❌ SKIP - Too volatile {gap:.1f}% [{earnings_type}]"
    else:
        return f"❌ SKIP - Small gap {gap:.1f}% [{earnings_type}]"

def is_trading_day():
    uk_tz = pytz.timezone('Europe/London')
    now = datetime.now(uk_tz)
    return now.weekday() < 5

def get_next_run_info():
    uk_tz = pytz.timezone('Europe/London')
    now = datetime.now(uk_tz)
    today_2_15 = now.replace(hour=14, minute=15, second=0, microsecond=0)
    
    if now < today_2_15 and is_trading_day():
        time_until = today_2_15 - now
        hours = time_until.seconds // 3600
        minutes = (time_until.seconds % 3600) // 60
        if hours > 0:
            return f"TODAY at 2:15 PM (in {hours}h {minutes}m)"
        else:
            return f"TODAY at 2:15 PM (in {minutes} minutes)"
    else:
        days_ahead = 1
        next_day = now + timedelta(days=days_ahead)
        while next_day.weekday() >= 5:
            days_ahead += 1
            next_day = now + timedelta(days=days_ahead)
        
        if days_ahead == 1:
            return "TOMORROW at 2:15 PM"
        elif days_ahead == 3 and now.weekday() == 4:
            return "MONDAY at 2:15 PM"
        else:
            return f"{next_day.strftime('%A')} at 2:15 PM"

def main_earnings_scan():
    if not is_trading_day():
        print("📅 Weekend detected - skipping scan")
        return
    
    uk_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_tz)
    print(f"🚨 EARNINGS SCALP SCAN (CHANNEL BROADCAST) - {current_time.strftime('%H:%M UK on %A, %B %d')} 🚨")
    print("=" * 80)
    
    bmo_earnings, amc_earnings = get_earnings_calendar()
    total_earnings = len(bmo_earnings) + len(amc_earnings)
    
    if total_earnings == 0:
        no_earnings_msg = f"📭 <b>EARNINGS SCALP BOT</b>\n"
        no_earnings_msg += f"📅 {current_time.strftime('%A, %B %d, %Y')}\n"
        no_earnings_msg += f"⏰ Scan completed at {current_time.strftime('%H:%M UK')}\n\n"
        no_earnings_msg += f"📭 No BMO or AMC earnings found today\n\n"
        no_earnings_msg += f"✅ Bot working properly\n"
        no_earnings_msg += f"🎯 Ready for next trading day!"
        
        print("📭 No earnings found today")
        send_telegram_message(no_earnings_msg)
        return
    
    print(f"📊 Analyzing {len(bmo_earnings)} BMO + {len(amc_earnings)} AMC earnings...")
    print("🔧 TESTING MODE: Loosened parameters for more opportunities!")
    print()
    
    trading_opportunities = []
    analyzed_stocks = []
    
    # Process BMO earnings
    for i, earnings_item in enumerate(bmo_earnings, 1):
        symbol = earnings_item.get('symbol')
        print(f"[BMO {i}/{len(bmo_earnings)}] Analyzing {symbol}...")
        
        stock_data = analyze_stock_gap(symbol)
        if not stock_data:
            continue
        
        news_sentiment = get_free_news_sentiment(symbol)
        earnings_results = get_earnings_results(symbol)
        signal = generate_enhanced_signal(stock_data, earnings_results, earnings_item, news_sentiment, 'BMO')
        
        stock_data['signal'] = signal
        stock_data['earnings_type'] = 'BMO'
        stock_data['news_sentiment'] = news_sentiment
        stock_data['earnings_surprise'] = earnings_results.get('eps_surprise') if earnings_results else None
        
        print(f"    🎯 Signal: {signal}")
        print()
        
        analyzed_stocks.append(stock_data)
        
        if any(x in signal for x in ["🚀", "📉", "⚠️", "🟡", "🤔"]):  # Added more signal types
            trading_opportunities.append(stock_data)
    
    # Process AMC earnings
    for i, earnings_item in enumerate(amc_earnings, 1):
        symbol = earnings_item.get('symbol')
        print(f"[AMC {i}/{len(amc_earnings)}] Analyzing {symbol}...")
        
        stock_data = analyze_stock_gap(symbol)
        if not stock_data:
            continue
        
        news_sentiment = get_free_news_sentiment(symbol)
        earnings_results = get_earnings_results(symbol)
        signal = generate_enhanced_signal(stock_data, earnings_results, earnings_item, news_sentiment, 'AMC')
        
        stock_data['signal'] = signal
        stock_data['earnings_type'] = 'AMC'
        stock_data['news_sentiment'] = news_sentiment
        stock_data['earnings_surprise'] = earnings_results.get('eps_surprise') if earnings_results else None
        
        print(f"    🎯 Signal: {signal}")
        print()
        
        analyzed_stocks.append(stock_data)
        
        if any(x in signal for x in ["🚀", "📉", "⚠️", "🟡", "🤔"]):
            trading_opportunities.append(stock_data)
    
    print("=" * 80)
    
    # Send results to channel
    if trading_opportunities:
        print("🎯 TRADING OPPORTUNITIES FOUND:")
        
        channel_msg = f"🚨 <b>EARNINGS SCALP ALERTS</b> 🚨\n"
        channel_msg += f"📅 {current_time.strftime('%b %d, %Y')}\n"
        channel_msg += f"⏰ US Market opens in 15 minutes (2:30 PM UK)\n\n"
        
        for opp in trading_opportunities:
            print(f"📈 {opp['symbol']} [{opp['earnings_type']}] ({opp['company_name']})")
            print(f"   Gap: {opp['gap_percent']:+.1f}% | ${opp['yesterday_close']:.2f} → ${opp['current_price']:.2f}")
            print(f"   Market Cap: ${opp['market_cap']/1000000:.0f}M | Sector: {opp['sector']}")
            print(f"   Volume Surge: {opp['volume_surge']:.1f}x | News: {opp['news_sentiment']['sentiment']}")
            if opp['earnings_surprise']:
                print(f"   EPS Surprise: ${opp['earnings_surprise']:+.2f}")
            print(f"   🎯 {opp['signal']}")
            print()
            
            # Channel broadcast message
            channel_msg += f"📈 <b>{opp['symbol']}</b> [{opp['earnings_type']}]\n"
            channel_msg += f"Gap: <b>{opp['gap_percent']:+.1f}%</b>\n"
            channel_msg += f"${opp['yesterday_close']:.2f} → ${opp['current_price']:.2f}\n"
            channel_msg += f"Market Cap: ${opp['market_cap']/1000000:.0f}M\n"
            channel_msg += f"News: {opp['news_sentiment']['sentiment']}\n"
            if opp['earnings_surprise']:
                channel_msg += f"EPS Surprise: <b>${opp['earnings_surprise']:+.2f}</b>\n"
            channel_msg += f"{opp['signal']}\n\n"
        
        channel_msg += "🎯 2-3 minute scalp targets!\n"
        channel_msg += "📝 Paper trade and track results!"
        
        send_telegram_message(channel_msg)
        
    else:
        no_trades_msg = f"📭 <b>EARNINGS SCALP REPORT</b>\n"
        no_trades_msg += f"📅 {current_time.strftime('%A, %B %d, %Y')}\n"
        no_trades_msg += f"⏰ Scan completed at {current_time.strftime('%H:%M UK')}\n\n"
        no_trades_msg += f"📊 Earnings Found: {len(bmo_earnings)} BMO + {len(amc_earnings)} AMC\n"
        
        if analyzed_stocks:
            symbols = [f"{stock['symbol']}[{stock['earnings_type']}]" for stock in analyzed_stocks]
            no_trades_msg += f"📋 Analyzed: {', '.join(symbols)}\n\n"
            no_trades_msg += f"❌ NO TRADING OPPORTUNITIES\n"
            no_trades_msg += f"Filtered by enhanced criteria:\n"
            no_trades_msg += f"• BMO: Gaps >1.5%, Volume >300K, Cap >$200M\n"
            no_trades_msg += f"• AMC: Gaps >2%, Volume >250K, Cap >$150M\n"
            no_trades_msg += f"• News sentiment analysis\n\n"
        
        no_trades_msg += f"✅ Bot working properly\n"
        no_trades_msg += f"🎯 Ready for {get_next_run_info().split(' at ')[0]}'s scan!"
        
        print("📭 NO TRADING OPPORTUNITIES")
        print("Filtered by enhanced criteria")
        
        send_telegram_message(no_trades_msg)
    
    print("=" * 80)
    print("✅ Channel broadcast complete!")

def send_startup_message():
    """Send a message when the bot starts up"""
    uk_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_tz)
    startup_msg = f"🤖 <b>EARNINGS SCALP BOT ONLINE</b>\n"
    startup_msg += f"📅 Started: {current_time.strftime('%A, %B %d, %Y at %H:%M UK')}\n"
    startup_msg += f"🚀 Running on Railway 24/7\n"
    startup_msg += f"⏰ Scheduled for daily 2:15 PM UK scans\n"
    startup_msg += f"📡 Broadcasting to channel automatically\n\n"
    startup_msg += f"✅ All systems operational!"
    
    send_telegram_message(startup_msg)

if __name__ == "__main__":
    print("🤖 ENHANCED EARNINGS SCALP BOT (RAILWAY DEPLOYMENT)")
    print("📡 Now broadcasting to your Telegram channel!")
    print("🔧 Loosened parameters for more trading opportunities")
    print("📰 Smart news sentiment analysis included")
    print("🇬🇧 Properly scheduled for UK time!")
    
    uk_tz = pytz.timezone('Europe/London')
    current_uk_time = datetime.now(uk_tz)
    print(f"⏰ Current UK time: {current_uk_time.strftime('%H:%M on %A, %B %d')}")
    
    # Send startup notification
    send_startup_message()
    
    # Schedule the daily scan
    schedule.every().day.at("14:15").do(main_earnings_scan)
    
    print("📅 Scheduled for 2:15 PM UK time daily")
    print("🔄 Running initial test scan...")
    print()
    
    # Run initial test
    main_earnings_scan()
    
    next_run = get_next_run_info()
    print(f"\n⏳ Bot waiting for next scan: {next_run}")
    print("📡 Now broadcasting to your channel - fully automated!")
    print("🎯 Running 24/7 on Railway!")
    
    # Keep the bot running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
