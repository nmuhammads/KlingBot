"""
Start handler for KlingBot.
Handles /start command, user registration, referrals, and subscriptions.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import db
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router()


def get_main_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Create main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_generate", lang))],
            [
                KeyboardButton(text=t("btn_profile", lang)),
                KeyboardButton(text=t("btn_topup", lang))
            ]
        ],
        resize_keyboard=True
    )


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    """
    Handle /start command.
    
    - Creates or retrieves user
    - Stores referral code if provided
    - Records bot subscription
    - Shows welcome message
    """
    logger.info(f"Received /start from user {message.from_user.id}")
    
    user = message.from_user
    args = command.args  # Referral code from deep link
    
    try:
        # Get or create user with referral
        db_user = db.get_or_create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
            is_premium=user.is_premium or False,
            ref=args  # Will be processed (ref_username -> username)
        )
        logger.info(f"User {user.id} retrieved/created successfully")
    except Exception as e:
        logger.error(f"Error creating/retrieving user: {e}", exc_info=True)
        db_user = {"balance": 0, "language_code": "ru"}
    
    # Record bot subscription for this user
    try:
        bot_me = await message.bot.get_me()
        bot_source = getattr(bot_me, "username", None)
        if bot_source:
            db.ensure_bot_subscription(int(user.id), str(bot_source))
    except Exception as e:
        logger.error(f"Error recording bot subscription: {e}")
    
    # Determine user language
    lang = db_user.get("language_code", "ru") or "ru"
    if lang not in ("ru", "en"):
        lang = "ru"
    
    # Get balance
    balance = db_user.get("balance", 0)
    
    # Send welcome message
    try:
        await message.answer(
            t("welcome", lang, balance=balance),
            reply_markup=get_main_keyboard(lang)
        )
        logger.info(f"Welcome message sent to user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}", exc_info=True)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    user = db.get_user(message.from_user.id)
    lang = user.get("language_code", "ru") if user else "ru"
    
    await message.answer(t("help", lang))


@router.message(Command("lang"))
async def cmd_lang(message: Message) -> None:
    """Handle /lang command - language selection."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
        ]
    ])
    
    await message.answer(t("lang_select", "ru"), reply_markup=keyboard)


@router.callback_query(F.data.startswith("lang_"))
async def callback_lang(callback) -> None:
    """Handle language selection callback."""
    lang = callback.data.split("_")[1]
    
    # Update user language in database
    try:
        db.client.table("users").update({
            "language_code": lang
        }).eq("user_id", callback.from_user.id).execute()
    except Exception as e:
        logger.error(f"Error updating language: {e}")
    
    await callback.message.edit_text(t("lang_changed", lang))
    await callback.answer()


# Handle main menu button presses
@router.message(F.text.in_([t("btn_generate", "ru"), t("btn_generate", "en")]))
async def btn_generate_pressed(message: Message) -> None:
    """Redirect to generate handler."""
    from handlers.generate import show_mode_selection
    await show_mode_selection(message)


@router.message(F.text.in_([t("btn_profile", "ru"), t("btn_profile", "en")]))
async def btn_profile_pressed(message: Message) -> None:
    """Redirect to profile handler."""
    from handlers.profile import cmd_profile
    await cmd_profile(message)


@router.message(F.text.in_([t("btn_topup", "ru"), t("btn_topup", "en")]))
async def btn_topup_pressed(message: Message) -> None:
    """Redirect to topup handler."""
    from handlers.topup import cmd_topup
    await cmd_topup(message)
