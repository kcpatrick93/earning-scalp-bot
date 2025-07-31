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
FINNHUB_API_KEY    = os.getenv("FINNHUB_API_KEY")

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
    """Scrape real earnings data using NASDAQ API (plus Yahoo backup)"""
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nasdaq.com/market-activity/earnings',
        'Origin': 'https://www.nasdaq.com'
    }
    earnings_stocks = []
    # NASDAQ API endpoints
    for endpoint in [
        "https://api.nasdaq.com/api/calendar/earnings",
        "https://www.nasdaq.com/api/calendar/earnings"
    ]:
        try:
            r = requests.get(endpoint, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                for val in data.values():
                    if isinstance(val, list):
                        for item in val[:50]:
                            if isinstance(item, dict):
                                sym = next((item.get(k) for k in ['symbol','ticker','Symbol','Ticker'] if item.get(k)), None)
                                if sym and sym.isalpha() and len(sym)<=5:
                                    earnings_stocks.append({'symbol': sym.upper(), 'source': 'NASDAQ_API'})
                break
        except:
            continue
    # Yahoo Finance fallback
    if len(earnings_stocks) < 5:
        try:
            r = requests.get("https://finance.yahoo.com/calendar/earnings", headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if r.status_code == 200:
                syms = re.findall(r'"symbol":"([A-Z]{1,5})"', r.text)
                for sym in syms[:20]:
                    if sym not in [s['symbol'] for s in earnings_stocks]:
                        earnings_stocks.append({'symbol': sym, 'source': 'YAHOO_FINANCE'})
        except:
            pass
    # Dedupe
    unique = {s['symbol']: s for s in earnings_stocks}
    print(f"🔍 Found {len(unique)} earnings symbols")
    return list(unique.values())


def filter_stocks_by_market_cap(stocks):
    """Keep only stocks > $10B using hardcoded caps"""
    caps = {
        'MSFT':3809,'META':1804,'AAPL':3500,'GOOGL':2100,'AMZN':1800,
        'NVDA':3000,'TSLA':800,'QCOM':177,'ARM':174,'LRCX':126,
        'ADP':125,'HOOD':94,'F':45,'CVNA':72,'ALL':51,
        'RBLX':30,'FCX':60,'ALGN':15,'AVGO':700,'RDDT':25,
        'NFLX':200,'AMD':240,'INTC':180,'CRM':200,'ORCL':450,
        'UBER':120,'PYPL':60
    }
    out=[]
    for s in stocks:
        b = caps.get(s['symbol'],0)
        if b>=10:
            out.append({'symbol':s['symbol'],'market_cap':b*1e9,'source':s['source']})
    print(f"🎯 {len(out)} stocks >$10B")
    return out


def get_stock_price_data(symbol):
    """Fetch quote from Finnhub"""
    key = FINNHUB_API_KEY or "d1ehal1r01qjssrk4fu0d1ehal1r01qjssrk4fug"
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={key}", timeout=10)
        if r.status_code==200:
            d=r.json()
            if d.get('c') and d.get('pc'):
                gap=((d['c']-d['pc'])/d['pc'])*100
                return {'current_price':d['c'],'previous_close':d['pc'],'gap_percent':gap}
    except:
        pass
    return None


def ai_analyze_earnings(symbol, price_data):
    """Call OpenAI for earnings scalp analysis"""
    if not OPENAI_API_KEY: return None
    gap_info = f"Price movement: {price_data['gap_percent']:+.1f}% (${price_data['previous_close']:.2f}→${price_data['current_price']:.2f})"
    prompt = f"""
Analyze {symbol} for day trading based on earnings and price movement.

{gap_info}

Provide EXACT format:
RESULT: BEAT/MISS/INLINE
SENTIMENT: POSITIVE/NEGATIVE/NEUTRAL
DIRECTION: UP/DOWN
CONFIDENCE: [1-10]
REASONING: [brief]
"""
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":"You are a day trader analyzing earnings for scalping."},
                      {"role":"user","content":prompt}],
            max_tokens=200, temperature=0.1
        )
        return resp.choices[0].message.content
    except:
        return None


def parse_ai_analysis(text):
    """Turn AI reply into structured dict"""
    if not text: return None
    res={}
    for ln in text.splitlines():
        if ':' in ln:
            k,v=ln.split(':',1)
            k=k.strip().upper(); v=v.strip()
            if k=='RESULT': res['result']=v
            if k=='SENTIMENT': res['sentiment']=v
            if k=='DIRECTION': res['direction']=v
            if k=='CONFIDENCE':
                try: res['confidence']=int(v.split()[0])
                except: res['confidence']=5
            if k=='REASONING': res['reasoning']=v
    return res


def calculate_trading_score(conf, sent, dirn, gap):
    base=conf*7
    if abs(gap)<0.5: return 0
    if abs(gap)<1: base-=15
    elif gap>=1.5: base+=20
    elif abs(gap)>4: base-=15
    gap_dir='UP' if gap>0 else 'DOWN'
    base += 25 if gap_dir==dirn else -30
    if sent=='POSITIVE' and dirn=='UP': base+=15
    elif sent=='NEGATIVE' and dirn=='DOWN': base+=15
    elif sent=='NEUTRAL': base-=10
    else: base-=20
    return max(0,min(100,base))


def generate_trading_signal(sent, dirn, gap, score):
    if score<65: return None
    if sent=='POSITIVE' and dirn=='UP' and gap>1: return "🚀 STRONG BUY"
    if sent=='POSITIVE' and dirn=='UP' and gap>0.5: return "🟢 BUY"
    if sent=='NEGATIVE' and dirn=='DOWN' and gap<-1: return "📉 STRONG SHORT"
    if sent=='NEGATIVE' and dirn=='DOWN' and gap<-0.5: return "🔴 SHORT"
    return None


def run_corrected_analysis():
    print("🚨 CORRECTED EARNINGS ANALYSIS")
    earnings = scrape_real_earnings_data()
    if not earnings:
        return send_telegram_message("❌ Failed to scrape earnings data")
    qualified = filter_stocks_by_market_cap(earnings)
    if not qualified:
        return send_telegram_message("📭 No stocks meet market cap criteria")
    ops=[]
    for s in qualified[:15]:
        pd = get_stock_price_data(s['symbol'])
        if not pd or abs(pd['gap_percent'])<0.5: continue
        ai_txt = ai_analyze_earnings(s['symbol'], pd)
        parsed = parse_ai_analysis(ai_txt)
        if not parsed: continue
        score = calculate_trading_score(parsed['confidence'], parsed['sentiment'], parsed['direction'], pd['gap_percent'])
        sig = generate_trading_signal(parsed['sentiment'], parsed['direction'], pd['gap_percent'], score)
        if sig:
            ops.append({
                'symbol':s['symbol'],'signal':sig,'sentiment':parsed['sentiment'],
                'direction':parsed['direction'],'gap':pd['gap_percent'],
                'price_from':pd['previous_close'],'price_to':pd['current_price'],
                'confidence':parsed['confidence'],'score':score,
                'market_cap':s['market_cap'],'reasoning':parsed.get('reasoning','')
            })
        time.sleep(2)
    top = sorted(ops, key=lambda x: x['score'], reverse=True)[:5]
    if top:
        msg = f"🤖 <b>CLEAR TRADING OPPORTUNITIES</b>\n\n"
        msg += f"📅 {datetime.now().strftime('%b %d at %H:%M')}\n"
        msg += f"✅ Found {len(top)} clear signals:\n\n"
        for i,o in enumerate(top,1):
            cap_b = o['market_cap']/1e9
            msg += f"<b>#{i} {o['symbol']}</b> (${cap_b:.0f}B)\n"
            msg += f"💰 ${o['price_from']:.2f}→${o['price_to']:.2f} ({o['gap']:+.1f}%)\n"
            msg += f"🎯 <b>{o['signal']}</b>\n"
            msg += f"📊 Score: {o['score']}/100\n"
            msg += f"🤖 AI: {o['sentiment']} sentiment, {o['confidence']}/10 confidence\n"
            msg += f"💡 {o['reasoning'][:60]}...\n\n"
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
    # One-off run for smoke test
    scheduled_job()

    # Scheduler for daily runs at 14:10 London time
    scheduler = BlockingScheduler()
    trigger = CronTrigger(day_of_week='mon-fri', hour=14, minute=10, timezone='Europe/London')
    scheduler.add_job(scheduled_job, trigger, id="earnings_analysis")
    print("🔧 Scheduler started – runs Mon–Fri at 14:10 London time")
    scheduler.start()
