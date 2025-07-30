import requests
import schedule
import time
import pytz
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import openai
import re

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def get_uk_time():
    """Get current UK time (handles GMT/BST automatically)"""
    uk_tz = pytz.timezone('Europe/London')
    return datetime.now(uk_tz)

def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("📡 Telegram message sent!")
            return True
        else:
            print(f"❌ Telegram failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def scrape_nasdaq_earnings_full():
    """Scrape complete NASDAQ earnings calendar"""
    try:
        print("🔍 Scraping NASDAQ earnings calendar...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        all_earnings = []
        
        # Scrape multiple pages of NASDAQ earnings
        for page in range(1, 4):  # Pages 1-3 (300 companies)
            try:
                url = f"https://www.nasdaq.com/market-activity/earnings?page={page}"
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for earnings table
                    tables = soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')[1:]  # Skip header
                        
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 4:
                                try:
                                    # Extract data from table cells
                                    symbol_cell = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                                    company_cell = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                                    market_cap_cell = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                                    
                                    # Clean up symbol (remove extra characters)
                                    symbol = re.sub(r'[^A-Z]', '', symbol_cell.upper())
                                    
                                    # Extract market cap number
                                    market_cap = 0
                                    if market_cap_cell and '$' in market_cap_cell:
                                        # Extract numeric value from market cap
                                        cap_match = re.search(r'\$?([\d,]+)', market_cap_cell.replace(',', ''))
                                        if cap_match:
                                            market_cap = int(cap_match.group(1)) * 1000000  # Assume millions
                                    
                                    if symbol and len(symbol) <= 5 and len(symbol) >= 1:
                                        all_earnings.append({
                                            'symbol': symbol,
                                            'company': company_cell,
                                            'market_cap': market_cap
                                        })
                                
                                except Exception as e:
                                    continue
                
                print(f"✅ Scraped page {page}")
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error scraping page {page}: {e}")
                continue
        
        # Remove duplicates
        seen = set()
        unique_earnings = []
        for stock in all_earnings:
            if stock['symbol'] not in seen:
                seen.add(stock['symbol'])
                unique_earnings.append(stock)
        
        print(f"✅ Found {len(unique_earnings)} unique earnings stocks")
        return unique_earnings
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        # Fallback to known major stocks for today
        return [
            {'symbol': 'MSFT', 'company': 'Microsoft Corporation', 'market_cap': 3809178730813},
            {'symbol': 'META', 'company': 'Meta Platforms, Inc.', 'market_cap': 1804356663700},
            {'symbol': 'QCOM', 'company': 'QUALCOMM Incorporated', 'market_cap': 176832900000},
            {'symbol': 'LRCX', 'company': 'Lam Research Corporation', 'market_cap': 126146617160},
            {'symbol': 'ADP', 'company': 'Automatic Data Processing, Inc.', 'market_cap': 124573632441}
        ]

def filter_qualified_stocks(earnings_list):
    """Filter stocks by scalping criteria"""
    try:
        print("🎯 Filtering for scalping opportunities...")
        
        qualified = []
        
        for stock in earnings_list:
            # Apply filters
            market_cap = stock.get('market_cap', 0)
            symbol = stock.get('symbol', '')
            
            # Market cap filter (>$10B for high liquidity)
            if market_cap < 10_000_000_000:
                continue
            
            # Symbol validation
            if not symbol or len(symbol) > 5:
                continue
            
            # Add to qualified list
            qualified.append(stock)
        
        # Sort by market cap (largest first)
        qualified.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
        
        # Take top 20 for analysis
        top_qualified = qualified[:20]
        
        print(f"✅ {len(top_qualified)} stocks qualify for analysis")
        return top_qualified
        
    except Exception as e:
        print(f"❌ Filtering error: {e}")
        return []

def get_stock_price_data(symbol):
    """Get current price and gap data"""
    try:
        # Try multiple sources for price data
        
        # Method 1: Finnhub (most reliable)
        try:
            finnhub_key = "d1ehal1r01qjssrk4fu0d1ehal1r01qjssrk4fug"  # Demo key
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={finnhub_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                current = data.get('c', 0)
                previous = data.get('pc', 0)
                
                if current and previous:
                    gap = ((current - previous) / previous) * 100
                    return {
                        'current_price': current,
                        'previous_close': previous,
                        'gap_percent': gap
                    }
        except:
            pass
        
        # Method 2: Alpha Vantage fallback
        try:
            av_key = "demo"
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={av_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                quote = data.get("Global Quote", {})
                
                current = float(quote.get("05. price", 0))
                previous = float(quote.get("08. previous close", 0))
                
                if current and previous:
                    gap = ((current - previous) / previous) * 100
                    return {
                        'current_price': current,
                        'previous_close': previous,
                        'gap_percent': gap
                    }
        except:
            pass
        
        return None
        
    except Exception as e:
        print(f"❌ Price data error for {symbol}: {e}")
        return None

def scrape_earnings_news(symbol):
    """Scrape earnings news and data for a stock"""
    try:
        print(f"📰 Scraping earnings news for {symbol}...")
        
        # Search for earnings news
        search_query = f"{symbol} earnings Q2 2025 results"
        
        # Try Google News search (simplified)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Search multiple sources
        news_data = []
        
        # Method 1: Yahoo Finance earnings page
        try:
            yahoo_url = f"https://finance.yahoo.com/quote/{symbol}"
            response = requests.get(yahoo_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for earnings-related text
                text_content = soup.get_text()
                
                # Extract earnings-related sentences
                sentences = text_content.split('.')
                earnings_sentences = []
                
                for sentence in sentences[:50]:  # First 50 sentences
                    if any(word in sentence.lower() for word in ['earnings', 'eps', 'revenue', 'beat', 'miss', 'expect']):
                        earnings_sentences.append(sentence.strip())
                
                if earnings_sentences:
                    news_data.extend(earnings_sentences[:5])  # Top 5 relevant sentences
        except:
            pass
        
        # Return combined news data
        return " ".join(news_data) if news_data else f"No specific earnings news found for {symbol}"
        
    except Exception as e:
        print(f"❌ News scraping error for {symbol}: {e}")
        return f"Unable to fetch earnings news for {symbol}"

def analyze_with_ai(symbol, company, earnings_news, price_data):
    """Use AI to analyze earnings and predict direction"""
    try:
        print(f"🤖 AI analyzing {symbol}...")
        
        if not OPENAI_API_KEY:
            print("❌ No OpenAI API key")
            return None
        
        # Create comprehensive prompt
        gap_info = ""
        if price_data:
            gap_info = f"Current price gap: {price_data['gap_percent']:+.1f}% (${price_data['previous_close']:.2f} → ${price_data['current_price']:.2f})"
        
        prompt = f"""
        Analyze {symbol} ({company}) earnings for scalping opportunity.
        
        Earnings news/data:
        {earnings_news}
        
        {gap_info}
        
        Provide analysis in this EXACT format:
        RESULT: BEAT/MISS/INLINE
        SENTIMENT: POSITIVE/NEGATIVE/NEUTRAL
        DIRECTION: UP/DOWN
        CONFIDENCE: [1-10]
        REASONING: [brief explanation why]
        
        Focus on: Did they beat/miss EPS estimates? Any guidance changes? Should stock go UP or DOWN?
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert earnings analyst. Analyze earnings for short-term trading opportunities."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.1
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ AI analysis error for {symbol}: {e}")
        return None

def parse_ai_analysis(analysis_text):
    """Parse AI response into structured data"""
    try:
        if not analysis_text:
            return None
            
        parsed = {}
        lines = analysis_text.strip().split('\n')
        
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
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return None

def main_earnings_automation():
    """Complete automated earnings analysis"""
    print("🤖 AUTOMATED EARNINGS ANALYSIS")
    print("=" * 60)
    
    uk_time = get_uk_time()
    
    print(f"📅 Analysis time: {uk_time.strftime('%A, %B %d at %H:%M UK')}")
    print(f"🎯 Target: High-cap stocks with earnings today")
    print(f"⏰ US Market opens in 20 minutes (2:30 PM UK)")
    
    # Step 1: Scrape all earnings
    all_earnings = scrape_nasdaq_earnings_full()
    if not all_earnings:
        send_telegram_message("❌ Failed to get earnings data")
        return
    
    # Step 2: Filter qualified stocks
    qualified_stocks = filter_qualified_stocks(all_earnings)
    if not qualified_stocks:
        send_telegram_message("📭 No qualified earnings opportunities today")
        return
    
    print(f"📊 Analyzing {len(qualified_stocks)} qualified stocks...")
    
    # Step 3: Analyze each qualified stock
    opportunities = []
    
    for i, stock in enumerate(qualified_stocks[:15]):  # Limit to top 15
        symbol = stock['symbol']
        company = stock['company']
        market_cap = stock['market_cap']
        
        print(f"\n🔍 [{i+1}/{min(15, len(qualified_stocks))}] Analyzing {symbol}...")
        
        # Get price data
        price_data = get_stock_price_data(symbol)
        if not price_data:
            print(f"❌ {symbol}: No price data")
            continue
        
        # Skip if gap is too small
        if abs(price_data['gap_percent']) < 0.5:
            print(f"❌ {symbol}: Gap too small ({price_data['gap_percent']:+.1f}%)")
            continue
        
        # Get earnings news
        earnings_news = scrape_earnings_news(symbol)
        
        # AI analysis
        ai_analysis = analyze_with_ai(symbol, company, earnings_news, price_data)
        parsed = parse_ai_analysis(ai_analysis)
        
        if not parsed:
            print(f"❌ {symbol}: AI analysis failed")
            continue
        
        # Calculate combined score
        confidence = parsed.get('confidence', 5)
        sentiment = parsed.get('sentiment', 'NEUTRAL')
        direction = parsed.get('direction', 'UP')
        gap = price_data['gap_percent']
        
        # Score calculation
        base_score = confidence * 10
        
        # Gap alignment bonus
        gap_direction = "UP" if gap > 0 else "DOWN"
        if gap_direction == direction:
            base_score += min(25, abs(gap) * 8)
        else:
            base_score -= 15
        
        # Size bonus for bigger gaps
        if abs(gap) > 2:
            base_score += 10
        
        final_score = max(0, min(100, base_score))
        
        # Generate signal
        if sentiment == "POSITIVE" and gap > 1:
            signal = "🚀 STRONG BUY"
        elif sentiment == "NEGATIVE" and gap < -1:
            signal = "📉 STRONG SHORT"
        elif gap > 0.5:
            signal = "🟢 BUY"
        elif gap < -0.5:
            signal = "🔴 SHORT"
        else:
            signal = "🟡 NEUTRAL"
        
        if final_score >= 50:  # Minimum threshold
            opportunities.append({
                'symbol': symbol,
                'company': company,
                'signal': signal,
                'sentiment': sentiment,
                'direction': direction,
                'gap': gap,
                'price_from': price_data['previous_close'],
                'price_to': price_data['current_price'],
                'confidence': confidence,
                'score': final_score,
                'market_cap': market_cap,
                'reasoning': parsed.get('reasoning', 'No reasoning')
            })
            
            print(f"✅ {symbol}: {signal} (Score: {final_score})")
        else:
            print(f"❌ {symbol}: Score too low ({final_score})")
        
        # Rate limiting
        time.sleep(3)
    
    print("\n" + "=" * 60)
    
    # Step 4: Send results
    if opportunities:
        # Sort by score and get top 5
        top_5 = sorted(opportunities, key=lambda x: x['score'], reverse=True)[:5]
        
        # Create message
        uk_time = get_uk_time()
        msg = f"🤖 <b>TOP 5 EARNINGS PLAYS - AUTOMATED</b>\n"
        msg += f"📅 {uk_time.strftime('%b %d at %H:%M UK')}\n"
        msg += f"⏰ <b>MARKET OPENS IN 20 MINUTES!</b>\n\n"
        
        for i, opp in enumerate(top_5, 1):
            market_cap_b = opp['market_cap'] / 1_000_000_000
            msg += f"<b>#{i} {opp['symbol']}</b> (${market_cap_b:.0f}B)\n"
            msg += f"💰 ${opp['price_from']:.2f} → ${opp['price_to']:.2f} ({opp['gap']:+.1f}%)\n"
            msg += f"🎯 <b>{opp['signal']}</b> | Score: {opp['score']:.0f}/100\n"
            msg += f"🤖 {opp['sentiment']} | AI: {opp['direction']} | Conf: {opp['confidence']}/10\n"
            msg += f"💡 {opp['reasoning'][:70]}...\n\n"
        
        msg += f"⚡ <b>EXECUTION PLAN:</b>\n"
        msg += f"• Review opportunities above\n"
        msg += f"• Enter positions at 2:30 PM UK sharp\n"
        msg += f"• Target: 3-5% profit | Stop: 2% loss\n"
        msg += f"• Exit within 2-3 minutes\n\n"
        msg += f"🤖 Fully automated analysis complete!"
        
        # Send to Telegram
        if send_telegram_message(msg):
            print("✅ Analysis sent to Telegram!")
            
            # Send quick summary
            summary = f"📊 <b>ANALYSIS COMPLETE</b>\n"
            summary += f"🔍 Scanned {len(all_earnings)} earnings stocks\n"
            summary += f"🎯 {len(qualified_stocks)} met criteria\n"
            summary += f"✅ Found {len(top_5)} strong opportunities\n"
            summary += f"🚀 Ready to trade!"
            
            send_telegram_message(summary)
        else:
            print("❌ Failed to send results")
    else:
        uk_time = get_uk_time()
        msg = f"📭 <b>NO STRONG OPPORTUNITIES TODAY</b>\n"
        msg += f"📅 {uk_time.strftime('%b %d at %H:%M UK')}\n"
        msg += f"🔍 Analyzed {len(qualified_stocks)} qualified stocks\n"
        msg += f"📊 Found {len(opportunities)} potential plays\n"
        msg += f"❌ None met minimum confidence threshold\n"
        msg += f"💤 Better opportunities tomorrow!"
        
        send_telegram_message(msg)
        print("📭 No strong opportunities found")

def should_run_analysis():
    """Check if it's time to run the analysis (2:10 PM UK)"""
    uk_time = get_uk_time()
    return uk_time.hour == 14 and uk_time.minute == 10

def send_startup_message():
    """Send bot startup notification"""
    uk_time = get_uk_time()
    
    msg = f"🤖 <b>EARNINGS AUTOMATION BOT ONLINE</b>\n"
    msg += f"📅 {uk_time.strftime('%A, %B %d at %H:%M UK')}\n\n"
    msg += f"🎯 <b>FULL AUTOMATION ACTIVE:</b>\n"
    msg += f"• Auto-scrapes NASDAQ earnings calendar\n"
    msg += f"• Filters for high-cap, liquid stocks\n"
    msg += f"• AI analyzes earnings sentiment\n"
    msg += f"• Ranks by confidence scores\n"
    msg += f"• Sends top 5 opportunities\n\n"
    msg += f"⏰ <b>DAILY SCAN: 2:10 PM UK</b>\n"
    msg += f"📈 Market opens: 2:30 PM UK (20min buffer)\n"
    msg += f"🎯 Strategy: 3-5% profit, 2% stop\n\n"
    msg += f"✅ Zero manual work required!"
    
    send_telegram_message(msg)

if __name__ == "__main__":
    print("🤖 COMPLETE EARNINGS AUTOMATION BOT")
    print("🔍 Auto-scrapes + AI analysis + ranking")
    print("⏰ Daily execution at 2:10 PM UK")
    
    # Send startup notification
    send_startup_message()
    
    print("📅 Will run at 2:10 PM UK (14:10) daily")
    print("⏳ Bot running... checking every minute for UK time")
    
    # Manual time checking loop (more reliable than schedule library for timezone)
    while True:
        if should_run_analysis():
            print("🚨 IT'S 2:10 PM UK - RUNNING ANALYSIS!")
            main_earnings_automation()
            # Sleep for 2 hours to avoid running again today
            print("😴 Analysis complete, sleeping until tomorrow...")
            time.sleep(7200)  # 2 hours
        else:
            uk_time = get_uk_time()
            if uk_time.minute % 15 == 0:  # Log every 15 minutes
                print(f"⏰ Current UK time: {uk_time.strftime('%H:%M')} - waiting for 14:10...")
            time.sleep(60)  # Check every minute
