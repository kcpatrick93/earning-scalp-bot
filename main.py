import requests
import yfinance as yf
import schedule
import time
import pytz
import os
from datetime import datetime, timedelta

# Get tokens from environment variables
FINNHUB_TOKEN = os.getenv("FINNHUB_TOKEN", "d1ehal1r01qjssrk4fu0d1ehal1r01qjssrk4fug")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7626751011:AAHHWa7ItXmjaP4-icgw8Aiy6_SdvhMdVK4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@kp_earning_report_stockbot")

# COMPREHENSIVE LIST OF MAJOR STOCKS - NYSE + NASDAQ (Market Cap >$1B)
MAJOR_STOCKS = {
    # NASDAQ Mega/Large Caps
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'TSLA', 'META', 'AVGO', 'ORCL',
    'COST', 'NFLX', 'CRM', 'AMD', 'CSCO', 'ADBE', 'TXN', 'QCOM', 'INTU', 'CMCSA',
    'AMAT', 'INTC', 'PYPL', 'ISRG', 'BKNG', 'REGN', 'GILD', 'MU', 'ADI', 'LRCX',
    'PANW', 'KLAC', 'SNPS', 'CDNS', 'MRVL', 'ORLY', 'ABNB', 'WDAY', 'TEAM', 'DXCM',
    'SBUX', 'ZM', 'UBER', 'ROKU', 'DOCU', 'ZS', 'OKTA', 'SPLK', 'NDAQ', 'FAST',
    'PCAR', 'DLTR', 'BIIB', 'IDXX', 'LULU', 'CSGP', 'VRSK', 'EXC', 'CTSH', 'FISV',
    'ATVI', 'CHTR', 'LCID', 'RIVN', 'MRNA', 'VRTX', 'ALGN', 'SGEN', 'BMRN', 'ILMN',
    'WBA', 'PAYX', 'CTAS', 'ODFL', 'ROST', 'KHC', 'SIRI', 'XLNX', 'MNST', 'CRWD',
    
    # NYSE Mega/Large Caps  
    'V', 'JPM', 'WMT', 'XOM', 'UNH', 'MA', 'PG', 'HD', 'JNJ', 'BAC', 'KO', 'PEP',
    'LLY', 'TMO', 'LIN', 'ACN', 'MRK', 'WFC', 'DIS', 'ABT', 'VZ', 'COP', 'DHR',
    'PM', 'SPGI', 'RTX', 'HON', 'CAT', 'GS', 'NOW', 'IBM', 'AXP', 'BA', 'MMM',
    'GE', 'T', 'MCD', 'NKE', 'CVX', 'NEE', 'LMT', 'UPS', 'LOW', 'AMGN', 'SCHW',
    'BLK', 'SYK', 'ADP', 'TJX', 'MDLZ', 'C', 'DE', 'AMT', 'SPOT', 'PFE', 'SO',
    'CL', 'BMY', 'TMUS', 'UNP', 'MS', 'BABA', 'FDX', 'USB', 'CVS', 'TGT', 'ABBV',
    'MO', 'F', 'GM', 'DAL', 'AAL', 'UAL', 'LUV', 'CCL', 'RCL', 'NCLH', 'MGM',
    'WYNN', 'LVS', 'BYD', 'CAH', 'WBA', 'RAD', 'KR', 'SYY', 'COST', 'TJX', 'DG',
    
    # Additional Major Companies (>$1B market cap)
    'AZN', 'STLA', 'CBRE', 'DTE', 'SWK', 'BXP', 'NBIX', 'NMR', 'ARES', 'NXPI',
    'GLW', 'TR', 'ARCC', 'CZR', 'INCY', 'FYBR', 'OFLX', 'JBGS', 'ASH', 'SB',
    'IPA', 'CVEO', 'LVRO', 'AXR', 'GIC', 'DALN', 'EXE', 'ARI', 'WELL', 'UHS',
    'CINF', 'NBTB', 'VLTO', 'EKSO', 'TLRY', 'WM', 'FSUN', 'PFG', 'CDP', 'PDM',
    'WU', 'DM', 'BOH', 'SITC', 'RVTY', 'BSRR', 'ALRS', 'SYRS', 'RITM', 'ESQ',
    'NBN', 'BMRC', 'CZWI', 'HEES', 'V', 'PG', 'UNH', 'MRK', 'BKNG', 'BA', 'SPOT',
    
    # REITs and Energy
    'EQIX', 'PLD', 'CCI', 'AMT', 'SBAC', 'DLR', 'PSA', 'O', 'WELL', 'VTR', 'ARE',
    'EPD', 'ET', 'KMI', 'OKE', 'WMB', 'MPLX', 'PAA', 'PAGP', 'SMLP', 'CEQP',
    
    # Financial Services
    'BRK-A', 'BRK-B', 'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC',
    'COF', 'SCHW', 'BLK', 'SPGI', 'ICE', 'CME', 'MCO', 'MSCI', 'NDAQ', 'CBOE',
    
    # Healthcare & Biotech
    'JNJ', 'PFE', 'ABT', 'MRK', 'LLY', 'TMO', 'DHR', 'AMGN', 'GILD', 'BIIB',
    'VRTX', 'REGN', 'MRNA', 'BNTX', 'ZTS', 'BMY', 'AZN', 'NVO', 'ROCHE', 'SNY',
    
    # Technology Services
    'CRM', 'NOW', 'WDAY', 'TEAM', 'ZM', 'DOCU', 'ZS', 'OKTA', 'SPLK', 'SNOW',
    'PLTR', 'U', 'PATH', 'DDOG', 'NET', 'CRWD', 'S', 'TWLO', 'WORK', 'FIVN'
}

def send_telegram_message(message):
    """Send message with fallback attempts"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Try with HTML formatting
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("📡 Message sent!")
            return True
            
        # Fallback to plain text
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("📡 Message sent (plain text)!")
            return True
            
        print(f"❌ Message failed: {response.status_code} - {response.text}")
        return False
        
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def get_earnings_calendar():
    """Get earnings for major stocks only - NO API RATE LIMITS"""
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
            
            # Filter to major stocks using our curated list (NO API CALLS)
            for stock in earnings.get('earningsCalendar', []):
                symbol = stock.get('symbol')
                if symbol in MAJOR_STOCKS:  # Simple lookup - no API calls!
                    print(f"    ✅ Found major stock: {symbol}")
                    if stock.get('hour') == 'bmo':
                        bmo_earnings.append(stock)
                    elif stock.get('hour') == 'amc':
                        amc_earnings.append(stock)
            
            print(f"✅ Filtered to {len(bmo_earnings)} BMO + {len(amc_earnings)} AMC major stocks")
            return bmo_earnings, amc_earnings
        else:
            print(f"❌ Earnings API failed: {response.status_code}")
            return [], []
    except Exception as e:
        print(f"❌ Earnings API error: {e}")
        return [], []

def analyze_stock_gap(symbol):
    """Analyze stock with rate limiting protection"""
    try:
        print(f"  📊 Analyzing {symbol}...")
        stock = yf.Ticker(symbol)
        
        # Add delay to avoid rate limits
        time.sleep(0.5)
        
        hist = stock.history(period="2d")
        if len(hist) < 2:
            print(f"    ❌ No price data for {symbol}")
            return None
        
        yesterday_close = hist['Close'].iloc[-2]
        current_price = hist['Close'].iloc[-1]
        gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
        
        # Calculate volume surge
        recent_volume = hist['Volume'].iloc[-1]
        avg_volume_5d = hist['Volume'].mean()
        volume_surge = recent_volume / avg_volume_5d if avg_volume_5d > 0 else 1
        
        # Get basic company info (minimal API calls)
        try:
            time.sleep(0.3)  # Rate limit protection
            info = stock.info
            company_name = info.get('shortName', symbol)
            market_cap = info.get('marketCap', 0)
        except:
            company_name = symbol
            market_cap = 0
        
        print(f"    💰 {symbol} ({company_name}): ${yesterday_close:.2f} → ${current_price:.2f} ({gap_percent:+.1f}%)")
        
        return {
            'symbol': symbol,
            'company_name': company_name,
            'yesterday_close': yesterday_close,
            'current_price': current_price,
            'gap_percent': gap_percent,
            'volume_surge': volume_surge,
            'market_cap': market_cap
        }
    except Exception as e:
        print(f"    ❌ Error analyzing {symbol}: {e}")
        return None

def get_earnings_results(symbol):
    """Get earnings surprise data"""
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
        pass
    return None

def calculate_opportunity_score(stock_data, earnings_data, earnings_type):
    """Calculate opportunity score"""
    score = 0
    gap = abs(stock_data['gap_percent'])
    
    # Base score from gap size
    if 2 <= gap <= 6:
        score += 100
    elif 1.5 <= gap < 2 or 6 < gap <= 8:
        score += 80
    elif 1 <= gap < 1.5 or 8 < gap <= 10:
        score += 60
    else:
        score += 20
    
    # Earnings surprise bonus
    if earnings_data:
        eps_surprise = earnings_data.get('eps_surprise', 0)
        if eps_surprise > 0:
            score += 50  # Beat earnings
        elif eps_surprise < -0.05:
            score += 30  # Significant miss
    
    # Volume surge bonus
    volume_surge = stock_data.get('volume_surge', 1)
    if volume_surge > 2:
        score += 30
    elif volume_surge > 1.5:
        score += 20
    elif volume_surge > 1.2:
        score += 10
    
    # Market cap factor
    market_cap = stock_data.get('market_cap', 0)
    if market_cap > 50000000000:  # >$50B
        score += 20
    elif market_cap > 10000000000:  # >$10B
        score += 15
    elif market_cap > 5000000000:   # >$5B
        score += 10
    
    # AMC penalty
    if earnings_type == 'AMC':
        score -= 10
    
    return score

def generate_signal(stock_data, earnings_data, earnings_type):
    """Generate trading signal"""
    gap = stock_data['gap_percent']
    
    # Must have meaningful gap
    if abs(gap) < 1.0:
        return None
    
    # Skip extremely volatile gaps
    if abs(gap) > 12:
        return None
    
    # Generate signal
    if earnings_data:
        eps_surprise = earnings_data.get('eps_surprise', 0)
        if eps_surprise > 0 and gap > 0:
            return f"🚀 STRONG BUY - Beat + {gap:.1f}% gap [{earnings_type}]"
        elif eps_surprise < 0 and gap < 0:
            return f"📉 STRONG SHORT - Miss + {gap:.1f}% gap [{earnings_type}]"
        elif eps_surprise > 0 and gap < 0:
            return f"🤔 CONTRARIAN - Beat but {gap:.1f}% down [{earnings_type}]"
        elif eps_surprise < 0 and gap > 0:
            return f"⚠️ RISKY - Miss but {gap:.1f}% up [{earnings_type}]"
    
    # Gap-only signal
    direction = "BUY" if gap > 0 else "SHORT"
    return f"🟡 {direction} - {gap:.1f}% gap [{earnings_type}]"

def main_earnings_scan():
    print("🚨 SMART EARNINGS SCAN - TOP 5 RECOMMENDATIONS 🚨")
    print("=" * 60)
    
    bmo_earnings, amc_earnings = get_earnings_calendar()
    total_earnings = len(bmo_earnings) + len(amc_earnings)
    
    if total_earnings == 0:
        msg = "📭 No major earnings today"
        print(msg)
        send_telegram_message(msg)
        return
    
    print(f"📊 Analyzing {total_earnings} major stocks...")
    
    all_opportunities = []
    
    # Process BMO earnings
    for earnings_item in bmo_earnings:
        symbol = earnings_item.get('symbol')
        print(f"[BMO] {symbol}")
        
        stock_data = analyze_stock_gap(symbol)
        if not stock_data:
            continue
        
        earnings_results = get_earnings_results(symbol)
        signal = generate_signal(stock_data, earnings_results, 'BMO')
        
        if signal:
            score = calculate_opportunity_score(stock_data, earnings_results, 'BMO')
            all_opportunities.append({
                'symbol': symbol,
                'company_name': stock_data['company_name'],
                'signal': signal,
                'gap': stock_data['gap_percent'],
                'price_from': stock_data['yesterday_close'],
                'price_to': stock_data['current_price'],
                'earnings_type': 'BMO',
                'score': score,
                'earnings_data': earnings_results
            })
            print(f"    🎯 {signal} (Score: {score})")
        else:
            print(f"    ❌ No signal")
        print()
    
    # Process AMC earnings
    for earnings_item in amc_earnings:
        symbol = earnings_item.get('symbol')
        print(f"[AMC] {symbol}")
        
        stock_data = analyze_stock_gap(symbol)
        if not stock_data:
            continue
        
        earnings_results = get_earnings_results(symbol)
        signal = generate_signal(stock_data, earnings_results, 'AMC')
        
        if signal:
            score = calculate_opportunity_score(stock_data, earnings_results, 'AMC')
            all_opportunities.append({
                'symbol': symbol,
                'company_name': stock_data['company_name'],
                'signal': signal,
                'gap': stock_data['gap_percent'],
                'price_from': stock_data['yesterday_close'],
                'price_to': stock_data['current_price'],
                'earnings_type': 'AMC',
                'score': score,
                'earnings_data': earnings_results
            })
            print(f"    🎯 {signal} (Score: {score})")
        else:
            print(f"    ❌ No signal")
        print()
    
    print("=" * 60)
    
    # Rank and get TOP 5
    if all_opportunities:
        top_opportunities = sorted(all_opportunities, key=lambda x: x['score'], reverse=True)[:5]
        
        uk_tz = pytz.timezone('Europe/London')
        current_time = datetime.now(uk_tz)
        
        channel_msg = f"🚨 <b>TOP 5 EARNINGS PLAYS</b> 🚨\n"
        channel_msg += f"📅 {current_time.strftime('%b %d, %Y at %H:%M UK')}\n"
        channel_msg += f"📊 Analyzed {total_earnings} stocks → Top 5 picks\n\n"
        
        for i, opp in enumerate(top_opportunities, 1):
            channel_msg += f"<b>#{i} {opp['symbol']}</b> ({opp['company_name']})\n"
            channel_msg += f"📈 Gap: <b>{opp['gap']:+.1f}%</b> (${opp['price_from']:.2f} → ${opp['price_to']:.2f})\n"
            
            if opp['earnings_data']:
                eps_surprise = opp['earnings_data'].get('eps_surprise', 0)
                channel_msg += f"📊 EPS surprise: <b>${eps_surprise:+.2f}</b>\n"
            
            channel_msg += f"🎯 <b>{opp['signal']}</b>\n"
            channel_msg += f"⭐ Score: {opp['score']}/200\n\n"
        
        channel_msg += "🎯 <b>Top picks from major stocks!</b>\n"
        channel_msg += "📝 Trade with proper risk management!"
        
        print("🏆 TOP 5 RECOMMENDATIONS:")
        for i, opp in enumerate(top_opportunities, 1):
            print(f"#{i} {opp['symbol']}: {opp['signal']} (Score: {opp['score']})")
        
        if send_telegram_message(channel_msg):
            print("✅ Top 5 recommendations sent!")
        else:
            print("❌ Failed to send recommendations")
    else:
        msg = f"📭 No strong opportunities from {total_earnings} major earnings today"
        print(msg)
        send_telegram_message(msg)

def send_startup_message():
    """Send startup notification"""
    uk_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_tz)
    startup_msg = f"🤖 <b>SMART EARNINGS BOT ONLINE</b>\n"
    startup_msg += f"📅 Started: {current_time.strftime('%A, %B %d at %H:%M UK')}\n"
    startup_msg += f"🚀 Running 24/7 on Railway\n"
    startup_msg += f"📊 Monitoring {len(MAJOR_STOCKS)} major stocks\n"
    startup_msg += f"🏆 Smart ranking → TOP 5 recommendations only\n"
    startup_msg += f"⏰ Daily scans at 2:15 PM UK\n\n"
    startup_msg += f"✅ Ready to find the best opportunities!"
    
    if send_telegram_message(startup_msg):
        print("✅ Startup message sent!")
    else:
        print("❌ Failed to send startup message")

if __name__ == "__main__":
    print("🤖 SMART TOP 5 EARNINGS BOT")
    print(f"📊 Monitoring {len(MAJOR_STOCKS)} major stocks (NYSE + NASDAQ)")
    print("🏆 Intelligent opportunity scoring")
    
    # Send startup notification
    send_startup_message()
    
    # Schedule the daily scan
    schedule.every().day.at("14:15").do(main_earnings_scan)
    
    print("📅 Scheduled for 2:15 PM UK time daily")
    print("🔄 Running initial scan...")
    
    # Run initial scan
    main_earnings_scan()
    
    print("\n⏳ Bot waiting for next scheduled scan...")
    print("🎯 Smart recommendations, running 24/7!")
    
    # Keep the bot running
    while True:
        schedule.run_pending()
        time.sleep(60)
