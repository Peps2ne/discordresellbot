# Config File Of The Bot
import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0)) if os.getenv('GUILD_ID') else None

# Database Configuration
DATABASE_PATH = 'reseller_bot.db'

# Keys Configuration
KEYS_CONFIG = {
    'vallifetime': {
        'file': 'keys/vallifetime_keys.txt',
        'prefix': 'VAL-LT-'
    },
    'val1month': {
        'file': 'keys/val1month_keys.txt',
        'prefix': 'VAL-1M-'
    },
    'val1week': {
        'file': 'keys/val1week_keys.txt',
        'prefix': 'VAL-1W-'
    },
    'wooflifetime': {
        'file': 'keys/wooflifetime_keys.txt',
        'prefix': 'WOOF-LT-'
    },
    'woof1month': {
        'file': 'keys/woof1month_keys.txt',
        'prefix': 'WOOF-1M-'
    },
    'woof1week': {
        'file': 'keys/woof1week_keys.txt',
        'prefix': 'WOOF-1W-'
    }
}

# Embed Colors
COLORS = {
    'success': 0x00ff00,
    'error': 0xff0000,
    'info': 0x0099ff,
    'warning': 0xffaa00,
    'primary': 0x7289da
}

# Product Configuration
PRODUCTS = {
    'vallifetime': {
        'name': '🔥 Valorant LifeTime License',
        'price': 495.0,
        'duration': 365,
        'description': 'Valorant LifeTime Access'
    },
    'val1month': {
        'name': '⭐ Valorant 1 Month License',
        'price': 285.0,
        'duration': 30,
        'description': 'Valorant 1 Month Access'
    },
    'val1week': {
        'name': '🚀 Valorant 1 Week License',
        'price': 100.0,
        'duration': 7,
        'description': 'Valorant 1 Week Access'
    },
    'wooflifetime': {
        'name': '🔥 Spoofer LifeTime License',
        'price': 495.0,
        'duration': 365,
        'description': 'Woofer LifeTime Access'
    },
    'woof1month': {
        'name': '⭐ Spoofer 1 Month License',
        'price': 360.0,
        'duration': 30,
        'description': 'Woofer 1 Month Access'
    },
    'woof1week': {
        'name': '🚀 Spoofer 1 Week License',
        'price': 100.0,
        'duration': 7,
        'description': 'Woofer 1 Week Access'
    }
}

# Admin User IDs - ADD YOUR DISCORD ID HERE
ADMIN_IDS = [1091441605430493185]

# Auto-create keys directory
os.makedirs('keys', exist_ok=True)

# Validation
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found! Check your .env file.")
    exit(1)

print("✅ Config loaded!")
print(f"🏠 Guild ID: {GUILD_ID}")
print(f"👑 Admin: {ADMIN_IDS[0]}")
print(f"📁 Keys folder: {os.path.abspath('keys')}")
