# 🤖 ResellerBot - License Management Bot
# 📋 Description
ResellerBot is an advanced Discord bot developed specifically for the sale and management of Valorant cheat and Woofer spoofer licenses. The reseller system fully automates your license sales processes with automatic license distribution and a comprehensive admin panel. (You can place the product you are selling in the Config section. The general purpose is to sell license keys.)

# ✨ Features
- 🎯 Product Management
- Valorant Licenses
- 🔥 Lifetime (365 days) - $$
- ⭐ 1 Month (30 days) - $$
- 🚀 1 Week (7 days) - $$
- Spoofer Licenses
- 🔥 Lifetime (365 days) - $$
- ⭐ 1 Month (30 days) - $$
- 🚀 1 Week (7 days) - $$

🏪 Reseller System
- Customizable commission rates
- Automatic purchase with balance
- Commission tracking and earnings reports
- Reseller codes and statistics

🔑 License Management
- Manual key file management
- Automatic key retrieval and return system
- HWID binding and reset (daily limit)
- License term tracking and automatic deactivation

💰 Advanced Balance System
- Real-time balance tracking
- Detailed transaction history
- Admin-controlled balance addition/removal
- Automatic commission calculation

# 🚀 Installation
- 1- Requirements
pip install discord.py aiosqlite python-dotenv
- 2- Create a File Structure
ResellerBot/
├── bot.py
├── config.py
├── database.py
├── setup_database.py
├── .env
├── README.md
└── keys/ (will be created automaticly)
- 3- Set up the configuration
In the config.py file:
Add your Discord ID to the ADMIN_IDS list
Adjust product prices according to your needs
- 4- Set up the database
python setup_database.py
- 5- Launch Bot
python bot.py

# 🎮 Usage
👤 User Commands
- /prices - View product prices and stock status
- /myproducts - List the licenses you own
- /balance - Check your balance and transaction history

🏪 Reseller Commands
- /purchase - Purchase licenses with your balance (for yourself or your customers)

👑 Admin Commands
- /admin - Access the comprehensive admin control panel
- /addkey - Add a key to the specified product
- /stock - View the stock status of all products
- /licenses - Delete the specified license and return the key to stock
- /hwidreset - Reset the user's HWID
- /debug - View system status and debug information

📁 Key File Management
- Key File Format
- Keys are stored in separate files for each product:
- keys/vallifetime_keys.txt:
- VAL-LT-VALLIFETIME-2024-0001-SAMPLE
- VAL-LT-VALLIFETIME-2024-0002-SAMPLE
- VAL-LT-VALLIFETIME-2024-0003-SAMPLE

📁Adding Keys
- Manual: Add one key per line to the relevant file.

📁Key Processing Procedure
- When a license is purchased, the first key is extracted from the file.
- The key is assigned to the license and deleted from the file.
- If the license is canceled, the key is returned to the file.

🛡️ Security Features

**HWID Protection**
- Each license can be linked to one device
- Daily HWID reset limit (default: 3)
- Unlimited HWID resets by admin

**Admin Permissions**
- Only specified admin IDs can perform management operations
- All admin operations are logged
- Approval system for sensitive operations

**Data Security**
- Secure data storage with SQLite database
- Automatic transaction rollback
- Key return system in case of error

📊 Statistics and Reporting

Bot Statistics
- Total number of users and resellers
- Number of active and total licenses
- Monthly and total revenue reports
- Product-based sales analysis

Reseller Analysis
- Top-selling resellers
- Commission earnings reports
- Monthly and total sales performance

Add New Product

- 1- config.py → Add a new product to the PRODUCTS dict
- 2- Add key file configuration to the KEYS_CONFIG dict
- 3- Create the relevant key file
- 4- Add to the slash command choices

Commission Rates

- Default commission rate in config.py
- ‘commission_rate’: 0.20  # 20% commission

Price Update

- config.py → PRODUCTS
'vallifetime': {
-     'name': '🔥 Premium Valorant Lisansı',
-     'price': 495.0,  # Change The Price
-     'duration': 365,
-     'description': 'Valorant LifeTime Lisans'
}

# 📞 Support

For issues:

- Check this README file
- Check the system status with the /debug command
- Open an issue or contact the developer:

https://guns.lol/peps2ne / https://instagram.com/peps2ne / https://discord.com/invite/wkVNw27UFe

# 📄 License
This project is licensed under the MIT license.

# 🔗 Important Links

- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord.py Documentation](https://discordpy.readthedocs.io/en/stable/)
- [SQLite Documentation](https://sqlite.org/docs.html)
























