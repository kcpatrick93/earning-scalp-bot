import requests
import time
import os
import re
import openai
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
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
    """Scrape real earnings data using proven working method"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nasdaq.com/market-activity/earnings',
        'Origin': 'https://www.nasdaq.com'
    }
    earnings_stocks = []
    # Method 1: NASDAQ API
    nasdaq_endpoints = [
        "https://api.nasdaq.com/api/calendar/earnings",
        "https://www.nasdaq.com/api/calendar/earnings"
    ]
    for endpoint in nasdaq_endpoints:
        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for val in data.values():
                    if isinstance(val, list):
                        for item in val[:50]:
                            if isinstance(item, dict):
                                sym = next((item.get(f) for f in ['symbol','ticker','Symbol','Ticker'] if item.get(f)), None)
                                if sym and sym.isalpha() and len(sym)<=5:
                                    earnings_stocks.append({'symbol': sym.upper(), 'source': 'NASDAQ_API'})
                break
        except:
            continue

    # Method 2: Yahoo Finance backup
    if len(earnings_stocks) < 5:
        try:
            yahoo_url = "https://finance.yahoo.com/calendar/earnings"
            r = requests.get(yahoo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if r.status_code == 200:
                matches = re.findall(r'"symbol":"([A-Z]{1,5})"', r.text)
                for sym in matches[:20]:
                    if sym not in [s['symbol'] for s in earnings_stocks]:
                        earnings_stocks.append({'symbol': sym, 'source': 'YAHOO_FINANCE'})
        except:
            pass

    # Dedupe
    unique = {s['symbol']: s for s in earnings_stocks}
    return list(unique.values())


def filter_stocks_by_market_cap(earnings_stocks):
    """Filter stocks by market cap (>$10B)"""
    market_caps = {
        'MSFT':3809,'META':1804,'AAPL':3500,'GOOGL':2100,'AMZN':1800,
        'NVDA':3000,'TSLA':800,'QCOM':177,'ARM':174,'LRCX':126,
        'ADP':125,'HOOD':94,'F':45,'CVNA':72,'ALL':51,
        'RBLX':30,'FCX':60,'ALGN':15,'AVGO':700,'RDDT':25,
        'NFLX':200,'AMD':240,'INTC':180,'CRM':200,'ORCL':450,
        'UBER':120,'PYPL':60
    }
    qualified = []
    for s in earnings_stocks:
        cap_b = market_caps.get(s['symbol'], 0)
        if cap_b >= 10:
            qualified.append({'symbol':s['symbol'], 'market_cap': cap_b*1_000_000_000, 'source': s['source']})
    return qualified


def get_stock_price_data(symbol):
    """Get real price data from Finnhub"""
    try:
        key = os.getenv("FINNHUB_API_KEY") or "d1ehal1r01qjssrk4fu0d1ehal1r01qjssrk4fug"
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={key}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            c, pc = d.get('c'), d.get('pc')
            if c and pc:
                gap = ((c-pc)/pc)*100
                return {'current_price':c, 'previous_close':pc, 'gap_percent':gap}
    except:
        pass
    return None


def ai_analyze_earnings(symbol, price_data):
    """AI analysis of earnings"""
    if not OPENAI_API_KEY:
        return None
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
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are a day trader analyzing earnings for scalping. Be decisive about direction."},
                {"role":"user","content":prompt}
            ],
            max_tokens=200,
            temperature=0.1
        )
        return resp.choices[0].message.content
    except:
        return None


def parse_ai_analysis(ai_text):
    """Parse AI response into dict"""
    if not ai_text: return None
    parsed={} 
    for line in ai_text.splitlines():
        if ':' in line:
            k,v = line.split(':',1)
            k,v=k.strip().upper(),v.strip()
            if k=='RESULT': parsed['result']=v
            if k=='SENTIMENT': parsed['sentiment']=v
            if k=='DIRECTION': parsed['direction']=v
            if k=='CONFIDENCE':
                try: parsed['confidence']=int(v.split()[0])
                except: parsed['confidence']=5
            if k=='REASONING': parsed['reasoning']=v
    return parsed


def calculate_trading_score(confidence, sentiment, direction, gap):
    """Scoring algorithm"""
    base = confidence*7
    if abs(gap)<0.5: return 0
    elif abs(gap)<1.0: base-=15
    elif abs(gap)>=1.5: base+=20
    elif abs(gap)>4.0: base-=15
    gap_dir = 'UP' if gap>0 else 'DOWN'
    if gap_dir==direction: base+=25
    else: base-=30
    if sentiment=='POSITIVE' and direction=='UP': base+=15
    elif sentiment=='NEGATIVE' and direction=='DOWN': base+=15
    elif sentiment=='NEUTRAL': base-=10
    else: base-=20
    return max(0, min(100, base))


def generate_trading_signal(sentiment, direction, gap, score):
    """Signal generation"""
    if score<65: return None
    if sentiment=='POSITIVE' and direction=='UP' and gap>1.0: return "🚀 STRONG BUY"
    if sentiment=='POSITIVE' and direction=='UP' and gap>0.5: return "🟢 BUY"
    if sentiment=='NEGATIVE' and direction=='DOWN' and gap<-1.0: return "📉 STRONG SHORT"
    if sentiment=='NEGATIVE' and direction=='DOWN' and gap<-0.5: return "🔴 SHORT"
    return None


def run_corrected_analysis():
    """Run complete corrected analysis"""
    print("🚨 CORRECTED EARNINGS ANALYSIS")
    earnings = scrape_real_earnings_data()
    if not earnings:
        send_telegram_message("❌ Failed to scrape earnings data")
        return
    qualified = filter_stocks_by_market_cap(earnings)
    if not qualified:
        send_telegram_message("📭 No stocks meet market cap criteria")
        return
    opportunities=[]
    for stock in qualified[:15]:
        sym=stock['symbol']
        pd = get_stock_price_data(sym)
        if not pd or abs(pd['gap_percent'])<0.5: continue
        ai_txt=ai_analyze_earnings(sym,pd)
        parsed=parse_ai_analysis(ai_txt)
        if not parsed: continue
        score=calculate_trading_score(parsed['confidence'], parsed['sentiment'], parsed['direction'], pd['gap_percent'])
        signal=generate_trading_signal(parsed['sentiment'], parsed['direction'], pd['gap_percent'], score)
        if signal:
            opportunities.append({
                'symbol':sym,'signal':signal,'sentiment':parsed['sentiment'],
                'direction':parsed['direction'],'gap':pd['gap_percent'],
                'price_from':pd['previous_close'],'price_to':pd['current_price'],
                'confidence':parsed['confidence'],'score':score,
                'market_cap':stock['market_cap'],'reasoning':parsed.get('reasoning','')
            })
        time.sleep(2)
    top = sorted(opportunities, key=lambda x: x['score'], reverse=True)[:5]
    if top:
        msg = f"🤖 <b>CLEAR TRADING OPPORTUNITIES</b>\n\n"
        msg += f"📅 {datetime.now().strftime('%b %d at %H:%M')}\n"
        msg += f"✅ Found {len(top)} clear signals:\n\n"
        for i,opp in enumerate(top,1):
            cap_b = opp['market_cap']/1_000_000_000
            msg += f"<b>#{i} {opp['symbol']}</b> (${cap_b:.0f}B)\n"
            msg += f"💰 ${opp['price_from']:.2f} → ${opp['price_to']:.2f} ({opp['gap']:+.1f}%)\n"
            msg += f"🎯 <b>{opp['signal']}</b>\n"
            msg += f"📊 Score: {opp['score']}/100\n"
            msg += f"🤖 AI: {opp['sentiment']} sentiment, {opp['confidence']}/10 confidence\n"
            msg += f"💡 {opp['reasoning'][:60]}...\n\n"
        msg += "⚡ <b>STRATEGY:</b>\n• Entry: Current price\n• Target: 3-5% profit\n• Stop: 2% loss\n• Time: 2-3 minutes\n\n🔥 Only high-confidence trades!"
        send_telegram_message(msg)
    else:
        msg = f"📭 <b>NO CLEAR OPPORTUNITIES TODAY</b>\n\n"
        msg += f"🔍 Analyzed {len(qualified)} qualified stocks\n❌ None met strict criteria\n"
        msg += "💤 Better opportunities tomorrow!"
        send_telegram_message(msg)


def scheduled_job():
    print(f"⏰ Running analysis at {datetime.now()}")
    run_corrected_analysis()

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Europe/London")
    trigger = CronTrigger(day_of_week='mon-fri', hour=14, minute=10)
    scheduler.add_job(scheduled_job, trigger, id="earnings_analysis")
    print("🔧 Scheduler started – runs Mon–Fri at 14:10 London time")
    scheduler.start()
