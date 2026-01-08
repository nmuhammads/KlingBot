"""
Kling API Client for KlingBot.
Handles all interactions with the kie.ai Kling API.
"""

import logging
from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum

import httpx

from config import settings

logger = logging.getLogger(__name__)


class KlingModel(str, Enum):
    """Available Kling models."""
    TEXT_TO_VIDEO = "kling-2.6/text-to-video"
    IMAGE_TO_VIDEO = "kling-2.6/image-to-video"
    MOTION_CONTROL = "kling-2.6/motion-control"


class TaskState(str, Enum):
    """Task states from Kling API."""
    WAITING = "waiting"
    SUCCESS = "success"
    FAIL = "fail"


@dataclass
class KlingPricing:
    """Pricing configuration for Kling generations."""
    
    # T2V / I2V pricing (flat rate per generation)
    T2V_I2V_5S_NO_AUDIO = 55
    T2V_I2V_10S_NO_AUDIO = 110
    T2V_I2V_5S_WITH_AUDIO = 110
    T2V_I2V_10S_WITH_AUDIO = 220
    
    # Motion Control pricing (per second, min 5s)
    MC_720P_PER_SEC = 6
    MC_1080P_PER_SEC = 9
    MC_MIN_DURATION = 5
    
    @classmethod
    def get_t2v_i2v_price(cls, duration: int, with_audio: bool) -> int:
        """Get price for Text-to-Video or Image-to-Video."""
        if duration == 5:
            return cls.T2V_I2V_5S_WITH_AUDIO if with_audio else cls.T2V_I2V_5S_NO_AUDIO
        elif duration == 10:
            return cls.T2V_I2V_10S_WITH_AUDIO if with_audio else cls.T2V_I2V_10S_NO_AUDIO
        else:
            # Default to 5s pricing
            return cls.T2V_I2V_5S_WITH_AUDIO if with_audio else cls.T2V_I2V_5S_NO_AUDIO
    
    @classmethod
    def get_motion_control_price(cls, duration: int, mode: str) -> int:
        """
        Get price for Motion Control.
        
        Args:
            duration: Video duration in seconds (min 5s charged)
            mode: '720p' or '1080p'
        
        Returns:
            Price in tokens
        """
        effective_duration = max(cls.MC_MIN_DURATION, duration)
        price_per_sec = cls.MC_1080P_PER_SEC if mode == "1080p" else cls.MC_720P_PER_SEC
        return effective_duration * price_per_sec


class KlingClient:
    """Client for interacting with Kling API (kie.ai)."""
    
    def __init__(self):
        self.base_url = settings.kling_api_base_url
        self.api_key = settings.kling_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Kling API."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=json_data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from Kling API: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error making request to Kling API: {e}")
                raise
    
    async def create_text_to_video(
        self,
        prompt: str,
        duration: Literal["5", "10"] = "5",
        aspect_ratio: Literal["1:1", "16:9", "9:16"] = "16:9",
        sound: bool = False,
        callback_url: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Text-to-Video generation task.
        
        Args:
            prompt: Text prompt for video generation (max 2500 chars)
            duration: Video duration ('5' or '10' seconds)
            aspect_ratio: Aspect ratio ('1:1', '16:9', '9:16')
            sound: Whether to generate video with audio
            callback_url: Optional URL for completion callback
            meta: Optional metadata for tracking (generationId, tokens, userId)
        
        Returns:
            API response with taskId
        """
        payload = {
            "model": KlingModel.TEXT_TO_VIDEO.value,
            "input": {
                "prompt": prompt[:2500],
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "sound": sound
            }
        }
        
        if callback_url:
            payload["callBackUrl"] = callback_url
        
        if meta:
            payload["meta"] = meta
        
        logger.info(f"Creating T2V task: duration={duration}, aspect_ratio={aspect_ratio}, sound={sound}, meta={meta}")
        return await self._make_request("POST", "/jobs/createTask", json_data=payload)
    
    async def create_image_to_video(
        self,
        image_url: str,
        prompt: str = "",
        duration: Literal["5", "10"] = "5",
        sound: bool = False,
        callback_url: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an Image-to-Video generation task.
        
        Args:
            image_url: URL of the input image
            prompt: Text prompt for video generation (max 2500 chars)
            duration: Video duration ('5' or '10' seconds)
            sound: Whether to generate video with audio
            callback_url: Optional URL for completion callback
            meta: Optional metadata for tracking (generationId, tokens, userId)
        
        Returns:
            API response with taskId
        """
        payload = {
            "model": KlingModel.IMAGE_TO_VIDEO.value,
            "input": {
                "prompt": prompt[:2500] if prompt else "",
                "image_urls": [image_url],
                "duration": duration,
                "sound": sound
            }
        }
        
        if callback_url:
            payload["callBackUrl"] = callback_url
        
        if meta:
            payload["meta"] = meta
        
        logger.info(f"Creating I2V task: duration={duration}, sound={sound}, meta={meta}")
        return await self._make_request("POST", "/jobs/createTask", json_data=payload)
    
    async def create_motion_control(
        self,
        input_image_url: str,
        video_url: str,
        prompt: str = "",
        character_orientation: Literal["image", "video"] = "video",
        mode: Literal["720p", "1080p"] = "720p",
        callback_url: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Motion Control generation task.
        
        Args:
            input_image_url: URL of the source image (subject)
            video_url: URL of the reference video (3-30 seconds)
            prompt: Optional text prompt (max 2500 chars)
            character_orientation: 'image' or 'video' orientation
            mode: Output resolution ('720p' or '1080p')
            callback_url: Optional URL for completion callback
            meta: Optional metadata for tracking (generationId, tokens, userId)
        
        Returns:
            API response with taskId
        """
        payload = {
            "model": KlingModel.MOTION_CONTROL.value,
            "input": {
                "prompt": prompt[:2500] if prompt else "",
                "input_urls": [input_image_url],
                "video_urls": [video_url],
                "character_orientation": character_orientation,
                "mode": mode
            }
        }
        
        if callback_url:
            payload["callBackUrl"] = callback_url
        
        if meta:
            payload["meta"] = meta
        
        logger.info(f"Creating Motion Control task: orientation={character_orientation}, mode={mode}, meta={meta}")
        return await self._make_request("POST", "/jobs/createTask", json_data=payload)
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Query task status and results.
        
        Args:
            task_id: Task ID from create task response
        
        Returns:
            Task status and results
        """
        return await self._make_request("GET", "/jobs/recordInfo", params={"taskId": task_id})
    
    def parse_task_result(self, response: Dict[str, Any]) -> Optional[List[str]]:
        """
        Parse result URLs from task status response.
        
        Args:
            response: Response from get_task_status
        
        Returns:
            List of result URLs or None if not ready
        """
        try:
            data = response.get("data", {})
            state = data.get("state")
            
            if state != TaskState.SUCCESS.value:
                return None
            
            result_json = data.get("resultJson", "{}")
            if isinstance(result_json, str):
                import json
                result_data = json.loads(result_json)
            else:
                result_data = result_json
            
            return result_data.get("resultUrls", [])
        except Exception as e:
            logger.error(f"Error parsing task result: {e}")
            return None


# Global Kling client instance
kling_client = KlingClient()
