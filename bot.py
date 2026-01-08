"""
Bot initialization module.
Creates and configures the Aiogram Bot and Dispatcher instances.
"""

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings

# Initialize bot with default properties
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Initialize dispatcher with memory storage for FSM
dp = Dispatcher(storage=MemoryStorage())

