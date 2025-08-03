# Database SourceCode Of The Bot
import aiosqlite
import datetime
import os
import random
import string
import hashlib
from typing import Optional, List, Dict, Any

from config import KEYS_CONFIG

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    # ========================
    # KEY MANAGEMENT
    # ========================
    
    async def get_available_key(self, product_type: str) -> Optional[str]:
        """Get an available key from the specified product type"""
        try:
            if product_type not in KEYS_CONFIG:
                print(f"❌ Invalid product_type: {product_type}")
                return None
            
            key_file = KEYS_CONFIG[product_type]['file']
            
            if not os.path.exists(key_file):
                print(f"❌ Key file not found: {key_file}")
                return None
            
            # Read keys from file
            with open(key_file, 'r', encoding='utf-8') as f:
                keys = [line.strip() for line in f.readlines() if line.strip()]
            
            if not keys:
                print(f"⚠️ {key_file} file is empty!")
                return None
            
            # Take the first key
            selected_key = keys[0]
            
            # Remove used key from file
            remaining_keys = keys[1:]
            with open(key_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(remaining_keys))
                if remaining_keys:
                    f.write('\n')
            
            print(f"✅ Key taken: {selected_key} ({len(remaining_keys)} remaining)")
            return selected_key
            
        except Exception as e:
            print(f"❌ Key retrieval error: {e}")
            return None
    
    async def return_key(self, product_type: str, key: str) -> bool:
        """Return key back to file (for cancellation cases)"""
        try:
            if product_type not in KEYS_CONFIG:
                return False
            
            key_file = KEYS_CONFIG[product_type]['file']
            
            # Read existing keys
            existing_keys = []
            if os.path.exists(key_file):
                with open(key_file, 'r', encoding='utf-8') as f:
                    existing_keys = [line.strip() for line in f.readlines() if line.strip()]
            
            # Don't add if key already exists
            if key in existing_keys:
                return True
            
            # Add key to the beginning of file
            existing_keys.insert(0, key)
            
            with open(key_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(existing_keys))
                if existing_keys:
                    f.write('\n')
            
            print(f"✅ Key returned: {key}")
            return True
            
        except Exception as e:
            print(f"❌ Key return error: {e}")
            return False
    
    async def get_key_count(self, product_type: str) -> int:
        """Get the number of remaining keys for specified product type"""
        try:
            if product_type not in KEYS_CONFIG:
                return 0
            
            key_file = KEYS_CONFIG[product_type]['file']
            
            if not os.path.exists(key_file):
                return 0
            
            with open(key_file, 'r', encoding='utf-8') as f:
                keys = [line.strip() for line in f.readlines() if line.strip()]
            
            return len(keys)
            
        except Exception as e:
            print(f"❌ Key count error: {e}")
            return 0
    
    async def add_key(self, product_type: str, key: str) -> bool:
        """Add new key"""
        try:
            if product_type not in KEYS_CONFIG:
                return False
            
            key_file = KEYS_CONFIG[product_type]['file']
            
            # Check existing keys
            existing_keys = []
            if os.path.exists(key_file):
                with open(key_file, 'r', encoding='utf-8') as f:
                    existing_keys = [line.strip() for line in f.readlines() if line.strip()]
            
            # Don't add if key already exists
            if key in existing_keys:
                return False
            
            # Add key to file
            with open(key_file, 'a', encoding='utf-8') as f:
                f.write(key + '\n')
            
            print(f"✅ New key added: {key}")
            return True
            
        except Exception as e:
            print(f"❌ Key adding error: {e}")
            return False
    
    # ========================
    # DATABASE INITIALIZATION
    # ========================
    
    async def init_db(self):
        """Initialize database and create tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance REAL DEFAULT 0.0,
                    total_spent REAL DEFAULT 0.0,
                    total_earned REAL DEFAULT 0.0,
                    is_reseller BOOLEAN DEFAULT FALSE,
                    commission_rate REAL DEFAULT 0.0,
                    reseller_code TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Licenses table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    license_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    product_type TEXT NOT NULL,
                    product_name TEXT,
                    hwid TEXT,
                    hwid_limit INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    created_by INTEGER,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Transactions table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL NOT NULL,
                    transaction_type TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # HWID resets table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS hwid_resets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id TEXT,
                    user_id INTEGER,
                    reset_by INTEGER,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (license_id) REFERENCES licenses (license_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Admin logs table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    admin_username TEXT,
                    action TEXT NOT NULL,
                    target_user INTEGER,
                    target_license TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add default settings
            await db.execute('''
                INSERT OR IGNORE INTO settings (key, value) VALUES 
                ('max_hwid_resets_per_day', '3'),
                ('bot_status', 'active'),
                ('maintenance_mode', 'false')
            ''')
            
            await db.commit()
        
        # Check and create key files
        await self.ensure_key_files()
    
    async def ensure_key_files(self):
        """Ensure key files exist"""
        for product_type, config in KEYS_CONFIG.items():
            key_file = config['file']
            if not os.path.exists(key_file):
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                with open(key_file, 'w', encoding='utf-8') as f:
                    f.write("")  # Create empty file
                print(f"📁 Created: {key_file}")
    
    # ========================
    # UTILITY FUNCTIONS
    # ========================
    
    def generate_reseller_code(self) -> str:
        """Generate unique reseller code"""
        chars = string.ascii_uppercase + string.digits
        return 'RSL' + ''.join(random.choice(chars) for _ in range(8))
    
    def hash_hwid(self, hwid: str) -> str:
        """Hash HWID"""
        return hashlib.sha256(hwid.encode()).hexdigest()
    
    # ========================
    # USER OPERATIONS
    # ========================
    
    async def create_user(self, user_id: int, username: str) -> bool:
        """Create new user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                    (user_id, username)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT * FROM users WHERE user_id = ?',
                    (user_id,)
                )
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def update_user_activity(self, user_id: int) -> bool:
        """Update user activity"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?',
                    (user_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Error updating user activity: {e}")
            return False
    
    async def update_balance(self, user_id: int, amount: float, transaction_type: str, description: str = None) -> bool:
        """Update user balance"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Update balance
                await db.execute(
                    'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                    (amount, user_id)
                )
                
                # Add transaction record
                await db.execute(
                    'INSERT INTO transactions (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)',
                    (user_id, amount, transaction_type, description)
                )
                
                # Update total spent/earned
                if amount > 0:
                    await db.execute(
                        'UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?',
                        (amount, user_id)
                    )
                else:
                    await db.execute(
                        'UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?',
                        (abs(amount), user_id)
                    )
                
                await db.commit()
                return True
        except Exception as e:
            print(f"Error updating balance: {e}")
            return False
    
    async def make_reseller(self, user_id: int, commission_rate: float) -> tuple:
        """Make user a reseller"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Generate unique reseller code
                while True:
                    reseller_code = self.generate_reseller_code()
                    cursor = await db.execute(
                        'SELECT COUNT(*) FROM users WHERE reseller_code = ?',
                        (reseller_code,)
                    )
                    count = await cursor.fetchone()
                    if count[0] == 0:
                        break
                
                await db.execute(
                    'UPDATE users SET is_reseller = TRUE, commission_rate = ?, reseller_code = ? WHERE user_id = ?',
                    (commission_rate, reseller_code, user_id)
                )
                await db.commit()
                return True, reseller_code
        except Exception as e:
            print(f"Error making reseller: {e}")
            return False, None
    
    async def search_users(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    '''SELECT * FROM users 
                       WHERE CAST(user_id AS TEXT) LIKE ? OR username LIKE ? 
                       ORDER BY last_activity DESC LIMIT ?''',
                    (f'%{query}%', f'%{query}%', limit)
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error searching users: {e}")
            return []
    
    # ========================
    # LICENSE OPERATIONS
    # ========================
    
    async def create_license(self, user_id: int, product_type: str, duration_days: int, 
                           created_by: int, hwid_limit: int = 1, product_name: str = None) -> Optional[str]:
        """Create new license"""
        try:
            # Get key from text file
            license_id = await self.get_available_key(product_type)
            
            if not license_id:
                print(f"❌ No available key found for {product_type}!")
                return None
            
            async with aiosqlite.connect(self.db_path) as db:
                expires_at = datetime.datetime.now() + datetime.timedelta(days=duration_days)
                
                await db.execute(
                    '''INSERT INTO licenses 
                       (license_id, user_id, product_type, product_name, hwid_limit, expires_at, created_by) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (license_id, user_id, product_type, product_name, hwid_limit, expires_at, created_by)
                )
                await db.commit()
                
                print(f"✅ License created: {license_id}")
                return license_id
                
        except Exception as e:
            print(f"❌ License creation error: {e}")
            # Return key on error
            if 'license_id' in locals():
                await self.return_key(product_type, license_id)
            return None
    
    async def get_license_by_id(self, license_id: str) -> Optional[Dict]:
        """Get license by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT * FROM licenses WHERE license_id = ?',
                    (license_id,)
                )
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting license: {e}")
            return None
    
    async def get_user_licenses(self, user_id: int, include_expired: bool = False) -> List[Dict]:
        """Get user licenses"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if include_expired:
                    cursor = await db.execute(
                        'SELECT * FROM licenses WHERE user_id = ? ORDER BY created_at DESC',
                        (user_id,)
                    )
                else:
                    cursor = await db.execute(
                        'SELECT * FROM licenses WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP ORDER BY created_at DESC',
                        (user_id,)
                    )
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting user licenses: {e}")
            return []
    
    async def delete_license(self, license_id: str, user_id: int) -> bool:
        """Delete license"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # First get license info
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT * FROM licenses WHERE license_id = ? AND user_id = ?',
                    (license_id, user_id)
                )
                license_data = await cursor.fetchone()
                
                if not license_data:
                    return False
                
                # Delete license
                await db.execute(
                    'DELETE FROM licenses WHERE license_id = ? AND user_id = ?',
                    (license_id, user_id)
                )
                await db.commit()
                
                # Return key to stock
                await self.return_key(license_data['product_type'], license_id)
                
                return True
        except Exception as e:
            print(f"Error deleting license: {e}")
            return False
    
    async def reset_hwid(self, license_id: str, user_id: int, reason: str) -> bool:
        """Reset HWID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE licenses SET hwid = NULL WHERE license_id = ? AND user_id = ?',
                    (license_id, user_id)
                )
                
                # Add reset record
                await db.execute(
                    'INSERT INTO hwid_resets (license_id, user_id, reason) VALUES (?, ?, ?)',
                    (license_id, user_id, reason)
                )
                
                await db.commit()
                return True
        except Exception as e:
            print(f"Error resetting HWID: {e}")
            return False
    
    async def get_hwid_reset_count(self, user_id: int, days: int = 1) -> int:
        """Get user's daily HWID reset count"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''SELECT COUNT(*) FROM hwid_resets 
                       WHERE user_id = ? AND created_at >= datetime('now', '-{} days')'''.format(days),
                    (user_id,)
                )
                count = await cursor.fetchone()
                return count[0] if count else 0
        except Exception as e:
            print(f"Error getting HWID reset count: {e}")
            return 0
    
    async def search_licenses(self, query: str, limit: int = 10) -> List[Dict]:
        """Search licenses"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    '''SELECT * FROM licenses 
                       WHERE license_id LIKE ? OR product_type LIKE ? 
                       ORDER BY created_at DESC LIMIT ?''',
                    (f'%{query}%', f'%{query}%', limit)
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error searching licenses: {e}")
            return []
    
    # ========================
    # TRANSACTION OPERATIONS
    # ========================
    
    async def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user transactions"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
                    (user_id, limit)
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []
    
    # ========================
    # ADMIN OPERATIONS
    # ========================
    
    async def log_admin_action(self, admin_id: int, action: str, target_user: int = None, 
                             target_license: str = None, details: str = None) -> bool:
        """Log admin activity"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''INSERT INTO admin_logs 
                       (admin_id, action, target_user, target_license, details) 
                       VALUES (?, ?, ?, ?, ?)''',
                    (admin_id, action, target_user, target_license, details)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Error logging admin action: {e}")
            return False
    
    async def get_admin_logs(self, limit: int = 20) -> List[Dict]:
        """Get admin logs"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?',
                    (limit,)
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting admin logs: {e}")
            return []
    
    # ========================
    # STATISTICS & CLEANUP
    # ========================
    
    async def get_bot_statistics(self) -> Dict[str, Any]:
        """Get bot statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # Total users
                cursor = await db.execute('SELECT COUNT(*) FROM users')
                stats['total_users'] = (await cursor.fetchone())[0]
                
                # Total resellers
                cursor = await db.execute('SELECT COUNT(*) FROM users WHERE is_reseller = TRUE')
                stats['total_resellers'] = (await cursor.fetchone())[0]
                
                # Active licenses
                cursor = await db.execute('SELECT COUNT(*) FROM licenses WHERE expires_at > CURRENT_TIMESTAMP')
                stats['active_licenses'] = (await cursor.fetchone())[0]
                
                # Total licenses
                cursor = await db.execute('SELECT COUNT(*) FROM licenses')
                stats['total_licenses'] = (await cursor.fetchone())[0]
                
                # Monthly licenses
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM licenses WHERE created_at >= date('now', 'start of month')"
                )
                stats['monthly_licenses'] = (await cursor.fetchone())[0]
                
                # Total revenue
                cursor = await db.execute(
                    "SELECT SUM(ABS(amount)) FROM transactions WHERE transaction_type = 'purchase'"
                )
                result = await cursor.fetchone()
                stats['total_revenue'] = result[0] if result[0] else 0.0
                
                # Monthly revenue
                cursor = await db.execute(
                    """SELECT SUM(ABS(amount)) FROM transactions 
                       WHERE transaction_type = 'purchase' 
                       AND created_at >= date('now', 'start of month')"""
                )
                result = await cursor.fetchone()
                stats['monthly_revenue'] = result[0] if result[0] else 0.0
                
                return stats
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    async def cleanup_expired_licenses(self) -> int:
        """Clean up expired licenses"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT COUNT(*) FROM licenses WHERE expires_at <= CURRENT_TIMESTAMP AND is_active = TRUE'
                )
                count = (await cursor.fetchone())[0]
                
                await db.execute(
                    'UPDATE licenses SET is_active = FALSE WHERE expires_at <= CURRENT_TIMESTAMP'
                )
                await db.commit()
                
                return count
        except Exception as e:
            print(f"Error cleaning up licenses: {e}")
            return 0
    
    # ========================
    # SETTINGS
    # ========================
    
    async def get_setting(self, key: str) -> Optional[str]:
        """Get setting value"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT value FROM settings WHERE key = ?',
                    (key,)
                )
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Error getting setting: {e}")
            return None
    
    async def set_setting(self, key: str, value: str) -> bool:
        """Set setting value"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                    (key, value)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Error setting value: {e}")
            return False
