import requests
import os

# Your bot details
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7626751011:AAHHWa7ItXmjaP4-icgw8Aiy6_SdvhMdVK4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1001002605954379")

def test_telegram():
    print("🔧 Testing Telegram connection...")
    
    # Test 1: Bot info
    bot_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    try:
        response = requests.get(bot_url)
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Bot OK: @{bot_info['result']['username']}")
        else:
            print(f"❌ Bot failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Bot error: {e}")
        return
    
    # Test 2: Send test message
    message = "🔧 Test message from Railway bot"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Try different methods
    test_methods = [
        {'chat_id': TELEGRAM_CHAT_ID, 'text': message},
        {'chat_id': '@kp_earning_report_stockbot', 'text': message},
        {'chat_id': TELEGRAM_CHAT_ID.replace('-100', ''), 'text': message}
    ]
    
    for i, data in enumerate(test_methods, 1):
        print(f"🔄 Method {i}: {data['chat_id']}")
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                print(f"✅ SUCCESS with method {i}!")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("❌ All methods failed")
    return False

if __name__ == "__main__":
    test_telegram()
