"""
Supabase Database Client for KlingBot.
Handles all database operations including users, generations, and subscriptions.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)


class Database:
    """Database client for Supabase operations."""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    
    def _first(self, data: List[Dict]) -> Optional[Dict]:
        """Get first item from list or None."""
        return data[0] if data else None
    
    # ==================== USERS ====================
    
    def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
        is_premium: bool = False,
        ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing user or create new one.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            language_code: User's language code (ru/en)
            is_premium: Whether user has Telegram Premium
            ref: Referral code (partner's username)
        
        Returns:
            User data dictionary
        """
        try:
            # Check if user exists
            result = self.client.table("users").select("*").eq("user_id", user_id).execute()
            existing = self._first(result.data)
            
            if existing:
                # Update user info if changed
                update_data = {}
                if username and existing.get("username") != username:
                    update_data["username"] = username
                if first_name and existing.get("first_name") != first_name:
                    update_data["first_name"] = first_name
                if last_name and existing.get("last_name") != last_name:
                    update_data["last_name"] = last_name
                if is_premium != existing.get("is_premium"):
                    update_data["is_premium"] = is_premium
                
                if update_data:
                    update_data["updated_at"] = datetime.utcnow().isoformat()
                    self.client.table("users").update(update_data).eq("user_id", user_id).execute()
                
                return existing
            
            # Create new user
            # Process referral code: extract username from ref_<username> format
            ref_username = None
            if ref:
                if ref.startswith("ref_"):
                    ref_username = ref[4:]  # Remove 'ref_' prefix
                else:
                    ref_username = ref
            
            payload = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "language_code": language_code or "ru",
                "is_premium": is_premium,
                "ref": ref_username,
                "balance": 6  # Default starting balance
            }
            
            created = self.client.table("users").insert(payload).execute()
            logger.info(f"Created new user: {user_id} (ref: {ref_username})")
            return self._first(created.data) or payload
            
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            raise
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            result = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return self._first(result.data)
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def update_user_balance(self, user_id: int, amount: int) -> bool:
        """
        Update user balance by amount (can be negative for deduction).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            user = self.get_user(user_id)
            if not user:
                return False
            
            new_balance = user.get("balance", 0) + amount
            if new_balance < 0:
                return False  # Insufficient balance
            
            self.client.table("users").update({
                "balance": new_balance,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error updating balance for {user_id}: {e}")
            return False
    
    def deduct_balance(self, user_id: int, amount: int) -> bool:
        """Deduct balance from user. Returns True if successful."""
        return self.update_user_balance(user_id, -amount)
    
    # ==================== BOT SUBSCRIPTIONS ====================
    
    def ensure_bot_subscription(self, user_id: int, bot_source: str) -> None:
        """
        Ensure user is subscribed to this bot (for tracking and broadcasts).
        Uses upsert to avoid duplicates.
        """
        try:
            payload = {
                "user_id": int(user_id),
                "bot_source": str(bot_source)
            }
            self.client.table("bot_subscriptions").upsert(
                payload,
                on_conflict="user_id,bot_source"
            ).execute()
        except Exception as e:
            logger.error(f"Error saving bot subscription: {e}")
    
    # ==================== GENERATIONS ====================
    
    def create_generation(
        self,
        user_id: int,
        prompt: str,
        model: str,
        provider_task_id: str,
        cost: int,
        media_type: str = "video",
        input_images: Optional[List[str]] = None,
        video_duration: Optional[float] = None,
        video_resolution: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new generation record.
        
        Args:
            user_id: Telegram user ID
            prompt: Generation prompt
            model: Model name (e.g., 'kling-2.6/text-to-video')
            provider_task_id: Task ID from Kling API
            cost: Cost in tokens
            media_type: Type of media ('video')
            input_images: List of input image URLs
            video_duration: Duration in seconds
            video_resolution: Resolution (e.g., '720p', '1080p')
        
        Returns:
            Created generation record
        """
        try:
            payload = {
                "user_id": user_id,
                "prompt": prompt,
                "model": model,
                "provider_task_id": provider_task_id,
                "cost": cost,
                "status": "pending",
                "media_type": media_type,
                "input_images": input_images,
                "video_duration": video_duration,
                "video_resolution": video_resolution
            }
            
            result = self.client.table("generations").insert(payload).execute()
            return self._first(result.data)
        except Exception as e:
            logger.error(f"Error creating generation: {e}")
            return None
    
    def update_generation(
        self,
        generation_id: int,
        status: str,
        video_url: Optional[str] = None,
        error_message: Optional[str] = None,
        provider_task_id: Optional[str] = None
    ) -> bool:
        """Update generation status and result."""
        try:
            update_data = {
                "status": status,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            if video_url:
                update_data["video_url"] = video_url
            if error_message:
                update_data["error_message"] = error_message
            if provider_task_id:
                update_data["provider_task_id"] = provider_task_id
            
            self.client.table("generations").update(update_data).eq("id", generation_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating generation {generation_id}: {e}")
            return False
    
    def get_generation_by_task_id(self, provider_task_id: str) -> Optional[Dict[str, Any]]:
        """Get generation by provider task ID."""
        try:
            result = self.client.table("generations").select("*").eq("provider_task_id", provider_task_id).execute()
            return self._first(result.data)
        except Exception as e:
            logger.error(f"Error getting generation by task ID {provider_task_id}: {e}")
            return None
    
    def get_user_generations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent generations."""
        try:
            result = self.client.table("generations")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting generations for user {user_id}: {e}")
            return []


# Global database instance
db = Database()
