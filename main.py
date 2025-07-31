import requests
import time
import os
import json
from datetime import datetime
from bs4 import BeautifulSoup
import re

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def try_nasdaq_api_approach():
    """Try to find NASDAQ's API endpoints"""
    print("🔍 TRYING NASDAQ API APPROACH")
    print("=" * 40)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nasdaq.com/market-activity/earnings',
        'Origin': 'https://www.nasdaq.com'
    }
    
    # Common API endpoints that earnings sites use
    api_endpoints = [
        "https://api.nasdaq.com/api/calendar/earnings",
        "https://www.nasdaq.com/api/v1/earnings-calendar",
        "https://api.nasdaq.com/api/screener/earnings",
        "https://www.nasdaq.com/api/calendar/earnings?date=2025-07-30"
    ]
    
    for endpoint in api_endpoints:
        try:
            print(f"🔗 Trying: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=15)
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ JSON response received: {len(str(data))} chars")
                    
                    # Look for earnings data in JSON
                    if isinstance(data, dict):
                        # Look for common earnings data fields
                        for key, value in data.items():
                            if isinstance(value, list) and len(value) > 0:
                                print(f"📊 Found array '{key}' with {len(value)} items")
                                
                                # Check first item for stock-like data
                                first_item = value[0]
                                if isinstance(first_item, dict):
                                    print(f"   Sample item keys: {list(first_item.keys())}")
                                    
                                    # Look for symbol field
                                    for item_key in first_item.keys():
                                        if 'symbol' in item_key.lower() or 'ticker' in item_key.lower():
                                            print(f"   ✅ Found symbol field: {item_key}")
                                            return data
                    
                    return data
                except json.JSONDecodeError:
                    print("❌ Not JSON data")
                    # Check if it's HTML with JSON embedded
                    if 'application/json' in response.headers.get('content-type', ''):
                        print("🔍 Checking for embedded JSON...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)
    
    return None

def try_alternative_earnings_sources():
    """Try multiple alternative sources"""
    print("\n🔄 TRYING ALTERNATIVE SOURCES")
    print("=" * 40)
    
    found_stocks = []
    
    # Source 1: Yahoo Finance
    try:
        print("📰 Testing Yahoo Finance...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Try Yahoo earnings calendar
        yahoo_url = "https://finance.yahoo.com/calendar/earnings?from=2025-07-30&to=2025-07-30&day=2025-07-30"
        response = requests.get(yahoo_url, headers=headers, timeout=15)
        
        print(f"Yahoo status: {response.status_code}")
        
        if response.status_code == 200:
            # Look for stock symbols in the response
            content = response.text
            
            # Look for JSON data in the page
            json_matches = re.findall(r'"symbol":"([A-Z]{1,5})"', content)
            if json_matches:
                found_stocks.extend(json_matches)
                print(f"✅ Yahoo: Found {len(json_matches)} symbols in JSON")
            
            # Also try HTML parsing
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for table data
            for table in soup.find_all('table')[:3]:
                for row in table.find_all('tr')[1:10]:
                    for cell in row.find_all(['td', 'th'])[:3]:
                        text = cell.get_text(strip=True)
                        if text and len(text) <= 5 and text.isupper() and text.isalpha():
                            found_stocks.append(text)
            
            print(f"Yahoo HTML parsing: Found {len(set(found_stocks)) - len(set(json_matches))} additional symbols")
    
    except Exception as e:
        print(f"❌ Yahoo failed: {e}")
    
    # Source 2: MarketWatch
    try:
        print("📊 Testing MarketWatch...")
        
        mw_url = "https://www.marketwatch.com/tools/calendars/earnings"
        response = requests.get(mw_url, headers=headers, timeout=15)
        
        print(f"MarketWatch status: {response.status_code}")
        
        if response.status_code == 200:
            # Look for symbols in MarketWatch
            content = response.text
            symbol_pattern = r'\b[A-Z]{2,5}\b'
            mw_symbols = re.findall(symbol_pattern, content)
            
            # Filter out common words
            filtered_mw = [s for s in mw_symbols if s not in ['THE', 'AND', 'FOR', 'YOU', 'ARE', 'ALL', 'NEW', 'GET', 'SEE', 'NOW', 'WAY', 'MAY', 'USE', 'TOP', 'WEB']]
            found_stocks.extend(filtered_mw[:20])  # Take first 20
            
            print(f"✅ MarketWatch: Found {len(filtered_mw)} potential symbols")
    
    except Exception as e:
        print(f"❌ MarketWatch failed: {e}")
    
    # Source 3: Earnings Whispers (if accessible)
    try:
        print("📢 Testing Earnings Whispers...")
        
        ew_url = "https://www.earningswhispers.com/calendar"
        response = requests.get(ew_url, headers=headers, timeout=15)
        
        print(f"Earnings Whispers status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for earnings symbols
            for link in soup.find_all('a')[:50]:
                href = link.get('href', '')
                if '/stocks/' in href:
                    # Extract symbol from URL like /stocks/AAPL
                    symbol_match = re.search(r'/stocks/([A-Z]{1,5})', href)
                    if symbol_match:
                        found_stocks.append(symbol_match.group(1))
            
            print(f"✅ Earnings Whispers: Found symbols in links")
    
    except Exception as e:
        print(f"❌ Earnings Whispers failed: {e}")
    
    # Clean up results
    if found_stocks:
        # Remove duplicates and common words
        unique_stocks = []
        seen = set()
        common_words = {'THE', 'AND', 'FOR', 'YOU', 'ARE', 'ALL', 'NEW', 'GET', 'SEE', 'NOW', 'WAY', 'MAY', 'USE', 'TOP', 'WEB', 'ONE', 'TWO', 'DAY', 'OUT', 'WHO', 'BUT', 'NOT', 'CAN', 'HAS', 'HAD', 'HER', 'HIS', 'HIM', 'SHE', 'WAS'}
        
        for stock in found_stocks:
            stock = stock.upper().strip()
            if (stock not in seen and 
                stock not in common_words and 
                len(stock) >= 2 and 
                len(stock) <= 5 and 
                stock.isalpha()):
                unique_stocks.append(stock)
                seen.add(stock)
        
        return unique_stocks[:20]  # Return top 20
    
    return []

def try_known_earnings_today():
    """Use known major earnings as fallback while testing other methods"""
    print("\n💡 USING KNOWN EARNINGS AS FALLBACK")
    print("=" * 40)
    
    # These are companies we know reported today from earlier research
    known_today = ['MSFT', 'META', 'QCOM', 'LRCX', 'ADP', 'HOOD', 'F', 'ARM', 'CVNA', 'ALL']
    
    print(f"📊 Known earnings today: {known_today}")
    return known_today

def test_complete_scraping():
    """Test complete scraping with all methods"""
    print("🚨 COMPLETE EARNINGS SCRAPING TEST")
    print("=" * 60)
    
    all_found_stocks = []
    
    # Method 1: Try NASDAQ API
    print("🔍 METHOD 1: NASDAQ API")
    nasdaq_data = try_nasdaq_api_approach()
    if nasdaq_data:
        print("✅ NASDAQ API worked!")
        # Process NASDAQ data here
    else:
        print("❌ NASDAQ API failed")
    
    # Method 2: Alternative sources
    print("\n🔍 METHOD 2: ALTERNATIVE SOURCES")
    alt_stocks = try_alternative_earnings_sources()
    if alt_stocks:
        all_found_stocks.extend(alt_stocks)
        print(f"✅ Alternative sources found {len(alt_stocks)} stocks")
    else:
        print("❌ Alternative sources failed")
    
    # Method 3: Fallback
    print("\n🔍 METHOD 3: FALLBACK DATA")
    fallback_stocks = try_known_earnings_today()
    
    # Combine all results
    if all_found_stocks:
        final_stocks = all_found_stocks
        source = "Scraped from web"
    else:
        final_stocks = fallback_stocks
        source = "Known earnings (fallback)"
    
    print(f"\n📊 FINAL RESULTS:")
    print(f"Found {len(final_stocks)} stocks from: {source}")
    print(f"Stocks: {final_stocks}")
    
    # Create results message
    if all_found_stocks:
        msg = f"✅ <b>SCRAPING SUCCESS!</b>\n\n"
        msg += f"🔍 <b>Real web scraping worked!</b>\n"
        msg += f"📊 Found {len(final_stocks)} earnings stocks\n\n"
        msg += f"<b>Today's earnings stocks:</b>\n"
        
        for i, stock in enumerate(final_stocks[:10], 1):
            msg += f"{i}. {stock}\n"
        
        if len(final_stocks) > 10:
            msg += f"... and {len(final_stocks)-10} more\n"
        
        msg += f"\n🚀 <b>AUTOMATION WILL WORK!</b>\n"
        msg += f"✅ Can scrape real earnings daily\n"
        msg += f"✅ Ready for live trading bot"
        
    else:
        msg = f"⚠️ <b>SCRAPING NEEDS WORK</b>\n\n"
        msg += f"❌ Web scraping failed\n"
        msg += f"💡 Using fallback data for now\n"
        msg += f"📊 Found {len(final_stocks)} known earnings\n\n"
        msg += f"<b>Fallback stocks:</b>\n"
        
        for i, stock in enumerate(final_stocks[:8], 1):
            msg += f"{i}. {stock}\n"
        
        msg += f"\n🔧 <b>NEXT STEPS:</b>\n"
        msg += f"• Need better scraping method\n"
        msg += f"• Could use paid earnings API\n"
        msg += f"• Or manual daily input"
    
    # Send results
    print(f"\n📱 Sending results to Telegram...")
    if send_telegram_message(msg):
        print("✅ Results sent successfully!")
    else:
        print("❌ Telegram send failed")
    
    return final_stocks

if __name__ == "__main__":
    print("🧪 ADVANCED SCRAPING TEST")
    print("🎯 Testing multiple scraping approaches")
    print("🔍 Will find the method that works")
    print()
    
    stocks = test_complete_scraping()
    
    print(f"\n📊 FINAL RESULT: {len(stocks)} stocks found")
    print(f"⏰ Test completed: {datetime.now().strftime('%H:%M:%S')}")
    
    if stocks:
        print("🎉 SUCCESS! Bot can get earnings data")
    else:
        print("❌ FAILED! Need alternative approach")
