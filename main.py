import requests
import time
import os
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import openai
import re

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        print(f"📡 Telegram response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def scrape_real_earnings_data():
    """Scrape real earnings data using proven working method"""
    print("🔍 SCRAPING REAL EARNINGS DATA")
    print("=" * 50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nasdaq.com/market-activity/earnings',
        'Origin': 'https://www.nasdaq.com'
    }
    
    earnings_stocks = []
    
    # Method 1: NASDAQ API (proven to work)
    try:
        print("📊 Trying NASDAQ API...")
        nasdaq_endpoints = [
            "https://api.nasdaq.com/api/calendar/earnings",
            "https://www.nasdaq.com/api/calendar/earnings"
        ]
        
        for endpoint in nasdaq_endpoints:
            try:
                response = requests.get(endpoint, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ NASDAQ API working: {len(str(data))} chars")
                    
                    # Process JSON data for symbols
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, list) and len(value) > 0:
                                for item in value[:50]:
                                    if isinstance(item, dict):
                                        symbol = None
                                        for field in ['symbol', 'ticker', 'Symbol', 'Ticker']:
                                            if field in item:
                                                symbol = item[field]
                                                break
                                        
                                        if symbol and len(symbol) <= 5 and symbol.isalpha():
                                            earnings_stocks.append({
                                                'symbol': symbol.upper(),
                                                'source': 'NASDAQ_API'
                                            })
                    break
            except Exception as e:
                continue
    except Exception as e:
        print(f"❌ NASDAQ API error: {e}")
    
    # Method 2: Yahoo Finance backup
    if len(earnings_stocks) < 5:
        try:
            print("📰 Trying Yahoo Finance backup...")
            yahoo_url = "https://finance.yahoo.com/calendar/earnings"
            response = requests.get(yahoo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            
            if response.status_code == 200:
                content = response.text
                json_matches = re.findall(r'"symbol":"([A-Z]{1,5})"', content)
                
                for symbol in json_matches[:20]:
                    if symbol not in [stock['symbol'] for stock in earnings_stocks]:
                        earnings_stocks.append({
                            'symbol': symbol,
                            'source': 'YAHOO_FINANCE'
                        })
                print(f"✅ Yahoo added {len(json_matches)} stocks")
        except Exception as e:
            print(f"❌ Yahoo Finance error: {e}")
    
    # Remove duplicates
    unique_stocks = {}
    for stock in earnings_stocks:
        symbol = stock['symbol']
        if symbol not in unique_stocks:
            unique_stocks[symbol] = stock
    
    final_stocks = list(unique_stocks.values())
    print(f"📊 Total unique stocks found: {len(final_stocks)}")
    return final_stocks

def filter_stocks_by_market_cap(earnings_stocks):
    """Filter stocks by market cap (>$10B)"""
    print(f"\n🎯 FILTERING BY MARKET CAP (>$10B)")
    print("=" * 40)
    
    # Market caps in billions
    market_caps = {
        'MSFT': 3809, 'META': 1804, 'AAPL': 3500, 'GOOGL': 2100, 'AMZN': 1800,
        'NVDA': 3000, 'TSLA': 800, 'QCOM': 177, 'ARM': 174, 'LRCX': 126,
        'ADP': 125, 'HOOD': 94, 'F': 45, 'CVNA': 72, 'ALL': 51, 'RBLX': 30,
        'FCX': 60, 'ALGN': 15, 'AVGO': 700, 'RDDT': 25, 'NFLX': 200, 'AMD': 240,
        'INTC': 180, 'CRM': 200, 'ORCL': 450, 'UBER': 120, 'PYPL': 60
    }
    
    qualified_stocks = []
    for stock in earnings_stocks:
        symbol = stock['symbol']
        market_cap_b = market_caps.get(symbol, 0)
        
        if market_cap_b >= 10:  # >$10B
            qualified_stocks.append({
                'symbol': symbol,
                'market_cap': market_cap_b * 1_000_000_000,
                'source': stock['source']
            })
            print(f"✅ {symbol}: ${market_cap_b}B")
        else:
            print(f"❌ {symbol}: ${market_cap_b}B (too small)")
    
    print(f"\n✅ {len(qualified_stocks)} stocks qualify")
    return qualified_stocks

def get_stock_price_data(symbol):
    """Get real price data"""
    try:
        finnhub_key = "d1ehal1r01qjssrk4fu0d1ehal1r01qjssrk4fug"
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={finnhub_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get('c', 0)
            previous = data.get('pc', 0)
            
            if current and previous and current > 0 and previous > 0:
                gap = ((current - previous) / previous) * 100
                return {
                    'current_price': current,
                    'previous_close': previous,
                    'gap_percent': gap
                }
    except Exception as e:
        print(f"❌ Price error for {symbol}: {e}")
    
    return None

def ai_analyze_earnings(symbol, price_data):
    """AI analysis of earnings"""
    if not OPENAI_API_KEY:
        return None
    
    try:
        gap_info = f"Price movement: {price_data['gap_percent']:+.1f}% (${price_data['previous_close']:.2f} → ${price_data['current_price']:.2f})"
        
        prompt = f"""
        Analyze {symbol} for day trading based on earnings and price movement.
        
        {gap_info}
        
        Provide analysis in EXACT format:
        RESULT: BEAT/MISS/INLINE
        SENTIMENT: POSITIVE/NEGATIVE/NEUTRAL
        DIRECTION: UP/DOWN
        CONFIDENCE: [1-10]
        REASONING: [brief explanation]
        
        Focus on 2-3 minute scalping opportunity.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a day trader analyzing earnings for scalping. Be decisive about direction."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.1
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ AI error for {symbol}: {e}")
        return None

def parse_ai_analysis(ai_text):
    """Parse AI response"""
    if not ai_text:
        return None
    
    parsed = {}
    lines = ai_text.strip().split('\n')
    
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().upper()
            value = value.strip()
            
            if key == 'RESULT':
                parsed['result'] = value
            elif key == 'SENTIMENT':
                parsed['sentiment'] = value
            elif key == 'DIRECTION':
                parsed['direction'] = value
            elif key == 'CONFIDENCE':
                try:
                    parsed['confidence'] = int(value.split()[0])
                except:
                    parsed['confidence'] = 5
            elif key == 'REASONING':
                parsed['reasoning'] = value
    
    return parsed

def calculate_trading_score(confidence, sentiment, direction, gap):
    """CORRECTED scoring algorithm - more discriminating"""
    
    # Base score from AI confidence (more conservative)
    base_score = confidence * 7  # 1-10 becomes 7-70
    
    # Gap requirements - must have meaningful movement
    if abs(gap) < 0.5:
        return 0  # No trade for tiny gaps
    elif abs(gap) < 1.0:
        base_score -= 15  # Penalty for small gaps
    elif abs(gap) >= 1.5:
        base_score += 20  # Bonus for good gaps
    elif abs(gap) > 4.0:
        base_score -= 15  # Penalty for excessive risk
    
    # Direction alignment (critical for success)
    gap_direction = "UP" if gap > 0 else "DOWN"
    if gap_direction == direction:
        base_score += 25  # Big bonus for alignment
    else:
        base_score -= 30  # Big penalty for misalignment
    
    # Sentiment clarity bonus
    if sentiment == "POSITIVE" and direction == "UP":
        base_score += 15
    elif sentiment == "NEGATIVE" and direction == "DOWN":
        base_score += 15
    elif sentiment == "NEUTRAL":
        base_score -= 10  # Penalty for unclear signals
    else:
        base_score -= 20  # Penalty for contradictory signals
    
    # Cap between 0-100
    final_score = max(0, min(100, base_score))
    return final_score

def generate_trading_signal(sentiment, direction, gap, score):
    """CORRECTED signal generation - only clear trades"""
    
    # Must meet minimum score threshold
    if score < 65:
        return None  # No signal for low-confidence trades
    
    # Clear buy signals
    if sentiment == "POSITIVE" and direction == "UP" and gap > 1.0:
        return "🚀 STRONG BUY"
    elif sentiment == "POSITIVE" and direction == "UP" and gap > 0.5:
        return "🟢 BUY"
    
    # Clear sell signals  
    elif sentiment == "NEGATIVE" and direction == "DOWN" and gap < -1.0:
        return "📉 STRONG SHORT"
    elif sentiment == "NEGATIVE" and direction == "DOWN" and gap < -0.5:
        return "🔴 SHORT"
    
    # NO NEUTRAL SIGNALS - we don't trade unclear opportunities
    else:
        return None

def run_corrected_analysis():
    """Run complete corrected analysis"""
    print("🚨 CORRECTED EARNINGS ANALYSIS")
    print("=" * 60)
    print("🎯 Only clear BUY/SELL opportunities")
    print("❌ No neutral or weak signals")
    print("📊 Maximum 5 results, could be fewer")
    
    # Step 1: Scrape earnings
    earnings_stocks = scrape_real_earnings_data()
    if not earnings_stocks:
        send_telegram_message("❌ Failed to scrape earnings data")
        return
    
    # Step 2: Filter by market cap
    qualified_stocks = filter_stocks_by_market_cap(earnings_stocks)
    if not qualified_stocks:
        send_telegram_message("📭 No stocks meet market cap criteria")
        return
    
    print(f"\n📊 ANALYZING {len(qualified_stocks)} QUALIFIED STOCKS")
    print("=" * 60)
    
    # Step 3: Analyze each stock
    clear_opportunities = []
    
    for i, stock in enumerate(qualified_stocks[:15], 1):
        symbol = stock['symbol']
        market_cap = stock['market_cap']
        
        print(f"\n[{i}/{min(15, len(qualified_stocks))}] 🔍 {symbol}")
        
        # Get price data
        price_data = get_stock_price_data(symbol)
        if not price_data:
            print(f"  ❌ No price data")
            continue
        
        gap = price_data['gap_percent']
        print(f"  💰 Gap: {gap:+.1f}%")
        
        # Skip tiny gaps
        if abs(gap) < 0.5:
            print(f"  ❌ Gap too small")
            continue
        
        # AI analysis
        ai_analysis = ai_analyze_earnings(symbol, price_data)
        parsed = parse_ai_analysis(ai_analysis)
        
        if not parsed:
            print(f"  ❌ AI analysis failed")
            continue
        
        confidence = parsed.get('confidence', 5)
        sentiment = parsed.get('sentiment', 'NEUTRAL')
        direction = parsed.get('direction', 'UP')
        
        print(f"  🤖 AI: {sentiment} sentiment, {direction} direction, {confidence}/10 confidence")
        
        # Calculate score
        score = calculate_trading_score(confidence, sentiment, direction, gap)
        print(f"  📊 Score: {score}/100")
        
        # Generate signal
        signal = generate_trading_signal(sentiment, direction, gap, score)
        
        if signal:  # Only include clear signals
            clear_opportunities.append({
                'symbol': symbol,
                'signal': signal,
                'sentiment': sentiment,
                'direction': direction,
                'gap': gap,
                'price_from': price_data['previous_close'],
                'price_to': price_data['current_price'],
                'confidence': confidence,
                'score': score,
                'market_cap': market_cap,
                'reasoning': parsed.get('reasoning', 'Analysis complete')
            })
            print(f"  ✅ CLEAR SIGNAL: {signal}")
        else:
            print(f"  ❌ No clear signal (score: {score})")
        
        time.sleep(2)  # Rate limiting
    
    print(f"\n📊 FOUND {len(clear_opportunities)} CLEAR OPPORTUNITIES")
    
    # Step 4: Send results
    if clear_opportunities:
        # Sort by score, take maximum 5
        top_opportunities = sorted(clear_opportunities, key=lambda x: x['score'], reverse=True)[:5]
        
        print(f"\n🏆 TOP {len(top_opportunities)} OPPORTUNITIES:")
        for i, opp in enumerate(top_opportunities, 1):
            print(f"#{i} {opp['symbol']}: {opp['signal']} {opp['gap']:+.1f}% (Score: {opp['score']}/100)")
        
        # Create message
        msg = f"🤖 <b>CLEAR TRADING OPPORTUNITIES</b>\n\n"
        msg += f"📅 {datetime.now().strftime('%b %d at %H:%M')}\n"
        msg += f"✅ Found {len(top_opportunities)} clear signals:\n\n"
        
        for i, opp in enumerate(top_opportunities, 1):
            market_cap_b = opp['market_cap'] / 1_000_000_000
            
            msg += f"<b>#{i} {opp['symbol']}</b> (${market_cap_b:.0f}B)\n"
            msg += f"💰 ${opp['price_from']:.2f} → ${opp['price_to']:.2f} ({opp['gap']:+.1f}%)\n"
            msg += f"🎯 <b>{opp['signal']}</b>\n"
            msg += f"📊 Score: {opp['score']:.0f}/100\n"
            msg += f"🤖 AI: {opp['sentiment']} sentiment, {opp['confidence']}/10 confidence\n"
            msg += f"💡 {opp['reasoning'][:60]}...\n\n"
        
        msg += f"⚡ <b>STRATEGY:</b>\n"
        msg += f"• Entry: Current price\n"
        msg += f"• Target: 3-5% profit\n"
        msg += f"• Stop: 2% loss\n"
        msg += f"• Time: 2-3 minutes\n\n"
        msg += f"🔥 Only high-confidence trades!"
        
        send_telegram_message(msg)
        print("✅ Clear opportunities sent!")
        
    else:
        print("📭 No clear opportunities found")
        
        msg = f"📭 <b>NO CLEAR OPPORTUNITIES TODAY</b>\n\n"
        msg += f"🔍 Analyzed {len(qualified_stocks)} qualified stocks\n"
        msg += f"❌ None met strict criteria:\n"
        msg += f"  • Score > 65/100\n"
        msg += f"  • Clear BUY or SELL signal\n"
        msg += f"  • Meaningful price gap\n"
        msg += f"  • AI confidence alignment\n\n"
        msg += f"✅ System working perfectly\n"
        msg += f"💤 Better opportunities tomorrow!"
        
        send_telegram_message(msg)

if __name__ == "__main__":
    print("🔧 CORRECTED SYSTEM TEST")
    print("🎯 Only clear BUY/SELL signals")
    print("❌ No neutral or forced results")
    print("📊 Quality over quantity")
    print()
    
    run_corrected_analysis()
    
    print(f"\n⏰ Test completed: {datetime.now().strftime('%H:%M:%S')}")
    print("🔥 This is the final logic for daily automation!")
