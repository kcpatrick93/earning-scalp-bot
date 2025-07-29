import requests
import schedule
import time
import pytz
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import yfinance as yf
import openai

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7626751011:AAHHWa7ItXmjaP4-icgw8Aiy6_SdvhMdVK4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@kp_earning_report_stockbot")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI key if available
if OPENAI_API_KEY:
    openai.api_key = 
    
def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("📡 Message sent!")
            return True
        else:
            # Fallback to plain text
            data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def get_market_cap_and_price(symbol):
    """Get market cap and price data using yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get market cap
        info = ticker.info
        market_cap = info.get('marketCap', 0)
        
        # Get price data
        hist = ticker.history(period="2d", interval="1d")
        if len(hist) < 2:
            return None, None
            
        previous_close = hist['Close'].iloc[-2]
        current_price = hist['Close'].iloc[-1]
        
        # Try to get real-time/pre-market price
        try:
            current_price = info.get('regularMarketPrice', current_price)
            premarket_price = info.get('preMarketPrice')
            if premarket_price and premarket_price > 0:
                current_price = premarket_price
        except:
            pass
        
        gap_percent = ((current_price - previous_close) / previous_close) * 100
        
        price_data = {
            'symbol': symbol,
            'current_price': current_price,
            'previous_close': previous_close,
            'gap_percent': gap_percent
        }
        
        return market_cap, price_data
    except Exception as e:
        print(f"❌ Error getting data for {symbol}: {e}")
        return None, None

def analyze_earnings_with_llm(symbol, use_claude=False):
    """Use LLM to analyze earnings sentiment and direction"""
    try:
        prompt = f"""
        Analyze {symbol} earnings results released today (July 29, 2025).
        
        Research and provide:
        1. Beat/Miss/Inline: Did they beat, miss, or meet EPS and revenue estimates?
        2. Key highlights: Any major announcements, guidance changes, or surprises?
        3. Sentiment: Overall positive, negative, or neutral?
        4. Direction prediction: Should the stock go UP or DOWN based on the earnings?
        5. Confidence: Rate your confidence 1-10 (10 = very confident)
        
        Format your response as:
        RESULT: BEAT/MISS/INLINE
        EPS: [actual vs expected]
        REVENUE: [actual vs expected] 
        SENTIMENT: POSITIVE/NEGATIVE/NEUTRAL
        DIRECTION: UP/DOWN
        CONFIDENCE: [1-10]
        REASONING: [brief explanation]
        
        Be concise but thorough in your analysis.
        """
        
        if use_claude and CLAUDE_API_KEY:
            # Use Claude API (Anthropic)
            headers = {
                'Authorization': f'Bearer {CLAUDE_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['content'][0]['text']
            else:
                print(f"❌ Claude API error: {response.status_code}")
                return None
                
        elif OPENAI_API_KEY:
            # Use OpenAI GPT
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Much cheaper option - perfect for this task
                messages=[
                    {"role": "system", "content": "You are a financial analyst expert at analyzing earnings reports and predicting stock movements."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            return response.choices[0].message.content
        else:
            print("❌ No LLM API key configured")
            return None
            
    except Exception as e:
        print(f"❌ LLM analysis error for {symbol}: {e}")
        return None

def parse_llm_analysis(analysis_text):
    """Parse the LLM response into structured data"""
    try:
        lines = analysis_text.strip().split('\n')
        parsed = {}
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()
                
                if key == 'RESULT':
                    parsed['result'] = value
                elif key == 'EPS':
                    parsed['eps'] = value
                elif key == 'REVENUE':
                    parsed['revenue'] = value
                elif key == 'SENTIMENT':
                    parsed['sentiment'] = value
                elif key == 'DIRECTION':
                    parsed['direction'] = value
                elif key == 'CONFIDENCE':
                    try:
                        parsed['confidence'] = int(value.split()[0])  # Extract number
                    except:
                        parsed['confidence'] = 5
                elif key == 'REASONING':
                    parsed['reasoning'] = value
        
        return parsed
    except Exception as e:
        print(f"❌ Error parsing LLM analysis: {e}")
        return None

def scrape_nasdaq_bmo_earnings():
    """Get BMO (Before Market Open) earnings for today"""
    try:
        print("🔍 Getting today's BMO earnings...")
        
        # Try multiple sources
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Method 1: Try NASDAQ earnings page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # For now, use known BMO stocks from today + major earnings calendars
        # In production, you'd want to scrape multiple sources
        
        known_bmo_today = [
            'PG', 'UNH', 'MRK', 'BA', 'SPOT', 'AMT', 'RCL', 'ECL', 'UPS', 'PYPL', 'JCI',
            'AZN', 'STZ', 'NVR', 'CMG', 'MMM', 'GD', 'NOC', 'KO'
        ]
        
        print(f"✅ Found {len(known_bmo_today)} BMO earnings stocks")
        return known_bmo_today
        
    except Exception as e:
        print(f"❌ Error getting BMO earnings: {e}")
        return ['PG', 'UNH', 'BA', 'SPOT', 'UPS']  # Fallback

def analyze_earnings_opportunity(symbol):
    """Complete earnings analysis combining LLM + price data"""
    try:
        print(f"🔍 Analyzing {symbol}...")
        
        # Get market cap and price data
        market_cap, price_data = get_market_cap_and_price(symbol)
        
        if not market_cap or market_cap < 1_000_000_000:
            print(f"❌ {symbol}: Market cap too small or unavailable")
            return None
        
        if not price_data:
            print(f"❌ {symbol}: No price data")
            return None
        
        # Get LLM earnings analysis
        print(f"🤖 Getting LLM analysis for {symbol}...")
        llm_analysis = analyze_earnings_with_llm(symbol)
        
        if not llm_analysis:
            print(f"❌ {symbol}: LLM analysis failed")
            return None
        
        # Parse LLM response
        parsed_analysis = parse_llm_analysis(llm_analysis)
        
        if not parsed_analysis:
            print(f"❌ {symbol}: Failed to parse LLM response")
            return None
        
        # Combine LLM sentiment with gap analysis
        gap = price_data['gap_percent']
        sentiment = parsed_analysis.get('sentiment', 'NEUTRAL')
        direction = parsed_analysis.get('direction', 'UNKNOWN')
        confidence = parsed_analysis.get('confidence', 5)
        
        # Calculate combined score
        # LLM confidence + gap alignment bonus
        base_score = confidence * 10  # 1-10 becomes 10-100
        
        # Bonus if gap aligns with LLM direction
        gap_direction = "UP" if gap > 0 else "DOWN"
        if gap_direction == direction:
            alignment_bonus = min(20, abs(gap) * 5)  # Up to 20 point bonus
            base_score += alignment_bonus
        else:
            base_score -= 10  # Penalty for misalignment
        
        # Gap size matters for execution
        if abs(gap) < 0.5:
            base_score -= 20  # Too small to trade
        elif abs(gap) > 8:
            base_score -= 30  # Too risky
        
        final_score = max(0, min(100, base_score))
        
        # Determine trading signal
        if sentiment == "POSITIVE" and direction == "UP":
            if gap > 1:
                signal = f"🚀 STRONG BUY"
            else:
                signal = f"🟢 BUY"
        elif sentiment == "NEGATIVE" and direction == "DOWN":
            if gap < -1:
                signal = f"📉 STRONG SHORT"
            else:
                signal = f"🔴 SHORT"
        elif sentiment == "POSITIVE" and gap > 0:
            signal = f"🟡 CAUTIOUS BUY"
        elif sentiment == "NEGATIVE" and gap < 0:
            signal = f"🟡 CAUTIOUS SHORT"
        else:
            signal = f"⚪ MIXED SIGNALS"
            final_score -= 20
        
        if final_score < 40:  # Minimum threshold
            print(f"❌ {symbol}: Score too low ({final_score})")
            return None
        
        print(f"✅ {symbol}: {signal} (Score: {final_score})")
        
        return {
            'symbol': symbol,
            'signal': signal,
            'sentiment': sentiment,
            'direction': direction,
            'gap': gap,
            'price_from': price_data['previous_close'],
            'price_to': price_data['current_price'],
            'confidence': confidence,
            'score': final_score,
            'market_cap': market_cap,
            'llm_reasoning': parsed_analysis.get('reasoning', 'No reasoning provided'),
            'eps_info': parsed_analysis.get('eps', 'N/A'),
            'revenue_info': parsed_analysis.get('revenue', 'N/A')
        }
        
    except Exception as e:
        print(f"❌ Error analyzing {symbol}: {e}")
        return None

def main_llm_earnings_scan():
    """Main LLM-powered earnings scan"""
    print("🤖 LLM EARNINGS ANALYSIS SCAN 🤖")
    print("=" * 60)
    
    uk_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_tz)
    
    print(f"📅 Scan time: {current_time.strftime('%A, %B %d at %H:%M UK')}")
    print(f"🤖 Using AI to analyze earnings sentiment")
    print(f"🎯 Target: >$1B market cap, BMO earnings")
    print(f"⏰ Entry: Market open (2:30 PM UK)")
    print(f"💰 Target: 3-5% profit | Stop: 2% loss")
    
    # Check API keys
    if not OPENAI_API_KEY and not CLAUDE_API_KEY:
        print("❌ No LLM API key configured!")
        print("Set OPENAI_API_KEY or CLAUDE_API_KEY environment variable")
        return
    
    # Get BMO earnings
    bmo_stocks = scrape_nasdaq_bmo_earnings()
    
    if not bmo_stocks:
        msg = "📭 No BMO earnings data available today"
        print(msg)
        send_telegram_message(msg)
        return
    
    print(f"📊 Analyzing {len(bmo_stocks)} BMO stocks with AI...")
    print("-" * 60)
    
    opportunities = []
    processed = 0
    
    # Analyze each stock with LLM
    for symbol in bmo_stocks:
        opportunity = analyze_earnings_opportunity(symbol)
        if opportunity:
            opportunities.append(opportunity)
        
        processed += 1
        print(f"Progress: {processed}/{len(bmo_stocks)}")
        
        # Rate limiting for API calls
        time.sleep(2)  # Be nice to APIs
    
    print("=" * 60)
    
    if opportunities:
        # Sort by combined score and get top 5
        top_5 = sorted(opportunities, key=lambda x: x['score'], reverse=True)[:5]
        
        # Create detailed message
        msg = f"🤖 <b>AI EARNINGS ANALYSIS - TOP 5</b> 🤖\n"
        msg += f"📅 {current_time.strftime('%b %d at %H:%M UK')}\n"
        msg += f"⏰ <b>ENTRY: 2:30 PM UK (Market Open)</b>\n"
        msg += f"🎯 <b>TARGET: 3-5% | STOP: 2%</b>\n\n"
        
        for i, opp in enumerate(top_5, 1):
            market_cap_b = opp['market_cap'] / 1_000_000_000
            msg += f"<b>#{i} {opp['symbol']}</b> (${market_cap_b:.1f}B)\n"
            msg += f"💰 ${opp['price_from']:.2f} → ${opp['price_to']:.2f} ({opp['gap']:+.1f}%)\n"
            msg += f"🤖 <b>{opp['signal']}</b> | AI Score: {opp['score']:.0f}/100\n"
            msg += f"📊 Sentiment: {opp['sentiment']} | Direction: {opp['direction']}\n"
            msg += f"📈 EPS: {opp['eps_info']}\n"
            msg += f"💼 Revenue: {opp['revenue_info']}\n"
            msg += f"🧠 AI: {opp['llm_reasoning'][:100]}...\n\n"
        
        msg += "⚡ <b>EXECUTION:</b>\n"
        msg += "• Enter at 2:30 PM UK sharp\n"
        msg += "• Stop-loss: 2% | Target: 3-5%\n"
        msg += "• Exit within 2-3 minutes\n\n"
        msg += "🚀 AI-powered earnings plays!"
        
        print("🏆 TOP 5 AI-ANALYZED OPPORTUNITIES:")
        for i, opp in enumerate(top_5, 1):
            print(f"#{i} {opp['symbol']}: {opp['signal']} {opp['gap']:+.1f}% (Score: {opp['score']:.0f})")
            print(f"    AI: {opp['sentiment']} sentiment, {opp['direction']} direction")
        
        if send_telegram_message(msg):
            print("✅ AI analysis sent to Telegram!")
        else:
            print("❌ Failed to send Telegram message")
    else:
        msg = f"🤖 AI EARNINGS SCAN COMPLETE\n"
        msg += f"📊 Analyzed {len(bmo_stocks)} BMO stocks\n"
        msg += f"❌ No qualifying opportunities found\n"
        msg += f"🎯 Criteria: >$1B cap, strong AI confidence\n"
        msg += f"💤 Better luck tomorrow!"
        
        print("📭 No qualifying opportunities found")
        send_telegram_message(msg)

def send_startup_message():
    """Send bot startup notification"""
    uk_tz = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_tz)
    
    llm_provider = "OpenAI GPT-4" if OPENAI_API_KEY else "Claude" if CLAUDE_API_KEY else "None"
    
    msg = f"🤖 <b>AI EARNINGS BOT ONLINE</b> 🤖\n"
    msg += f"📅 {current_time.strftime('%A, %B %d at %H:%M UK')}\n\n"
    msg += f"🧠 <b>AI ANALYST:</b> {llm_provider}\n"
    msg += f"📊 <b>STRATEGY:</b>\n"
    msg += f"• AI analyzes earnings sentiment\n"
    msg += f"• Combines with gap analysis\n"
    msg += f"• Target: >$1B cap BMO stocks\n"
    msg += f"• Entry: 2:30 PM UK\n"
    msg += f"• Profit: 3-5% | Stop: 2%\n\n"
    msg += f"⏰ Daily scans at 2:15 PM UK\n"
    
    if not OPENAI_API_KEY and not CLAUDE_API_KEY:
        msg += f"⚠️ No AI API key configured!\n"
    
    msg += f"✅ Ready for AI-powered trading!"
    
    send_telegram_message(msg)

if __name__ == "__main__":
    print("🤖 AI EARNINGS SCALPING BOT v3.0")
    print("🧠 LLM-powered earnings analysis")
    print("📊 Sentiment + Gap combination")
    print("⚡ 2-3 minute scalping strategy")
    
    # Send startup notification
    send_startup_message()
    
    # Schedule daily scan at 2:15 PM UK
    schedule.every().day.at("14:15").do(main_llm_earnings_scan)
    
    print("📅 Scheduled for 2:15 PM UK daily")
    print("🔄 Running initial test scan...")
    
    # Run test scan immediately
    main_llm_earnings_scan()
    
    print("\n⏳ AI bot running... waiting for next scan")
    
    # Keep the bot running
    while True:
        schedule.run_pending()
        time.sleep(60)
