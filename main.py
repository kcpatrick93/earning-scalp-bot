import requests
import time
import os
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

def test_nasdaq_scraping_detailed():
    """Test NASDAQ scraping with detailed debugging"""
    print("🔍 TESTING NASDAQ EARNINGS SCRAPING")
    print("=" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    scraped_stocks = []
    
    # Test scraping pages 1-3
    for page in range(1, 4):
        print(f"\n📄 TESTING PAGE {page}")
        print("-" * 30)
        
        try:
            url = f"https://www.nasdaq.com/market-activity/earnings?page={page}"
            print(f"🌐 URL: {url}")
            
            response = requests.get(url, headers=headers, timeout=20)
            print(f"📊 Response Status: {response.status_code}")
            print(f"📊 Response Size: {len(response.content)} bytes")
            
            if response.status_code != 200:
                print(f"❌ Page {page} failed with status {response.status_code}")
                continue
            
            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: What's on the page?
            page_text = soup.get_text().lower()
            print(f"📝 Page contains 'earnings': {'YES' if 'earnings' in page_text else 'NO'}")
            print(f"📝 Page contains 'market cap': {'YES' if 'market cap' in page_text else 'NO'}")
            
            # Method 1: Look for tables
            tables = soup.find_all('table')
            print(f"📊 Found {len(tables)} tables on page {page}")
            
            page_stocks = []
            
            for table_idx, table in enumerate(tables):
                print(f"  📋 Table {table_idx + 1}:")
                
                rows = table.find_all('tr')
                print(f"    - {len(rows)} rows")
                
                for row_idx, row in enumerate(rows[1:6]):  # Check first 5 data rows
                    cells = row.find_all(['td', 'th'])
                    print(f"    - Row {row_idx + 1}: {len(cells)} cells")
                    
                    if len(cells) >= 3:
                        # Extract cell contents
                        cell_contents = []
                        for cell in cells[:6]:  # First 6 cells
                            text = cell.get_text(strip=True)
                            cell_contents.append(text[:30])  # First 30 chars
                        
                        print(f"      Cells: {cell_contents}")
                        
                        # Look for stock symbols (2-5 uppercase letters)
                        for cell_text in cell_contents:
                            # Clean and check for symbols
                            clean_text = re.sub(r'[^A-Z]', '', cell_text.upper())
                            if len(clean_text) >= 2 and len(clean_text) <= 5 and clean_text.isalpha():
                                # Additional validation - common stock patterns
                                if not clean_text in ['TIME', 'SYMBOL', 'COMPANY', 'NAME', 'CAP', 'MARKET']:
                                    page_stocks.append({
                                        'symbol': clean_text,
                                        'raw_text': cell_text,
                                        'table': table_idx + 1,
                                        'row': row_idx + 1
                                    })
                                    print(f"      ✅ Found symbol: {clean_text}")
            
            # Method 2: Look for specific patterns in text
            print(f"🔍 Text pattern search on page {page}:")
            
            # Look for symbol patterns in the raw text
            symbol_pattern = r'\b[A-Z]{2,5}\b'
            symbols_in_text = re.findall(symbol_pattern, page_text.upper())
            
            # Filter out common words
            filtered_symbols = []
            common_words = {'THE', 'AND', 'FOR', 'YOU', 'ARE', 'WITH', 'THIS', 'THAT', 'FROM', 'HAVE', 'MORE', 'WILL', 'TIME', 'ABOUT', 'OUT', 'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'BUT', 'NOT', 'WHAT', 'ALL', 'WERE', 'WHEN', 'THERE', 'BEEN', 'EACH', 'WHICH', 'THEIR', 'SAID', 'HIM', 'SHE', 'HAS', 'HIS'}
            
            for symbol in symbols_in_text:
                if symbol not in common_words and len(symbol) <= 5:
                    filtered_symbols.append(symbol)
            
            unique_text_symbols = list(set(filtered_symbols))[:10]  # First 10 unique
            print(f"  Found in text: {unique_text_symbols}")
            
            # Combine results
            if page_stocks:
                scraped_stocks.extend(page_stocks)
                print(f"✅ Page {page}: Found {len(page_stocks)} potential stocks")
            else:
                print(f"❌ Page {page}: No stocks found")
            
            # Rate limiting
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Error scraping page {page}: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("📊 SCRAPING RESULTS SUMMARY")
    print("=" * 60)
    
    if scraped_stocks:
        # Remove duplicates
        unique_symbols = {}
        for stock in scraped_stocks:
            symbol = stock['symbol']
            if symbol not in unique_symbols:
                unique_symbols[symbol] = stock
        
        final_stocks = list(unique_symbols.values())
        
        print(f"✅ TOTAL FOUND: {len(final_stocks)} unique stock symbols")
        print("\n📋 SCRAPED STOCKS:")
        
        for i, stock in enumerate(final_stocks[:15], 1):  # Show first 15
            print(f"{i:2d}. {stock['symbol']} (from table {stock['table']}, row {stock['row']})")
        
        # Create success message
        symbol_list = [stock['symbol'] for stock in final_stocks[:10]]
        
        msg = f"✅ <b>NASDAQ SCRAPING TEST SUCCESS!</b>\n\n"
        msg += f"🔍 <b>Scraped 3 pages of NASDAQ earnings</b>\n"
        msg += f"📊 Found {len(final_stocks)} unique stocks\n\n"
        msg += f"<b>Sample stocks found:</b>\n"
        
        for i, symbol in enumerate(symbol_list, 1):
            msg += f"{i}. {symbol}\n"
        
        if len(final_stocks) > 10:
            msg += f"... and {len(final_stocks) - 10} more\n"
        
        msg += f"\n🚀 <b>SCRAPING SYSTEM WORKS!</b>\n"
        msg += f"✅ Can get real earnings data daily\n"
        msg += f"✅ Ready for full automation"
        
        print(f"\n📱 Sending results to Telegram...")
        if send_telegram_message(msg):
            print("✅ SUCCESS! Scraping results sent to Telegram!")
        else:
            print("❌ Telegram send failed, but scraping worked!")
        
        return final_stocks
        
    else:
        print("❌ NO STOCKS FOUND!")
        print("\nDEBUG INFO:")
        print("- Check if NASDAQ changed their website structure")
        print("- Try different scraping approach")
        print("- May need to use different earnings source")
        
        msg = f"❌ <b>NASDAQ SCRAPING TEST FAILED</b>\n\n"
        msg += f"🔍 Attempted to scrape 3 pages\n"
        msg += f"📊 Found 0 stock symbols\n\n"
        msg += f"🔧 <b>ISSUE:</b>\n"
        msg += f"• NASDAQ may have changed structure\n"
        msg += f"• Need alternative scraping method\n"
        msg += f"• May need different data source\n\n"
        msg += f"💡 Will try backup scraping methods"
        
        send_telegram_message(msg)
        return []

def test_alternative_sources():
    """Test alternative earnings sources if NASDAQ fails"""
    print("\n🔄 TESTING ALTERNATIVE EARNINGS SOURCES")
    print("=" * 50)
    
    alternative_stocks = []
    
    # Method 1: Try Yahoo Finance earnings calendar
    try:
        print("📰 Testing Yahoo Finance earnings calendar...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        yahoo_url = "https://finance.yahoo.com/calendar/earnings"
        response = requests.get(yahoo_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for stock symbols in Yahoo earnings
            tables = soup.find_all('table')
            
            for table in tables[:2]:  # Check first 2 tables
                rows = table.find_all('tr')
                for row in rows[1:10]:  # First 10 rows
                    cells = row.find_all(['td', 'th'])
                    for cell in cells[:3]:  # First 3 cells
                        text = cell.get_text(strip=True)
                        # Look for symbol pattern
                        if len(text) >= 2 and len(text) <= 5 and text.isupper():
                            alternative_stocks.append(text)
            
            print(f"✅ Yahoo Finance: Found {len(set(alternative_stocks))} symbols")
        
    except Exception as e:
        print(f"❌ Yahoo Finance failed: {e}")
    
    # Method 2: Try Investing.com earnings
    try:
        print("📊 Testing Investing.com earnings calendar...")
        
        investing_url = "https://www.investing.com/earnings-calendar/"
        response = requests.get(investing_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            print("✅ Investing.com accessible")
            # Could add more parsing here
        
    except Exception as e:
        print(f"❌ Investing.com failed: {e}")
    
    if alternative_stocks:
        unique_alt = list(set(alternative_stocks))[:10]
        print(f"📊 Alternative sources found: {unique_alt}")
        return unique_alt
    
    return []

if __name__ == "__main__":
    print("🧪 NASDAQ SCRAPING TEST - REAL DATA ONLY")
    print("🎯 Testing if bot can get actual earnings from NASDAQ")
    print("⚠️  No hardcoded data - pure scraping test")
    print()
    
    # Test NASDAQ scraping
    scraped_stocks = test_nasdaq_scraping_detailed()
    
    if not scraped_stocks:
        # Try alternative sources
        alternative_stocks = test_alternative_sources()
        
        if alternative_stocks:
            print("✅ Backup sources found stocks!")
        else:
            print("❌ All scraping methods failed")
    
    print(f"\n⏰ Scraping test completed: {datetime.now().strftime('%H:%M:%S')}")
    print("🎯 This tests the core automation capability!")
