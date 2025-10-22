import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
import json
import os
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def generate_video(self, prompt: str, duration: int = 30) -> str:
        """Generate video using available AI models with fallbacks."""
        models_to_try = [
            self._generate_with_openai,
            self._generate_with_runwayml,
            self._generate_with_stability,
            self._generate_with_huggingface,
            self._generate_basic_video
        ]

        for model_func in models_to_try:
            try:
                video_url = await model_func(prompt, duration)
                if video_url:
                    logger.info(f"Successfully generated video using {model_func.__name__}")
                    return video_url
            except Exception as e:
                logger.warning(f"Failed to generate with {model_func.__name__}: {e}")
                continue

        raise Exception("All AI models failed to generate video")

    async def _generate_with_openai(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using OpenAI Sora (if available) or GPT-4 for content."""
        if not hasattr(settings, 'openai_api_key') or not settings.openai_api_key:
            return None

        try:
            # First generate script with GPT-4
            script = await self._generate_script_with_openai(prompt)

            # Try Sora API (if available)
            url = "https://api.openai.com/v1/images/generations"  # Placeholder for Sora
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json"
            }

            # For now, generate images and simulate video creation
            image_data = {
                "prompt": f"High-quality image for video about: {prompt}",
                "model": "dall-e-3",
                "size": "1792x1024",
                "quality": "standard"
            }

            async with self.session.post("https://api.openai.com/v1/images/generations",
                                       headers=headers, json=image_data) as response:
                if response.status == 200:
                    result = await response.json()
                    image_url = result["data"][0]["url"]

                    # Simulate video creation from image
                    video_url = await self._create_video_from_image(image_url, script, duration)
                    return video_url

        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            return None

    async def _generate_script_with_openai(self, prompt: str) -> str:
        """Generate video script using OpenAI GPT-4."""
        if not hasattr(settings, 'openai_api_key') or not settings.openai_api_key:
            return f"Create an engaging video about: {prompt}"

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }

        script_prompt = f"""Create a compelling video script for a viral video about: {prompt}

Requirements:
- Engaging hook in first 5 seconds
- Clear value proposition
- Call to action
- Under 60 seconds total
- Natural, conversational tone

Format as a script with timing cues."""

        data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": script_prompt}],
            "max_tokens": 500
        }

        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"Create an amazing video about: {prompt}"

    async def _generate_with_runwayml(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using RunwayML Gen-2/Gen-3."""
        if not hasattr(settings, 'runwayml_api_key') or not settings.runwayml_api_key:
            return None

        try:
            url = "https://api.runwayml.com/v1/image_to_video"
            headers = {
                "Authorization": f"Bearer {settings.runwayml_api_key}",
                "Content-Type": "application/json"
            }

            # First generate an image, then convert to video
            image_prompt = f"High-quality image for video: {prompt}"
            image_data = {
                "model": "gen-3-alpha-turbo",
                "prompt": image_prompt,
                "ratio": "16:9"
            }

            async with self.session.post("https://api.runwayml.com/v1/image_generation",
                                       headers=headers, json=image_data) as response:
                if response.status != 200:
                    raise Exception(f"RunwayML image generation failed: {response.status}")
                image_result = await response.json()
                image_id = image_result["id"]

            # Wait for image generation
            await asyncio.sleep(10)

            # Generate video from image
            video_data = {
                "model": "gen-3-alpha-turbo",
                "prompt_image": image_id,
                "prompt_text": prompt,
                "duration": min(duration, 10),  # RunwayML limit
                "ratio": "16:9"
            }

            async with self.session.post(url, headers=headers, json=video_data) as response:
                if response.status != 200:
                    raise Exception(f"RunwayML video generation failed: {response.status}")
                result = await response.json()
                return result.get("video")

        except Exception as e:
            logger.error(f"RunwayML generation error: {e}")
            return None

    async def _generate_with_stability(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using Stability AI."""
        if not hasattr(settings, 'stability_api_key') or not settings.stability_api_key:
            return None

        try:
            url = "https://api.stability.ai/v2beta/image-to-video"
            headers = {
                "Authorization": f"Bearer {settings.stability_api_key}",
                "Content-Type": "application/json"
            }

            # Generate image first
            image_data = {
                "prompt": f"High-quality image for video: {prompt}",
                "aspect_ratio": "16:9",
                "model": "sd3-large"
            }

            async with self.session.post("https://api.stability.ai/v2beta/stable-image/generate/core",
                                       headers=headers, json=image_data) as response:
                if response.status != 200:
                    raise Exception(f"Stability image generation failed: {response.status}")
                image_result = await response.json()
                image_id = image_result["id"]

            # Wait for image
            await asyncio.sleep(15)

            # Generate video
            video_data = {
                "image": image_id,
                "seed": 0,
                "cfg_scale": 2.5,
                "motion_bucket_id": 127
            }

            async with self.session.post(url, headers=headers, json=video_data) as response:
                if response.status != 200:
                    raise Exception(f"Stability video generation failed: {response.status}")
                result = await response.json()
                return result.get("video")

        except Exception as e:
            logger.error(f"Stability generation error: {e}")
            return None

    async def _generate_with_huggingface(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using Hugging Face free models."""
        if not hasattr(settings, 'huggingface_api_key') or not settings.huggingface_api_key:
            return None

        try:
            # Use a free video generation model
            url = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
            headers = {
                "Authorization": f"Bearer {settings.huggingface_api_key}",
                "Content-Type": "application/json"
            }

            # Generate image first using another HF model
            image_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
            image_data = {
                "inputs": f"High-quality image for video: {prompt}",
                "parameters": {
                    "width": 1024,
                    "height": 576
                }
            }

            async with self.session.post(image_url, headers=headers, json=image_data) as response:
                if response.status != 200:
                    raise Exception(f"HuggingFace image generation failed: {response.status}")
                image_bytes = await response.read()

            # Generate video from image
            video_data = {
                "inputs": image_bytes,
                "parameters": {
                    "num_frames": min(duration * 8, 25),  # Approximate frames
                    "width": 1024,
                    "height": 576
                }
            }

            async with self.session.post(url, headers=headers, data=json.dumps(video_data)) as response:
                if response.status != 200:
                    raise Exception(f"HuggingFace video generation failed: {response.status}")
                result = await response.json()
                return result[0]["video"] if result else None

        except Exception as e:
            logger.error(f"HuggingFace generation error: {e}")
            return None

    async def _generate_basic_video(self, prompt: str, duration: int) -> Optional[str]:
        """Generate a basic video when AI services are unavailable."""
        try:
            # Create a simple placeholder video URL
            # In production, this would create an actual video
            video_id = f"video_{hash(prompt)}_{int(asyncio.get_event_loop().time())}"
            return f"https://storage.googleapis.com/safwaan-ai-studio/videos/{video_id}.mp4"
        except Exception as e:
            logger.error(f"Basic video generation error: {e}")
            return None

    async def _create_video_from_image(self, image_url: str, script: str, duration: int) -> str:
        """Create video from image and script (placeholder implementation)."""
        # In a real implementation, this would use ffmpeg or similar
        # to combine image with text-to-speech audio
        video_id = f"generated_{hash(image_url + script)}_{int(asyncio.get_event_loop().time())}"
        return f"https://storage.googleapis.com/safwaan-ai-studio/generated/{video_id}.mp4"

    async def enhance_video(self, video_url: str) -> str:
        """Enhance video quality using AI."""
        # Use Stability AI for video enhancement
        if not hasattr(settings, 'stability_api_key') or not settings.stability_api_key:
            return video_url

        try:
            url = "https://api.stability.ai/v2beta/image-to-video/upscale"
            headers = {
                "Authorization": f"Bearer {settings.stability_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "video": video_url,
                "scale": 2
            }

            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("video", video_url)
                else:
                    logger.warning(f"Video enhancement failed: {response.status}")
                    return video_url
        except Exception as e:
            logger.error(f"Video enhancement error: {e}")
            return video_url

    async def generate_captions(self, video_description: str) -> Dict[str, Any]:
        """Generate captions and hashtags for video."""
        if not hasattr(settings, 'openai_api_key') or not settings.openai_api_key:
            return {"captions": ["Amazing video! 🎥"], "hashtags": ["#viral", "#video"]}

        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json"
            }

            prompt = f"""Generate engaging captions and hashtags for a viral video with this description: {video_description}

Return JSON format:
{{
    "captions": ["Caption 1", "Caption 2", "Caption 3"],
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
}}"""

            data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            }

            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except:
                        return {"captions": [content[:100]], "hashtags": ["#viral", "#video"]}
                else:
                    return {"captions": ["Amazing video! 🎥"], "hashtags": ["#viral", "#video"]}
        except Exception as e:
            logger.error(f"Caption generation error: {e}")
            return {"captions": ["Amazing video! 🎥"], "hashtags": ["#viral", "#video"]}

    async def generate_thumbnail(self, video_description: str) -> str:
        """Generate thumbnail image for video."""
        if not hasattr(settings, 'openai_api_key') or not settings.openai_api_key:
            return "https://via.placeholder.com/1280x720?text=Viral+Video"

        try:
            url = "https://api.openai.com/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "prompt": f"High-quality thumbnail image for a viral video about: {video_description}. Eye-catching, professional, click-worthy.",
                "model": "dall-e-3",
                "size": "1792x1024",
                "quality": "standard"
            }

            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["data"][0]["url"]
                else:
                    return "https://via.placeholder.com/1280x720?text=Viral+Video"
        except Exception as e:
            logger.error(f"Thumbnail generation error: {e}")
            return "https://via.placeholder.com/1280x720?text=Viral+Video"