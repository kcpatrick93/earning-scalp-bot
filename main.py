# Alternative data sources to replace Yahoo Finance

import requests
import time

def get_finnhub_data(symbol):
    """Use Finnhub API - more reliable than Yahoo"""
    try:
        # Free tier: 60 calls/minute
        api_key = "d1ehal1r01qjssrk4fu0d1ehal1r01qjssrk4fug"  # Demo key
        
        # Get quote data
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current_price = data.get('c', 0)
            previous_close = data.get('pc', 0)
            
            if current_price and previous_close:
                gap_percent = ((current_price - previous_close) / previous_close) * 100
                return {
                    'current_price': current_price,
                    'previous_close': previous_close,
                    'gap_percent': gap_percent
                }
        return None
    except Exception as e:
        print(f"Finnhub error: {e}")
        return None

def get_alpha_vantage_data(symbol):
    """Use Alpha Vantage - 25 free calls/day"""
    try:
        api_key = "demo"  # Get real key from alphavantage.co
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            quote = data.get("Global Quote", {})
            
            current_price = float(quote.get("05. price", 0))
            previous_close = float(quote.get("08. previous close", 0))
            
            if current_price and previous_close:
                gap_percent = ((current_price - previous_close) / previous_close) * 100
                return {
                    'current_price': current_price,
                    'previous_close': previous_close,
                    'gap_percent': gap_percent
                }
        return None
    except Exception as e:
        print(f"Alpha Vantage error: {e}")
        return None

def get_polygon_data(symbol):
    """Use Polygon.io - 5 free calls/minute"""
    try:
        api_key = "your_polygon_key"  # Get from polygon.io
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apikey={api_key}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                previous_close = result.get("c", 0)
                
                # Get current price from another endpoint
                current_url = f"https://api.polygon.io/v1/last/stocks/{symbol}?apikey={api_key}"
                current_response = requests.get(current_url, timeout=10)
                
                if current_response.status_code == 200:
                    current_data = current_response.json()
                    current_price = current_data.get("last", {}).get("price", 0)
                    
                    if current_price and previous_close:
                        gap_percent = ((current_price - previous_close) / previous_close) * 100
                        return {
                            'current_price': current_price,
                            'previous_close': previous_close,
                            'gap_percent': gap_percent
                        }
        return None
    except Exception as e:
        print(f"Polygon error: {e}")
        return None

def get_market_data_robust(symbol):
    """Try multiple sources in order of preference"""
    print(f"Getting data for {symbol}...")
    
    # Try Finnhub first (most reliable free option)
    data = get_finnhub_data(symbol)
    if data:
        print(f"✅ {symbol}: Got data from Finnhub")
        return data
    
    time.sleep(1)  # Rate limiting
    
    # Try Alpha Vantage
    data = get_alpha_vantage_data(symbol)
    if data:
        print(f"✅ {symbol}: Got data from Alpha Vantage")
        return data
    
    time.sleep(1)
    
    # Try Polygon (if you have key)
    data = get_polygon_data(symbol)
    if data:
        print(f"✅ {symbol}: Got data from Polygon")
        return data
    
    print(f"❌ {symbol}: All data sources failed")
    return None

# Hardcoded market caps to avoid Yahoo Finance completely
MARKET_CAPS = {
    'PG': 392_000_000_000,   # Procter & Gamble
    'UNH': 255_000_000_000,  # UnitedHealth
    'BA': 138_000_000_000,   # Boeing
    'MRK': 320_000_000_000,  # Merck
    'SPOT': 52_000_000_000,  # Spotify
    # Add more as needed
}

def get_market_cap_fallback(symbol):
    """Get market cap from hardcoded values"""
    return MARKET_CAPS.get(symbol, 0)
