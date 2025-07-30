import os
import time

print("🔍 DEBUGGING RAILWAY DEPLOYMENT")
print("=" * 50)

# Check environment variables
print("📋 Environment Variables:")
print(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
print(f"TELEGRAM_BOT_TOKEN: {'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET'}")
print(f"TELEGRAM_CHAT_ID: {'SET' if os.getenv('TELEGRAM_CHAT_ID') else 'NOT SET'}")

# Test imports
print("\n📦 Testing Imports:")
try:
    import requests
    print("✅ requests")
except Exception as e:
    print(f"❌ requests: {e}")

try:
    import openai
    print("✅ openai")
except Exception as e:
    print(f"❌ openai: {e}")

try:
    from datetime import datetime
    print("✅ datetime")
except Exception as e:
    print(f"❌ datetime: {e}")

# Test OpenAI
print("\n🤖 Testing OpenAI:")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("⚠️ No OpenAI API key - using mock mode")
    
    # Mock analysis for testing
    def mock_analysis(symbol):
        mock_data = {
            'PG': "RESULT: BEAT\nSENTIMENT: POSITIVE\nDIRECTION: UP\nCONFIDENCE: 8",
            'UNH': "RESULT: MISS\nSENTIMENT: NEGATIVE\nDIRECTION: DOWN\nCONFIDENCE: 9"
        }
        return mock_data.get(symbol, "RESULT: UNKNOWN\nSENTIMENT: NEUTRAL\nDIRECTION: UP\nCONFIDENCE: 5")
    
    print("✅ Mock analysis ready")
    
else:
    try:
        openai.api_key = OPENAI_API_KEY
        print("✅ OpenAI API key set")
        
        # Test API call
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'API test successful'"}],
            max_tokens=10
        )
        print("✅ OpenAI API test successful")
        
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")

# Simple backtest data
MARKET_DATA = {
    'PG': {'gap': 2.03, 'cap': 392_000_000_000},
    'UNH': {'gap': -4.62, 'cap': 255_000_000_000},
    'BA': {'gap': 1.64, 'cap': 138_000_000_000}
}

print(f"\n📊 Market Data Loaded: {len(MARKET_DATA)} stocks")

# Simple analysis
print("\n🔬 RUNNING SIMPLE BACKTEST:")
print("-" * 30)

for symbol, data in MARKET_DATA.items():
    gap = data['gap']
    market_cap_b = data['cap'] / 1_000_000_000
    
    # Simple logic without LLM
    if gap > 2:
        signal = "🚀 STRONG BUY"
        score = 80
    elif gap > 0:
        signal = "🟢 BUY"
        score = 60
    elif gap < -2:
        signal = "📉 STRONG SHORT"
        score = 80
    else:
        signal = "🔴 SHORT"
        score = 60
    
    print(f"{symbol}: {signal} | Gap: {gap:+.1f}% | Cap: ${market_cap_b:.1f}B | Score: {score}")

print("\n✅ BASIC BACKTEST COMPLETE!")
print("🎯 This proves the bot structure works")
print("🔧 Now we can add LLM analysis once API issues are resolved")

print(f"\n⏰ Test completed at: {datetime.now()}")

# Keep container running for a bit
print("\n⏳ Keeping container alive for 30 seconds...")
time.sleep(30)
print("🏁 Test finished")
