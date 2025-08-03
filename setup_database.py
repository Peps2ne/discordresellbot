# Setup Database
import asyncio
import os
from database import Database
from config import DATABASE_PATH, KEYS_CONFIG, PRODUCTS

async def setup_database():
    """Database setup script"""
    
    print("🚀 ResellerBot Database Setup Starting...")
    
    # Remove old database if exists
    if os.path.exists(DATABASE_PATH):
        response = input(f"⚠️ {DATABASE_PATH} file already exists. Do you want to delete and recreate it? (y/N): ")
        if response.lower() == 'y':
            os.remove(DATABASE_PATH)
            print("✅ Old database deleted")
        else:
            print("❌ Setup cancelled")
            return
    
    # Create keys folder
    os.makedirs('keys', exist_ok=True)
    print("📁 Keys folder created")
    
    # Create key files
    for product_type, config in KEYS_CONFIG.items():
        key_file = config['file']
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        # Create sample keys
        sample_keys = []
        for i in range(5):
            sample_key = f"{config['prefix']}{product_type.upper()}-{2024}-{i+1:04d}-SAMPLE"
            sample_keys.append(sample_key)
        
        with open(key_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sample_keys) + '\n')
        
        print(f"📄 Created: {key_file} ({len(sample_keys)} sample keys)")
    
    # Initialize database
    db = Database(DATABASE_PATH)
    await db.init_db()
    print("✅ Database tables created")
    
    # Add test admin user
    admin_id = 1091441605430493185
    await db.create_user(admin_id, "Admin")
    await db.make_reseller(admin_id, 0.20)  # 20% commission
    await db.update_balance(admin_id, 1000.0, "admin_add", "Initial balance")
    print(f"👑 Test admin created: {admin_id} ($1000 balance, 20% commission)")
    
    print("\n🎉 Setup complete!")
    print("📊 Setup summary:")
    print(f"   • Database: {DATABASE_PATH}")
    print(f"   • Product count: {len(PRODUCTS)}")
    print(f"   • Key files: {len(KEYS_CONFIG)}")
    print(f"   • Test admin: {admin_id}")
    print(f"   • Each product has 5 sample keys")
    print("\n🚀 You can now run bot.py!")

if __name__ == "__main__":
    asyncio.run(setup_database())
