import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import asyncio
import datetime
import os
from typing import Optional

from config import *
from database import Database

# ========================
# BOT SETUP
# ========================

class ResellerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Database connection
        self.db = Database(DATABASE_PATH)
        
    async def setup_hook(self):
        """Runs when bot starts"""
        print("🔧 Bot setting up...")
        
    async def on_ready(self):
        print(f'🤖 Bot logged in as: {self.user}')
        print(f'🆔 Bot ID: {self.user.id}')
        print(f'🏠 Guild count: {len(self.guilds)}')
        
        try:
            # Initialize database
            await self.db.init_db()
            print("✅ Database initialized")
            
            # Sync slash commands
            try:
                if GUILD_ID:
                    guild = discord.Object(id=GUILD_ID)
                    synced = await self.tree.sync(guild=guild)
                    print(f"✅ Synced {len(synced)} commands (Guild)")
                else:
                    synced = await self.tree.sync()
                    print(f"✅ Synced {len(synced)} commands (Global)")
            except Exception as e:
                print(f"❌ Command sync failed: {e}")
            
            # Start cleanup task
            if not cleanup_task.is_running():
                cleanup_task.start()
                print("🧹 Cleanup task started")
            
        except Exception as e:
            print(f"❌ Bot startup error: {e}")

# Bot instance
bot = ResellerBot()

# ========================
# UTILITY FUNCTIONS
# ========================

def create_embed(title: str, description: str, color: int) -> discord.Embed:
    """Create standard embed"""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.datetime.now()
    return embed

async def ensure_user_exists(user_id: int, username: str):
    """Ensure user exists in database"""
    await bot.db.create_user(user_id, username)
    await bot.db.update_user_activity(user_id)

# ========================
# BACKGROUND TASKS
# ========================

@tasks.loop(hours=24)
async def cleanup_task():
    """Daily cleanup task"""
    try:
        cleaned = await bot.db.cleanup_expired_licenses()
        print(f"🧹 Daily cleanup: {cleaned} expired licenses cleaned")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

@cleanup_task.before_loop
async def before_cleanup():
    """Wait for bot to be ready before cleanup task starts"""
    await bot.wait_until_ready()

# ========================
# USER COMMANDS
# ========================

@bot.tree.command(name="balance", description="View your balance and transaction history")
async def balance(interaction: discord.Interaction):
    await ensure_user_exists(interaction.user.id, interaction.user.display_name)
    
    user_data = await bot.db.get_user(interaction.user.id)
    if not user_data:
        embed = create_embed("❌ Error", "Could not retrieve user information.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get recent transactions
    transactions = await bot.db.get_user_transactions(interaction.user.id, 5)
    
    embed = create_embed(
        "💰 Balance Information",
        f"**Current Balance:** ${user_data['balance']:.2f}",
        COLORS['info']
    )
    
    embed.add_field(
        name="📊 Statistics",
        value=f"**Total Spent:** ${user_data['total_spent']:.2f}\n" +
              f"**Total Earned:** ${user_data['total_earned']:.2f}\n" +
              f"**Reseller:** {'✅ Yes' if user_data['is_reseller'] else '❌ No'}",
        inline=True
    )
    
    if user_data['is_reseller']:
        embed.add_field(
            name="🏪 Reseller Information",
            value=f"**Commission Rate:** {user_data['commission_rate']*100:.1f}%\n" +
                  f"**Reseller Code:** `{user_data['reseller_code']}`",
            inline=True
        )
    
    # Recent transactions
    if transactions:
        transaction_text = ""
        for tx in transactions:
            tx_type = "➕" if tx['amount'] > 0 else "➖"
            transaction_text += f"{tx_type} ${tx['amount']:+.2f} - {tx['transaction_type']}\n"
        
        embed.add_field(
            name="📋 Recent Transactions",
            value=transaction_text[:1000],
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="licenses", description="View your licenses")
async def licenses(interaction: discord.Interaction):
    await ensure_user_exists(interaction.user.id, interaction.user.display_name)
    
    licenses = await bot.db.get_user_licenses(interaction.user.id)
    
    if not licenses:
        embed = create_embed(
            "📦 Your Licenses",
            "You don't have any licenses yet.\n\n" +
            "💳 Contact administrators to purchase licenses.",
            COLORS['info']
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = create_embed(
        "📦 Your Licenses",
        f"You have {len(licenses)} active licenses:",
        COLORS['success']
    )
    
    for license_data in licenses:
        expires_at = datetime.datetime.fromisoformat(license_data['expires_at'].replace('Z', '+00:00'))
        days_left = (expires_at - datetime.datetime.now(datetime.timezone.utc)).days
        
        status_emoji = "✅" if days_left > 0 else "⏰"
        status_text = f"{days_left} days left" if days_left > 0 else "Expired"
        
        embed.add_field(
            name=f"{status_emoji} {license_data['product_name'] or license_data['product_type']}",
            value=f"**License ID:** `{license_data['license_id']}`\n" +
                  f"**Status:** {status_text}\n" +
                  f"**HWID:** {'Bound' if license_data['hwid'] else 'Not bound'}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="prices", description="View current product prices")
async def prices(interaction: discord.Interaction):
    await ensure_user_exists(interaction.user.id, interaction.user.display_name)
    user_data = await bot.db.get_user(interaction.user.id)
    
    embed = create_embed("💰 Product Price List", "Our current products and prices:", COLORS['info'])
    
    is_reseller = user_data and user_data['is_reseller']
    commission_rate = user_data['commission_rate'] if is_reseller else 0
    
    # Valorant products
    embed.add_field(
        name="🎯 VALORANT PRODUCTS",
        value="⬇️ Valorant cheat licenses",
        inline=False
    )
    
    val_products = ['vallifetime', 'val1month', 'val1week']
    for product_id in val_products:
        if product_id in PRODUCTS:
            product = PRODUCTS[product_id]
            original_price = product['price']
            reseller_price = original_price * (1 - commission_rate) if is_reseller else original_price
            
            # Check stock
            key_count = await bot.db.get_key_count(product_id)
            stock_text = f"📦 **Stock:** {key_count} keys" if key_count > 0 else "❌ **Out of stock**"
            
            value_text = f"💵 **${original_price}**\n⏰ {product['duration']} days\n📝 {product['description']}\n{stock_text}"
            
            if is_reseller:
                value_text += f"\n\n🏪 **Your Price:** ${reseller_price:.2f}"
                value_text += f"\n💰 **Your Commission:** ${original_price - reseller_price:.2f}"
            
            embed.add_field(
                name=product['name'],
                value=value_text,
                inline=True
            )
    
    # Spoofer products
    embed.add_field(
        name="🛡️ SPOOFER PRODUCTS",
        value="⬇️ Woofer spoofer licenses",
        inline=False
    )
    
    woof_products = ['wooflifetime', 'woof1month', 'woof1week']
    for product_id in woof_products:
        if product_id in PRODUCTS:
            product = PRODUCTS[product_id]
            original_price = product['price']
            reseller_price = original_price * (1 - commission_rate) if is_reseller else original_price
            
            # Check stock
            key_count = await bot.db.get_key_count(product_id)
            stock_text = f"📦 **Stock:** {key_count} keys" if key_count > 0 else "❌ **Out of stock**"
            
            value_text = f"💵 **${original_price}**\n⏰ {product['duration']} days\n📝 {product['description']}\n{stock_text}"
            
            if is_reseller:
                value_text += f"\n\n🏪 **Your Price:** ${reseller_price:.2f}"
                value_text += f"\n💰 **Your Commission:** ${original_price - reseller_price:.2f}"
            
            embed.add_field(
                name=product['name'],
                value=value_text,
                inline=True
            )
    
    if is_reseller:
        embed.add_field(
            name="🛒 Reseller Purchase",
            value=f"**Your Commission Rate:** {commission_rate*100:.1f}%\n" +
                  f"**Current Balance:** ${user_data['balance']:.2f}\n\n" +
                  "Use `/purchase` command to buy licenses with your balance!",
            inline=False
        )
    else:
        embed.add_field(
            name="💳 Purchase",
            value="Contact administrators to purchase licenses.\n\n" +
                  "🏪 **Want to become a reseller?**\n" +
                  "• Earn commissions\n" +
                  "• Buy directly with balance",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ========================
# RESELLER COMMANDS
# ========================

@bot.tree.command(name="purchase", description="Purchase a license (Resellers only)")
@app_commands.describe(
    product_type="Product type to purchase",
    user_id="User ID to give the license to (optional, leave empty for yourself)"
)
@app_commands.choices(product_type=[
    app_commands.Choice(name="🔥 Valorant LifeTime", value="vallifetime"),
    app_commands.Choice(name="⭐ Valorant 1 Month", value="val1month"),
    app_commands.Choice(name="🚀 Valorant 1 Week", value="val1week"),
    app_commands.Choice(name="🔥 Spoofer LifeTime", value="wooflifetime"),
    app_commands.Choice(name="⭐ Spoofer 1 Month", value="woof1month"),
    app_commands.Choice(name="🚀 Spoofer 1 Week", value="woof1week")
])
async def purchase(interaction: discord.Interaction, product_type: str, user_id: Optional[str] = None):
    # Ensure user exists
    await ensure_user_exists(interaction.user.id, interaction.user.display_name)
    
    # Get user data
    user_data = await bot.db.get_user(interaction.user.id)
    
    # Check if user is reseller
    if not user_data or not user_data['is_reseller']:
        embed = create_embed(
            "❌ Unauthorized Access",
            "**Only resellers can use this command!**\n\n" +
            "🏪 Contact administrators to become a reseller.\n" +
            "• Earn commissions\n" +
            "• Buy directly with balance\n" +
            "• Serve your customers faster",
            COLORS['error']
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check product validity
    if product_type not in PRODUCTS:
        embed = create_embed("❌ Invalid Product", "The specified product was not found.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    product = PRODUCTS[product_type]
    
    # Calculate reseller price
    original_price = product['price']
    reseller_price = original_price * (1 - user_data['commission_rate'])
    commission = original_price - reseller_price
    
    # Check stock
    key_count = await bot.db.get_key_count(product_type)
    if key_count <= 0:
        embed = create_embed(
            "❌ Out of Stock",
            f"**{product['name']}** is out of stock.\n\n" +
            "📞 Please contact administrators.",
            COLORS['warning']
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check balance
    if user_data['balance'] < reseller_price:
        embed = create_embed(
            "❌ Insufficient Balance",
            f"**Required Balance:** ${reseller_price:.2f}\n" +
            f"**Current Balance:** ${user_data['balance']:.2f}\n" +
            f"**Missing:** ${reseller_price - user_data['balance']:.2f}\n\n" +
            "💰 Contact administrators to add balance.",
            COLORS['error']
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Determine target user
    target_user_id = interaction.user.id
    target_username = interaction.user.display_name
    
    if user_id:
        try:
            target_user_id = int(user_id)
            target_user = bot.get_user(target_user_id)
            if target_user:
                target_username = target_user.display_name
            else:
                target_username = f"User {target_user_id}"
        except ValueError:
            embed = create_embed("❌ Invalid User ID", "Please enter a valid user ID.", COLORS['error'])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    # Confirmation message
    embed = create_embed(
        "🛒 Purchase Confirmation",
        f"**Product:** {product['name']}\n" +
        f"**Duration:** {product['duration']} days\n" +
        f"**Target User:** <@{target_user_id}>\n" +
        f"**Price:** ${reseller_price:.2f}\n" +
        f"**Your Commission:** ${commission:.2f}\n\n" +
        "✅ Click **Purchase** to confirm.",
        COLORS['info']
    )
    
    class PurchaseView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
        
        @discord.ui.button(label='✅ Purchase', style=discord.ButtonStyle.success)
        async def purchase(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Only the command user can perform this action.", ephemeral=True)
                return
            
            try:
                # Ensure target user exists
                await ensure_user_exists(target_user_id, target_username)
                
                # Create license
                license_id = await bot.db.create_license(
                    target_user_id, 
                    product_type, 
                    product['duration'],
                    interaction.user.id,
                    1,
                    product['name']
                )
                
                if not license_id:
                    embed = create_embed(
                        "❌ Purchase Failed",
                        "License creation failed. Checking stock...",
                        COLORS['error']
                    )
                    await button_interaction.response.edit_message(embed=embed, view=None)
                    return
                
                # Deduct balance
                success = await bot.db.update_balance(
                    interaction.user.id,
                    -reseller_price,
                    "purchase",
                    f"Reseller purchase: {product['name']} for user {target_user_id}"
                )
                
                if not success:
                    # Return key if payment fails
                    await bot.db.return_key(product_type, license_id)
                    embed = create_embed(
                        "❌ Payment Failed",
                        "Balance transaction failed. Transaction cancelled.",
                        COLORS['error']
                    )
                    await button_interaction.response.edit_message(embed=embed, view=None)
                    return
                
                # Admin log
                await bot.db.log_admin_action(
                    interaction.user.id,
                    "reseller_purchase",
                    target_user_id,
                    license_id,
                    f"Product: {product_type}, Price: {reseller_price:.2f}"
                )
                
                # Success message
                embed = create_embed(
                    "✅ Purchase Successful!",
                    f"**License ID:** `{license_id}`\n" +
                    f"**Product:** {product['name']}\n" +
                    f"**Target User:** <@{target_user_id}>\n" +
                    f"**Paid:** ${reseller_price:.2f}\n" +
                    f"**Commission:** ${commission:.2f}\n" +
                    f"**Remaining Balance:** ${user_data['balance'] - reseller_price:.2f}",
                    COLORS['success']
                )
                
                await button_interaction.response.edit_message(embed=embed, view=None)
                
                # Try to send DM to target user
                if target_user_id != interaction.user.id:
                    try:
                        target_user = bot.get_user(target_user_id)
                        if target_user:
                            dm_embed = create_embed(
                                "🎉 New License Received!",
                                f"**License ID:** `{license_id}`\n" +
                                f"**Product:** {product['name']}\n" +
                                f"**Duration:** {product['duration']} days\n" +
                                f"**Purchased by:** {interaction.user.display_name}\n\n" +
                                f"You can start using your license now!",
                                COLORS['success']
                            )
                            await target_user.send(embed=dm_embed)
                    except:
                        pass  # Ignore if DM fails
                
            except Exception as e:
                embed = create_embed(
                    "❌ Error Occurred",
                    f"An unexpected error occurred: {str(e)}",
                    COLORS['error']
                )
                await button_interaction.response.edit_message(embed=embed, view=None)
        
        @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.danger)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Only the command user can perform this action.", ephemeral=True)
                return
            
            embed = create_embed("❌ Purchase Cancelled", "Transaction cancelled.", COLORS['warning'])
            await button_interaction.response.edit_message(embed=embed, view=None)
    
    await interaction.response.send_message(embed=embed, view=PurchaseView(), ephemeral=True)

# ========================
# MODALS (Dialog Boxes)
# ========================

class UserSearchModal(discord.ui.Modal, title='👤 User Search'):
    def __init__(self):
        super().__init__()

    search_query = discord.ui.TextInput(
        label='User ID or Name',
        placeholder='Enter user ID or name to search...',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        query = self.search_query.value
        users = await bot.db.search_users(query)
        
        if not users:
            embed = create_embed("🔍 Search Result", "No users found.", COLORS['warning'])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = create_embed("🔍 User Search Results", f"**Search:** {query}", COLORS['info'])
        
        for user in users[:5]:  # Show first 5 results
            is_reseller = "🏪 Reseller" if user['is_reseller'] else "👤 Normal"
            embed.add_field(
                name=f"{is_reseller} - {user['username']}",
                value=f"**ID:** {user['user_id']}\n" +
                      f"**Balance:** ${user['balance']:.2f}\n" +
                      f"**Last Activity:** {user['last_activity'][:10]}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LicenseSearchModal(discord.ui.Modal, title='🔑 License Search'):
    def __init__(self):
        super().__init__()

    search_query = discord.ui.TextInput(
        label='License ID or Product Type',
        placeholder='Enter license ID or product type to search...',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        query = self.search_query.value
        licenses = await bot.db.search_licenses(query)
        
        if not licenses:
            embed = create_embed("🔍 Search Result", "No licenses found.", COLORS['warning'])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = create_embed("🔍 License Search Results", f"**Search:** {query}", COLORS['info'])
        
        for license_data in licenses[:5]:  # Show first 5 results
            status = "✅ Active" if license_data['is_active'] else "❌ Inactive"
            embed.add_field(
                name=f"{status} - {license_data['license_id']}",
                value=f"**User:** {license_data['user_id']}\n" +
                      f"**Product:** {license_data['product_type']}\n" +
                      f"**Expires:** {license_data['expires_at'][:10]}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BalanceModal(discord.ui.Modal, title='💰 Balance Operation'):
    def __init__(self, operation_type: str):
        self.operation_type = operation_type
        super().__init__()

    user_id = discord.ui.TextInput(
        label='User ID',
        placeholder='Enter the user ID for the operation...',
        required=True,
        max_length=20
    )
    
    amount = discord.ui.TextInput(
        label='Amount',
        placeholder='Enter amount to add/remove...',
        required=True,
        max_length=10
    )
    
    reason = discord.ui.TextInput(
        label='Reason',
        placeholder='Explain the reason for this operation...',
        required=False,
        max_length=200,
        style=discord.TextStyle.long
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            amount = float(self.amount.value)
            
            if self.operation_type == "remove":
                amount = -abs(amount)
            else:
                amount = abs(amount)
            
            # Ensure user exists
            user = bot.get_user(user_id)
            if user:
                await ensure_user_exists(user_id, user.display_name)
            else:
                await ensure_user_exists(user_id, "Unknown User")
            
            # Balance operation
            success = await bot.db.update_balance(
                user_id, amount, 
                "admin_add" if amount > 0 else "admin_remove",
                self.reason.value or "Manual operation by admin"
            )
            
            if success:
                # Admin log
                await bot.db.log_admin_action(
                    interaction.user.id, 
                    f"balance_{self.operation_type}",
                    user_id, None,
                    f"Amount: {amount}, Reason: {self.reason.value}"
                )
                
                embed = create_embed(
                    "✅ Balance Operation Successful",
                    f"**User:** <@{user_id}>\n" +
                    f"**Operation:** ${amount:+.2f}\n" +
                    f"**Reason:** {self.reason.value or 'Not specified'}",
                    COLORS['success']
                )
            else:
                embed = create_embed(
                    "❌ Balance Operation Failed",
                    "An error occurred. Please try again.",
                    COLORS['error']
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            embed = create_embed(
                "❌ Invalid Value",
                "Please enter a valid user ID and amount.",
                COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = create_embed(
                "❌ Error",
                f"An error occurred: {str(e)}",
                COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class LicenseCreateModal(discord.ui.Modal, title='🔑 Create License'):
    def __init__(self):
        super().__init__()

    user_id = discord.ui.TextInput(
        label='User ID',
        placeholder='Enter the user ID to give the license to...',
        required=True,
        max_length=20
    )
    
    product_type = discord.ui.TextInput(
        label='Product Type',
        placeholder='vallifetime, val1month, val1week, wooflifetime, woof1month, woof1week',
        required=True,
        max_length=50
    )
    
    duration = discord.ui.TextInput(
        label='Duration (Days)',
        placeholder='License duration (e.g., 30) - Leave empty for default',
        required=False,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            product_type = self.product_type.value.lower()
            
            # Check product type
            if product_type not in PRODUCTS:
                embed = create_embed(
                    "❌ Invalid Product Type",
                    f"Valid product types:\n" + "\n".join([f"• {key}: {value['name']}" for key, value in PRODUCTS.items()]),
                    COLORS['error']
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Determine duration
            if self.duration.value.strip():
                duration_days = int(self.duration.value)
            else:
                duration_days = PRODUCTS[product_type]['duration']
            
            # Ensure user exists
            user = bot.get_user(user_id)
            if user:
                await ensure_user_exists(user_id, user.display_name)
            else:
                await ensure_user_exists(user_id, "Unknown User")
            
            # Create license
            license_id = await bot.db.create_license(
                user_id, product_type, duration_days,
                interaction.user.id, 1, PRODUCTS[product_type]['name']
            )
            
            if license_id:
                # Admin log
                await bot.db.log_admin_action(
                    interaction.user.id, "license_create",
                    user_id, license_id,
                    f"Created {product_type} for {duration_days} days"
                )
                
                embed = create_embed(
                    "✅ License Created",
                    f"**License ID:** `{license_id}`\n" +
                    f"**User:** <@{user_id}>\n" +
                    f"**Product:** {PRODUCTS[product_type]['name']}\n" +
                    f"**Duration:** {duration_days} days",
                    COLORS['success']
                )
                
                # Try to send DM to user
                try:
                    if user:
                        dm_embed = create_embed(
                            "🎉 New License Received!",
                            f"**License ID:** `{license_id}`\n" +
                            f"**Product:** {PRODUCTS[product_type]['name']}\n" +
                            f"**Duration:** {duration_days} days\n\n" +
                            f"You can start using your license now!",
                            COLORS['success']
                        )
                        await user.send(embed=dm_embed)
                except:
                    pass  # Ignore if DM fails
                
            else:
                embed = create_embed(
                    "❌ License Creation Failed",
                    "No keys available or an error occurred.",
                    COLORS['error']
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            embed = create_embed(
                "❌ Invalid Value",
                "Please enter valid values.",
                COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = create_embed(
                "❌ Error",
                f"An error occurred: {str(e)}",
                COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ResellerCreateModal(discord.ui.Modal, title='🏪 Make Reseller'):
    def __init__(self):
        super().__init__()

    user_id = discord.ui.TextInput(
        label='User ID',
        placeholder='Enter the user ID to make reseller...',
        required=True,
        max_length=20
    )
    
    commission_rate = discord.ui.TextInput(
        label='Commission Rate (%)',
        placeholder='Enter commission rate (e.g., 20 = 20%)',
        required=True,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            commission = float(self.commission_rate.value) / 100.0
            
            if commission < 0 or commission > 1:
                embed = create_embed(
                    "❌ Invalid Commission",
                    "Commission rate must be between 0-100.",
                    COLORS['error']
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Ensure user exists
            user = bot.get_user(user_id)
            if user:
                await ensure_user_exists(user_id, user.display_name)
            else:
                await ensure_user_exists(user_id, "Unknown User")
            
            # Make reseller
            success, reseller_code = await bot.db.make_reseller(user_id, commission)
            
            if success:
                # Admin log
                await bot.db.log_admin_action(
                    interaction.user.id, "reseller_create",
                    user_id, None,
                    f"Commission rate: {commission*100:.1f}%, Code: {reseller_code}"
                )
                
                embed = create_embed(
                    "✅ Reseller Created",
                    f"**User:** <@{user_id}>\n" +
                    f"**Commission:** {commission*100:.1f}%\n" +
                    f"**Reseller Code:** `{reseller_code}`",
                    COLORS['success']
                )
                
                # Try to send DM to user
                try:
                    if user:
                        dm_embed = create_embed(
                            "🎉 You're Now a Reseller!",
                            f"**Your Commission Rate:** {commission*100:.1f}%\n" +
                            f"**Your Reseller Code:** `{reseller_code}`\n\n" +
                            f"🛒 Use `/purchase` command to buy licenses with your balance!\n" +
                            f"💰 Use `/balance` command to check your balance.",
                            COLORS['success']
                        )
                        await user.send(embed=dm_embed)
                except:
                    pass  # Ignore if DM fails
                
            else:
                embed = create_embed(
                    "❌ Reseller Creation Failed",
                    "An error occurred. Please try again.",
                    COLORS['error']
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            embed = create_embed(
                "❌ Invalid Value",
                "Please enter valid values.",
                COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = create_embed(
                "❌ Error",
                f"An error occurred: {str(e)}",
                COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# ========================
# ADMIN COMMANDS
# ========================

@bot.tree.command(name="admin", description="Admin panel (Admins only)")
async def admin_panel(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        embed = create_embed("❌ Unauthorized Access", "Only admins can use this command.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get bot statistics
    stats = await bot.db.get_bot_statistics()
    
    embed = create_embed(
        "👑 Admin Panel",
        "Welcome to the bot management panel!",
        COLORS['primary']
    )
    
    embed.add_field(
        name="📊 General Statistics",
        value=f"**👥 Total Users:** {stats.get('total_users', 0)}\n" +
              f"**🏪 Total Resellers:** {stats.get('total_resellers', 0)}\n" +
              f"**🔑 Active Licenses:** {stats.get('active_licenses', 0)}\n" +
              f"**📋 Total Licenses:** {stats.get('total_licenses', 0)}",
        inline=True
    )
    
    embed.add_field(
        name="💰 Revenue Statistics",
        value=f"**💵 Total Revenue:** ${stats.get('total_revenue', 0):.2f}\n" +
              f"**📅 Monthly Revenue:** ${stats.get('monthly_revenue', 0):.2f}\n" +
              f"**🎯 Monthly Licenses:** {stats.get('monthly_licenses', 0)} licenses",
        inline=True
    )
    
    # Check stock status
    stock_info = ""
    for product_id, product in PRODUCTS.items():
        key_count = await bot.db.get_key_count(product_id)
        stock_emoji = "✅" if key_count > 10 else "⚠️" if key_count > 0 else "❌"
        stock_info += f"{stock_emoji} {product['name']}: {key_count}\n"
    
    embed.add_field(
        name="📦 Stock Status",
        value=stock_info,
        inline=False
    )
    
    class AdminView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
        
        @discord.ui.button(label='👤 Search User', style=discord.ButtonStyle.primary, emoji='🔍')
        async def search_user(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            await button_interaction.response.send_modal(UserSearchModal())
        
        @discord.ui.button(label='🔑 Search License', style=discord.ButtonStyle.primary, emoji='🔍')
        async def search_license(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            await button_interaction.response.send_modal(LicenseSearchModal())
        
        @discord.ui.button(label='💰 Add Balance', style=discord.ButtonStyle.success, emoji='➕')
        async def add_balance(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            await button_interaction.response.send_modal(BalanceModal("add"))
        
        @discord.ui.button(label='💸 Remove Balance', style=discord.ButtonStyle.danger, emoji='➖')
        async def remove_balance(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            await button_interaction.response.send_modal(BalanceModal("remove"))
        
        @discord.ui.button(label='🔑 Create License', style=discord.ButtonStyle.success, emoji='✨')
        async def create_license(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            await button_interaction.response.send_modal(LicenseCreateModal())
        
        @discord.ui.button(label='🏪 Make Reseller', style=discord.ButtonStyle.secondary, emoji='👑')
        async def make_reseller(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            await button_interaction.response.send_modal(ResellerCreateModal())
        
        @discord.ui.button(label='📋 Admin Logs', style=discord.ButtonStyle.secondary, emoji='📜')
        async def admin_logs(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            logs = await bot.db.get_admin_logs(10)
            
            if not logs:
                embed = create_embed("📋 Admin Logs", "No log records found yet.", COLORS['info'])
            else:
                embed = create_embed("📋 Recent Admin Logs", f"Last {len(logs)} admin operations:", COLORS['info'])
                
                for log in logs:
                    embed.add_field(
                        name=f"🔸 {log['action']} - {log['created_at'][:16]}",
                        value=f"**Admin:** <@{log['admin_id']}>\n" +
                              f"**Target:** {f'<@{log['target_user']}>' if log['target_user'] else 'N/A'}\n" +
                              f"**Details:** {log['details'][:100] if log['details'] else 'N/A'}",
                        inline=False
                    )
            
            await button_interaction.response.send_message(embed=embed, ephemeral=True)
        
        @discord.ui.button(label='🔄 Refresh', style=discord.ButtonStyle.secondary, emoji='🔄')
        async def refresh(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            # Get new statistics
            new_stats = await bot.db.get_bot_statistics()
            
            new_embed = create_embed(
                "👑 Admin Panel (Updated)",
                "Welcome to the bot management panel!",
                COLORS['primary']
            )
            
            new_embed.add_field(
                name="📊 General Statistics",
                value=f"**👥 Total Users:** {new_stats.get('total_users', 0)}\n" +
                      f"**🏪 Total Resellers:** {new_stats.get('total_resellers', 0)}\n" +
                      f"**🔑 Active Licenses:** {new_stats.get('active_licenses', 0)}\n" +
                      f"**📋 Total Licenses:** {new_stats.get('total_licenses', 0)}",
                inline=True
            )
            
            new_embed.add_field(
                name="💰 Revenue Statistics",
                value=f"**💵 Total Revenue:** ${new_stats.get('total_revenue', 0):.2f}\n" +
                      f"**📅 Monthly Revenue:** ${new_stats.get('monthly_revenue', 0):.2f}\n" +
                      f"**🎯 Monthly Licenses:** {new_stats.get('monthly_licenses', 0)} licenses",
                inline=True
            )
            
            # Updated stock status
            new_stock_info = ""
            for product_id, product in PRODUCTS.items():
                key_count = await bot.db.get_key_count(product_id)
                stock_emoji = "✅" if key_count > 10 else "⚠️" if key_count > 0 else "❌"
                new_stock_info += f"{stock_emoji} {product['name']}: {key_count}\n"
            
            new_embed.add_field(
                name="📦 Stock Status",
                value=new_stock_info,
                inline=False
            )
            
            await button_interaction.response.edit_message(embed=new_embed, view=self)
    
    await interaction.response.send_message(embed=embed, view=AdminView(), ephemeral=True)

@bot.tree.command(name="addkeys", description="Add keys to specified product type (Admins only)")
@app_commands.describe(
    product_type="Product type to add keys to",
    keys="Keys to add (one per line)"
)
@app_commands.choices(product_type=[
    app_commands.Choice(name="🔥 Valorant LifeTime", value="vallifetime"),
    app_commands.Choice(name="⭐ Valorant 1 Month", value="val1month"),
    app_commands.Choice(name="🚀 Valorant 1 Week", value="val1week"),
    app_commands.Choice(name="🔥 Spoofer LifeTime", value="wooflifetime"),
    app_commands.Choice(name="⭐ Spoofer 1 Month", value="woof1month"),
    app_commands.Choice(name="🚀 Spoofer 1 Week", value="woof1week")
])
async def addkeys(interaction: discord.Interaction, product_type: str, keys: str):
    if interaction.user.id not in ADMIN_IDS:
        embed = create_embed("❌ Unauthorized Access", "Only admins can use this command.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Split keys into lines
    key_list = [key.strip() for key in keys.split('\n') if key.strip()]
    
    if not key_list:
        embed = create_embed("❌ Invalid Input", "Please enter at least one key.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Add keys
    added_count = 0
    duplicate_count = 0
    
    for key in key_list:
        success = await bot.db.add_key(product_type, key)
        if success:
            added_count += 1
        else:
            duplicate_count += 1
    
    # Admin log
    await bot.db.log_admin_action(
        interaction.user.id, "keys_added",
        None, None,
        f"Product: {product_type}, Added: {added_count}, Duplicates: {duplicate_count}"
    )
    
    embed = create_embed(
        "✅ Key Addition Complete",
        f"**Product:** {PRODUCTS[product_type]['name']}\n" +
        f"**Successfully Added:** {added_count} keys\n" +
        f"**Duplicate/Error:** {duplicate_count} keys\n" +
        f"**New Stock:** {await bot.db.get_key_count(product_type)} keys",
        COLORS['success']
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stock", description="View stock status of all products")
async def stock(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        embed = create_embed("❌ Unauthorized Access", "Only admins can use this command.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = create_embed("📦 Stock Status", "Current stock status of all products:", COLORS['info'])
    
    total_keys = 0
    
    # Valorant products
    val_stock = ""
    val_products = ['vallifetime', 'val1month', 'val1week']
    for product_id in val_products:
        if product_id in PRODUCTS:
            key_count = await bot.db.get_key_count(product_id)
            total_keys += key_count
            stock_emoji = "✅" if key_count > 10 else "⚠️" if key_count > 0 else "❌"
            val_stock += f"{stock_emoji} **{PRODUCTS[product_id]['name']}**\n📦 {key_count} keys available\n\n"
    
    embed.add_field(
        name="🎯 VALORANT PRODUCTS",
        value=val_stock,
        inline=True
    )
    
    # Spoofer products
    woof_stock = ""
    woof_products = ['wooflifetime', 'woof1month', 'woof1week']
    for product_id in woof_products:
        if product_id in PRODUCTS:
            key_count = await bot.db.get_key_count(product_id)
            total_keys += key_count
            stock_emoji = "✅" if key_count > 10 else "⚠️" if key_count > 0 else "❌"
            woof_stock += f"{stock_emoji} **{PRODUCTS[product_id]['name']}**\n📦 {key_count} keys available\n\n"
    
    embed.add_field(
        name="🛡️ SPOOFER PRODUCTS",
        value=woof_stock,
        inline=True
    )
    
    embed.add_field(
        name="📊 Total Summary",
        value=f"**🔑 Total Keys:** {total_keys}\n" +
              f"**📈 Product Varieties:** {len(PRODUCTS)}\n" +
              f"**⚡ Status:** {'Stock levels normal' if total_keys > 50 else 'Stock running low!' if total_keys > 0 else 'OUT OF STOCK!'}",
        inline=False
    )
    
    # Stock warning
    if total_keys == 0:
        embed.color = COLORS['error']
        embed.add_field(
            name="🚨 STOCK WARNING",
            value="**ALL STOCK DEPLETED!**\nKeys must be added urgently using `/addkeys` command.",
            inline=False
        )
    elif total_keys < 20:
        embed.color = COLORS['warning']
        embed.add_field(
            name="⚠️ Stock Warning",
            value="Stock levels are low! Consider adding new keys.",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="deletelicense", description="Delete specified license (Admins only)")
@app_commands.describe(
    license_id="License ID to delete",
    reason="Reason for deletion"
)
async def deletelicense(interaction: discord.Interaction, license_id: str, reason: str = "Deleted by admin"):
    if interaction.user.id not in ADMIN_IDS:
        embed = create_embed("❌ Unauthorized Access", "Only admins can use this command.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get license information
    license_data = await bot.db.get_license_by_id(license_id)
    
    if not license_data:
        embed = create_embed("❌ License Not Found", f"License with ID '{license_id}' not found.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Confirmation message
    embed = create_embed(
        "⚠️ License Deletion Confirmation",
        f"**License ID:** `{license_id}`\n" +
        f"**User:** <@{license_data['user_id']}>\n" +
        f"**Product:** {license_data['product_name'] or license_data['product_type']}\n" +
        f"**Reason:** {reason}\n\n" +
        "⚠️ **This action cannot be undone!** Key will be returned to stock.",
        COLORS['warning']
    )
    
    class DeleteConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label='✅ Delete', style=discord.ButtonStyle.danger)
        async def confirm_delete(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Only the command admin can perform this action.", ephemeral=True)
                return
            
            # Delete license
            success = await bot.db.delete_license(license_id, license_data['user_id'])
            
            if success:
                # Admin log
                await bot.db.log_admin_action(
                    interaction.user.id, "license_delete",
                    license_data['user_id'], license_id,
                    f"Reason: {reason}"
                )
                
                embed = create_embed(
                    "✅ License Deleted",
                    f"**License ID:** `{license_id}`\n" +
                    f"**User:** <@{license_data['user_id']}>\n" +
                    f"**Reason:** {reason}\n\n" +
                    "Key returned to stock.",
                    COLORS['success']
                )
                
                # Try to send DM to user
                try:
                    user = bot.get_user(license_data['user_id'])
                    if user:
                        dm_embed = create_embed(
                            "❌ Your License Has Been Cancelled",
                            f"**License ID:** `{license_id}`\n" +
                            f"**Product:** {license_data['product_name'] or license_data['product_type']}\n" +
                            f"**Reason:** {reason}\n\n" +
                            "Contact administrators for more information.",
                            COLORS['error']
                        )
                        await user.send(embed=dm_embed)
                except:
                    pass  # Ignore if DM fails
                
            else:
                embed = create_embed(
                    "❌ Deletion Failed",
                    "An error occurred while deleting the license.",
                    COLORS['error']
                )
            
            await button_interaction.response.edit_message(embed=embed, view=None)
        
        @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.secondary)
        async def cancel_delete(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Only the command admin can perform this action.", ephemeral=True)
                return
            
            embed = create_embed("❌ Operation Cancelled", "License deletion operation cancelled.", COLORS['info'])
            await button_interaction.response.edit_message(embed=embed, view=None)
    
    await interaction.response.send_message(embed=embed, view=DeleteConfirmView(), ephemeral=True)

@bot.tree.command(name="resethwid", description="Reset user's HWID (Admins only)")
@app_commands.describe(
    license_id="License ID to reset HWID for",
    reason="Reason for reset"
)
async def resethwid(interaction: discord.Interaction, license_id: str, reason: str = "Reset by admin"):
    if interaction.user.id not in ADMIN_IDS:
        embed = create_embed("❌ Unauthorized Access", "Only admins can use this command.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get license information
    license_data = await bot.db.get_license_by_id(license_id)
    
    if not license_data:
        embed = create_embed("❌ License Not Found", f"License with ID '{license_id}' not found.", COLORS['error'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Reset HWID
    success = await bot.db.reset_hwid(license_id, license_data['user_id'], reason)
    
    if success:
        # Admin log
        await bot.db.log_admin_action(
            interaction.user.id, "hwid_reset",
            license_data['user_id'], license_id,
            f"Reason: {reason}"
        )
        
        embed = create_embed(
            "✅ HWID Reset",
            f"**License ID:** `{license_id}`\n" +
            f"**User:** <@{license_data['user_id']}>\n" +
            f"**Product:** {license_data['product_name'] or license_data['product_type']}\n" +
            f"**Reason:** {reason}",
            COLORS['success']
        )
        
        # Try to send DM to user
        try:
            user = bot.get_user(license_data['user_id'])
            if user:
                dm_embed = create_embed(
                    "🔄 HWID Reset",
                    f"**License ID:** `{license_id}`\n" +
                    f"**Product:** {license_data['product_name'] or license_data['product_type']}\n" +
                    f"**Reason:** {reason}\n\n" +
                    "You can now use your license on a new device.",
                    COLORS['info']
                )
                await user.send(embed=dm_embed)
        except:
            pass  # Ignore if DM fails
        
    else:
        embed = create_embed(
            "❌ HWID Reset Failed",
            "An error occurred while resetting HWID.",
            COLORS['error']
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="debug", description="Check system status (Admins only)")
async def debug(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ Unauthorized access", ephemeral=True)
        return
    
    try:
        # Test database connection
        async with aiosqlite.connect(bot.db.db_path) as db:
            # List tables
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = await cursor.fetchall()
            table_list = [table[0] for table in tables]
            
            # User count
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM users")
                user_count = (await cursor.fetchone())[0]
            except:
                user_count = "Error"
            
            # License count
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM licenses")
                license_count = (await cursor.fetchone())[0]
            except:
                license_count = "Error"
        
        # Check key files
        key_files_status = ""
        for product_type, config in KEYS_CONFIG.items():
            file_exists = os.path.exists(config['file'])
            key_count = await bot.db.get_key_count(product_type)
            status_emoji = "✅" if file_exists else "❌"
            key_files_status += f"{status_emoji} {config['file']}: {key_count} keys\n"
        
        embed = create_embed(
            "🔧 System Debug",
            f"**📋 Tables:** {', '.join(table_list)}\n" +
            f"**👥 Users:** {user_count}\n" +
            f"**🔑 Licenses:** {license_count}\n" +
            f"**📁 DB File:** {os.path.exists(bot.db.db_path)}\n" +
            f"**📂 Keys Folder:** {os.path.exists('keys')}",
            COLORS['info']
        )
        
        embed.add_field(
            name="📄 Key Files",
            value=key_files_status,
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Debug error: {e}", ephemeral=True)

# Run the bot
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
