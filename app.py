import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import config

# Create required directories
os.makedirs("logs", exist_ok=True)
os.makedirs("receipts", exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def main():
    """Main bot entry point"""
    try:
        # Import handlers
        from handlers import (
            user_handlers,
            admin_handlers,
            plan_handlers,
            purchase_handlers,
            support_handlers,
            config_handlers,
            bank_handlers,
            settings_handlers
        )
        
        # Import middleware
        from middlewares.middlewares import CheckMembershipMiddleware
        
        # Register routers
        dp.include_router(user_handlers.router)
        dp.include_router(admin_handlers.router)
        dp.include_router(plan_handlers.router)
        dp.include_router(purchase_handlers.router)
        dp.include_router(support_handlers.router)
        dp.include_router(config_handlers.router)
        dp.include_router(bank_handlers.router)
        dp.include_router(settings_handlers.router)
        
        # Register middleware - اینجا مهم است
        dp.message.middleware(CheckMembershipMiddleware())
        dp.callback_query.middleware(CheckMembershipMiddleware())
        
        # Initialize database
        from database.database import init_db
        await init_db()
        
        logger.info("Bot started successfully!")
        
        # Start polling
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")