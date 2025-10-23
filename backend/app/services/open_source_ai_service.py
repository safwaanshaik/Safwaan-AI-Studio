import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiohttp
import os
from pathlib import Path
import torch
from diffusers import StableDiffusionPipeline, StableDiffusionImg2ImgPipeline, StableDiffusionInpaintPipeline
from transformers import pipeline as hf_pipeline, AutoTokenizer, AutoModelForCausalLM
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip
import edge_tts
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class OpenSourceAIService:
    """Open-source AI service with multiple free models and fallbacks."""

    def __init__(self):
        self.session = None
        self.models_loaded = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self._unload_all_models()

    async def generate_video(self, prompt: str, duration: int = 30) -> str:
        """Generate video using open-source AI models."""
        try:
            # Try multiple model combinations in order of preference
            generation_methods = [
                self._generate_with_stable_diffusion_and_llm,
                self._generate_with_huggingface_models,
                self._generate_with_replicate_api,
                self._generate_with_runpod_api,
                self._generate_fallback_video
            ]

            for method in generation_methods:
                try:
                    video_url = await method(prompt, duration)
                    if video_url:
                        logger.info(f"Successfully generated video using {method.__name__}")
                        return video_url
                except Exception as e:
                    logger.warning(f"Failed with {method.__name__}: {e}")
                    continue

            raise Exception("All open-source AI models failed")

        except Exception as e:
            logger.error(f"Open-source video generation failed: {e}")
            raise

    async def _generate_with_stable_diffusion_and_llm(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using Stable Diffusion + open-source LLM."""
        try:
            # Generate script with open-source LLM
            script = await self._generate_script_with_llm(prompt)

            # Generate images with Stable Diffusion
            images = await self._generate_images_stable_diffusion(script, duration)

            # Generate voiceover
            audio_path = await self._generate_voiceover_edge_tts(script)

            # Create video
            video_path = await self._create_video_moviepy(images, audio_path, duration)

            return video_path

        except Exception as e:
            logger.error(f"Stable Diffusion + LLM generation failed: {e}")
            return None

    async def _generate_with_huggingface_models(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using Hugging Face models."""
        try:
            # Use free Hugging Face models
            script = await self._generate_script_huggingface(prompt)
            images = await self._generate_images_huggingface(prompt, duration)
            audio_path = await self._generate_voiceover_coqui(script)
            video_path = await self._create_video_opencv(images, audio_path, duration)

            return video_path

        except Exception as e:
            logger.error(f"Hugging Face generation failed: {e}")
            return None

    async def _generate_with_replicate_api(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using Replicate API (has free tier)."""
        if not getattr(settings, 'replicate_api_key', None):
            return None

        try:
            url = "https://api.replicate.com/v1/predictions"
            headers = {
                "Authorization": f"Token {settings.replicate_api_key}",
                "Content-Type": "application/json"
            }

            # Use a free or low-cost model
            data = {
                "version": "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
                "input": {
                    "prompt": f"Cinematic video still: {prompt}",
                    "width": 1024,
                    "height": 576,
                    "num_outputs": duration // 3  # One image per 3 seconds
                }
            }

            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status != 201:
                    return None

                result = await response.json()
                prediction_id = result["id"]

                # Wait for completion
                for _ in range(30):  # Max 5 minutes
                    await asyncio.sleep(10)

                    status_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
                    async with self.session.get(status_url, headers=headers) as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            if status_data["status"] == "succeeded":
                                # Download images and create video
                                return await self._create_video_from_replicate(status_data["output"], prompt, duration)

                return None

        except Exception as e:
            logger.error(f"Replicate generation failed: {e}")
            return None

    async def _generate_with_runpod_api(self, prompt: str, duration: int) -> Optional[str]:
        """Generate video using RunPod API (GPU instances)."""
        if not getattr(settings, 'runpod_api_key', None):
            return None

        try:
            # RunPod API for GPU-accelerated generation
            url = "https://api.runpod.ai/v2/stable-diffusion/runsync"
            headers = {
                "Authorization": f"Bearer {settings.runpod_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "input": {
                    "prompt": f"Professional cinematic scene: {prompt}",
                    "width": 1024,
                    "height": 576,
                    "num_images": duration // 3,
                    "steps": 20,
                    "guidance_scale": 7.5
                }
            }

            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    images = result.get("output", [])
                    return await self._create_video_from_images(images, prompt, duration)

                return None

        except Exception as e:
            logger.error(f"RunPod generation failed: {e}")
            return None

    async def _generate_fallback_video(self, prompt: str, duration: int) -> Optional[str]:
        """Generate a basic fallback video."""
        try:
            # Create a simple animated text video
            output_dir = Path("/tmp/videos")
            output_dir.mkdir(exist_ok=True)
            video_path = output_dir / f"fallback_{int(asyncio.get_event_loop().time())}.mp4"

            # Create text clips
            words = prompt.split()
            clips = []

            for i, word in enumerate(words[:10]):  # Limit to 10 words
                txt_clip = TextClip(
                    word,
                    fontsize=70,
                    color='white',
                    bg_color='black',
                    size=(1920, 1080)
                ).set_duration(1.0)
                clips.append(txt_clip)

            # Concatenate and add background music if available
            video_clip = CompositeVideoClip(clips)

            # Write video
            video_clip.write_videofile(
                str(video_path),
                fps=24,
                codec="libx264",
                verbose=False,
                logger=None
            )

            return str(video_path)

        except Exception as e:
            logger.error(f"Fallback video generation failed: {e}")
            return None

    async def _generate_script_with_llm(self, prompt: str) -> str:
        """Generate script using open-source LLM."""
        try:
            # Try different open-source models
            models_to_try = [
                "microsoft/DialoGPT-medium",  # Conversational
                "distilgpt2",  # Lightweight GPT-2
                "gpt2"  # Full GPT-2
            ]

            for model_name in models_to_try:
                try:
                    if model_name not in self.models_loaded:
                        tokenizer = AutoTokenizer.from_pretrained(model_name)
                        model = AutoModelForCausalLM.from_pretrained(model_name)
                        self.models_loaded[model_name] = (tokenizer, model)

                    tokenizer, model = self.models_loaded[model_name]
                    model.to(self.device)

                    input_text = f"Write a viral video script about: {prompt}\nScript:"
                    inputs = tokenizer(input_text, return_tensors="pt").to(self.device)

                    with torch.no_grad():
                        outputs = model.generate(
                            inputs.input_ids,
                            max_length=200,
                            num_return_sequences=1,
                            temperature=0.8,
                            do_sample=True,
                            pad_token_id=tokenizer.eos_token_id
                        )

                    script = tokenizer.decode(outputs[0], skip_special_tokens=True)
                    script = script.replace(input_text, "").strip()

                    if len(script) > 50:  # Decent length
                        return script

                except Exception as e:
                    logger.warning(f"Failed with {model_name}: {e}")
                    continue

            # Fallback
            return f"Discover the amazing world of {prompt}. This incredible topic is changing everything. Join us as we explore the fascinating details!"

        except Exception as e:
            logger.error(f"LLM script generation failed: {e}")
            return f"Amazing insights about {prompt}!"

    async def _generate_script_huggingface(self, prompt: str) -> str:
        """Generate script using Hugging Face Inference API."""
        try:
            url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
            headers = {
                "Authorization": f"Bearer {getattr(settings, 'huggingface_api_key', '')}",
                "Content-Type": "application/json"
            }

            data = {
                "inputs": f"Write a viral video script about: {prompt}",
                "parameters": {
                    "max_length": 200,
                    "temperature": 0.8,
                    "do_sample": True
                }
            }

            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if isinstance(result, list) and result:
                        return result[0].get("generated_text", "").strip()

            return f"Explore the fascinating world of {prompt}!"

        except Exception as e:
            logger.error(f"Hugging Face script generation failed: {e}")
            return f"Amazing content about {prompt}!"

    async def _generate_images_stable_diffusion(self, script: str, duration: int) -> List[str]:
        """Generate images using Stable Diffusion."""
        try:
            if "stable_diffusion" not in self.models_loaded:
                self.models_loaded["stable_diffusion"] = StableDiffusionPipeline.from_pretrained(
                    "CompVis/stable-diffusion-v1-4",
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    safety_checker=None
                ).to(self.device)

            pipeline = self.models_loaded["stable_diffusion"]

            # Split script into segments
            segments = self._split_text_into_segments(script, duration // 3)
            images = []

            for segment in segments:
                prompt = f"Cinematic, professional video frame: {segment}"

                with torch.no_grad():
                    image = pipeline(prompt, num_inference_steps=20, guidance_scale=7.5).images[0]

                # Save image
                output_dir = Path("/tmp/ai_images")
                output_dir.mkdir(exist_ok=True)
                image_path = output_dir / f"frame_{len(images):03d}.png"
                image.save(image_path)
                images.append(str(image_path))

            return images

        except Exception as e:
            logger.error(f"Stable Diffusion image generation failed: {e}")
            return []

    async def _generate_images_huggingface(self, prompt: str, duration: int) -> List[str]:
        """Generate images using Hugging Face."""
        try:
            url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
            headers = {
                "Authorization": f"Bearer {getattr(settings, 'huggingface_api_key', '')}",
                "Content-Type": "application/json"
            }

            images = []
            num_images = duration // 3

            for i in range(num_images):
                data = {
                    "inputs": f"Cinematic video frame {i+1}: {prompt}",
                    "parameters": {
                        "width": 768,
                        "height": 432
                    }
                }

                async with self.session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        image_data = await response.read()

                        output_dir = Path("/tmp/ai_images")
                        output_dir.mkdir(exist_ok=True)
                        image_path = output_dir / f"hf_frame_{i:03d}.png"

                        with open(image_path, "wb") as f:
                            f.write(image_data)

                        images.append(str(image_path))

            return images

        except Exception as e:
            logger.error(f"Hugging Face image generation failed: {e}")
            return []

    async def _generate_voiceover_edge_tts(self, script: str) -> str:
        """Generate voiceover using Edge TTS."""
        try:
            output_dir = Path("/tmp/audio")
            output_dir.mkdir(exist_ok=True)
            audio_path = output_dir / "voiceover.mp3"

            # Use high-quality voice
            voice = "en-US-AriaRUS"  # Premium voice
            communicate = edge_tts.Communicate(script, voice)
            await communicate.save(str(audio_path))

            return str(audio_path)

        except Exception as e:
            logger.error(f"Edge TTS voiceover failed: {e}")
            return "/tmp/silent.mp3"

    async def _generate_voiceover_coqui(self, script: str) -> str:
        """Generate voiceover using Coqui TTS."""
        try:
            # This would require Coqui TTS installation
            # For now, return silent audio
            output_dir = Path("/tmp/audio")
            output_dir.mkdir(exist_ok=True)
            audio_path = output_dir / "coqui_voiceover.wav"

            # Placeholder - would implement Coqui TTS here
            # For production, install coqui-tts and use it

            return str(audio_path)

        except Exception as e:
            logger.error(f"Coqui TTS voiceover failed: {e}")
            return "/tmp/silent.mp3"

    async def _create_video_moviepy(self, image_paths: List[str], audio_path: str, duration: int) -> str:
        """Create video using MoviePy."""
        try:
            output_dir = Path("/tmp/videos")
            output_dir.mkdir(exist_ok=True)
            video_path = output_dir / f"generated_{int(asyncio.get_event_loop().time())}.mp4"

            # Create video clips
            clips = []
            image_duration = duration / len(image_paths)

            for i, image_path in enumerate(image_paths):
                if Path(image_path).exists():
                    clip = ImageClip(image_path, duration=image_duration)
                    # Add fade transitions
                    if i > 0:
                        clip = clip.fadein(0.5)
                    if i < len(image_paths) - 1:
                        clip = clip.fadeout(0.5)
                    clips.append(clip)

            if not clips:
                raise Exception("No valid image clips")

            video_clip = CompositeVideoClip(clips)

            # Add audio
            if Path(audio_path).exists() and audio_path != "/tmp/silent.mp3":
                audio_clip = AudioFileClip(audio_path)
                if audio_clip.duration > duration:
                    audio_clip = audio_clip.subclip(0, duration)
                video_clip = video_clip.set_audio(audio_clip)

            # Write video
            video_clip.write_videofile(
                str(video_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )

            return str(video_path)

        except Exception as e:
            logger.error(f"MoviePy video creation failed: {e}")
            raise

    async def _create_video_opencv(self, image_paths: List[str], audio_path: str, duration: int) -> str:
        """Create video using OpenCV (fallback)."""
        try:
            output_dir = Path("/tmp/videos")
            output_dir.mkdir(exist_ok=True)
            video_path = output_dir / f"opencv_{int(asyncio.get_event_loop().time())}.mp4"

            if not image_paths:
                raise Exception("No images provided")

            # Read first image to get dimensions
            first_image = cv2.imread(image_paths[0])
            height, width = first_image.shape[:2]

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(video_path), fourcc, 24.0, (width, height))

            # Add each image for appropriate duration
            frames_per_image = int(24 * (duration / len(image_paths)))

            for image_path in image_paths:
                if Path(image_path).exists():
                    image = cv2.imread(image_path)
                    for _ in range(frames_per_image):
                        out.write(image)

            out.release()
            return str(video_path)

        except Exception as e:
            logger.error(f"OpenCV video creation failed: {e}")
            raise

    async def _create_video_from_replicate(self, output_urls: List[str], prompt: str, duration: int) -> str:
        """Create video from Replicate output."""
        try:
            # Download images from Replicate
            image_paths = []
            for i, url in enumerate(output_urls):
                async with self.session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        output_dir = Path("/tmp/ai_images")
                        output_dir.mkdir(exist_ok=True)
                        image_path = output_dir / f"rep_{i:03d}.png"

                        with open(image_path, "wb") as f:
                            f.write(image_data)

                        image_paths.append(str(image_path))

            # Create video
            return await self._create_video_moviepy(image_paths, "/tmp/silent.mp3", duration)

        except Exception as e:
            logger.error(f"Replicate video creation failed: {e}")
            return None

    async def _create_video_from_images(self, image_urls: List[str], prompt: str, duration: int) -> str:
        """Create video from image URLs."""
        try:
            image_paths = []
            for i, url in enumerate(image_urls):
                async with self.session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        output_dir = Path("/tmp/ai_images")
                        output_dir.mkdir(exist_ok=True)
                        image_path = output_dir / f"url_{i:03d}.png"

                        with open(image_path, "wb") as f:
                            f.write(image_data)

                        image_paths.append(str(image_path))

            return await self._create_video_moviepy(image_paths, "/tmp/silent.mp3", duration)

        except Exception as e:
            logger.error(f"URL video creation failed: {e}")
            return None

    def _split_text_into_segments(self, text: str, num_segments: int) -> List[str]:
        """Split text into segments."""
        words = text.split()
        segment_size = len(words) // num_segments
        segments = []

        for i in range(num_segments):
            start = i * segment_size
            end = (i + 1) * segment_size if i < num_segments - 1 else len(words)
            segment = " ".join(words[start:end])
            segments.append(segment)

        return segments

    async def _unload_all_models(self):
        """Unload all loaded models."""
        try:
            for model_name, model_data in self.models_loaded.items():
                if hasattr(model_data, 'to'):
                    # It's a PyTorch model
                    model_data.to('cpu')
                elif isinstance(model_data, tuple):
                    # Tokenizer and model tuple
                    tokenizer, model = model_data
                    model.to('cpu')

            self.models_loaded.clear()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("All AI models unloaded")

        except Exception as e:
            logger.error(f"Error unloading models: {e}")

    async def generate_captions(self, video_description: str) -> Dict[str, Any]:
        """Generate captions using open-source models."""
        try:
            # Try open-source LLM first
            if "gpt2" not in self.models_loaded:
                tokenizer = AutoTokenizer.from_pretrained("gpt2")
                model = AutoModelForCausalLM.from_pretrained("gpt2")
                self.models_loaded["gpt2"] = (tokenizer, model)

            tokenizer, model = self.models_loaded["gpt2"]
            model.to(self.device)

            prompt = f"Write engaging captions for a video about: {video_description}\nCaptions:"
            inputs = tokenizer(prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = model.generate(
                    inputs.input_ids,
                    max_length=150,
                    num_return_sequences=1,
                    temperature=0.8,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )

            captions_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            captions_text = captions_text.replace(prompt, "").strip()

            # Parse into captions and hashtags
            lines = captions_text.split('\n')
            captions = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            hashtags = [line.strip() for line in lines if line.strip() and line.startswith('#')]

            if not captions:
                captions = [f"Amazing video about {video_description}!"]

            if not hashtags:
                hashtags = ["#viral", "#video", "#content"]

            return {
                "captions": captions[:3],
                "hashtags": hashtags[:10]
            }

        except Exception as e:
            logger.error(f"Open-source caption generation failed: {e}")
            return {
                "captions": [f"Amazing content about {video_description}!"],
                "hashtags": ["#viral", "#video", "#content"]
            }