"""
Top-up handler for KlingBot.
Handles /topup command and payment integration with Hub Bot.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import settings
from database import db
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router()


def make_hub_link(method: str, amount: int) -> str:
    """
    Generate deep link to Hub Bot for payment.
    
    Args:
        method: Payment method ('stars', 'sbp', 'card')
        amount: Amount to top up
    
    Returns:
        Deep link URL
    """
    if method == "stars":
        payload = f"pay-{amount}"
    elif method == "sbp":
        payload = f"pay-sbp-{amount}"
    elif method == "card":
        payload = f"pay-card-{amount}"
    else:
        payload = f"pay-{amount}"
    
    return f"https://t.me/{settings.hub_bot_username}?start={payload}"


@router.message(Command("topup"))
async def cmd_topup(message: Message) -> None:
    """Handle /topup command - show payment methods."""
    user = db.get_user(message.from_user.id)
    lang = user.get("language_code", "ru") if user else "ru"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_stars", lang), callback_data="topup_method_stars")],
        [InlineKeyboardButton(text=t("btn_sbp", lang), callback_data="topup_method_sbp")],
        [InlineKeyboardButton(text=t("btn_card", lang), callback_data="topup_method_card")]
    ])
    
    await message.answer(t("topup_method", lang), reply_markup=keyboard)


@router.callback_query(F.data.startswith("topup_method_"))
async def callback_topup_method(callback) -> None:
    """Handle payment method selection."""
    method = callback.data.split("_")[2]  # stars, sbp, card
    
    user = db.get_user(callback.from_user.id)
    lang = user.get("language_code", "ru") if user else "ru"
    
    # Get allowed amounts based on method
    if method == "stars":
        amounts = settings.allowed_star_amounts
    else:
        amounts = settings.allowed_amounts
    
    # Create buttons with amounts
    buttons = []
    for amount in amounts:
        url = make_hub_link(method, amount)
        buttons.append([InlineKeyboardButton(text=f"💰 {amount} 🪙", url=url)])
    
    buttons.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="topup_back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(t("topup_amount", lang), reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "topup_back")
async def callback_topup_back(callback) -> None:
    """Handle back button in topup flow."""
    user = db.get_user(callback.from_user.id)
    lang = user.get("language_code", "ru") if user else "ru"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_stars", lang), callback_data="topup_method_stars")],
        [InlineKeyboardButton(text=t("btn_sbp", lang), callback_data="topup_method_sbp")],
        [InlineKeyboardButton(text=t("btn_card", lang), callback_data="topup_method_card")]
    ])
    
    await callback.message.edit_text(t("topup_method", lang), reply_markup=keyboard)
    await callback.answer()
