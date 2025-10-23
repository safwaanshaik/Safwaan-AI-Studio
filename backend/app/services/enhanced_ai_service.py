import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiohttp
import os
from pathlib import Path
import torch
from diffusers import StableDiffusionPipeline, StableDiffusionImg2ImgPipeline, StableDiffusionInpaintPipeline
from transformers import pipeline as hf_pipeline, AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip, concatenate_videoclips
import edge_tts
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class EnhancedAIService:
    """Enhanced AI service with advanced error handling, performance optimization, and production features."""

    def __init__(self):
        self.session = None
        self.models_loaded = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_cache = {}
        self.performance_metrics = {
            "videos_generated": 0,
            "average_generation_time": 0,
            "success_rate": 0,
            "errors": []
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self._cleanup_resources()

    async def generate_video_enhanced(
        self,
        prompt: str,
        duration: int = 30,
        style: str = "cinematic",
        quality: str = "high",
        target_platform: str = "universal"
    ) -> Dict[str, Any]:
        """Enhanced video generation with comprehensive error handling and optimization."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Validate inputs
            if not prompt or len(prompt.strip()) < 10:
                raise ValueError("Prompt must be at least 10 characters long")

            if duration < 10 or duration > 120:
                raise ValueError("Duration must be between 10-120 seconds")

            # Pre-flight checks
            await self._validate_system_resources()

            # Generate content with multiple fallbacks
            result = await self._generate_with_comprehensive_fallbacks(
                prompt, duration, style, quality, target_platform
            )

            # Post-processing and optimization
            if result.get("video_path"):
                result = await self._post_process_video(result, target_platform, quality)

            # Update performance metrics
            generation_time = asyncio.get_event_loop().time() - start_time
            self._update_performance_metrics(True, generation_time)

            result.update({
                "generation_time": generation_time,
                "quality": quality,
                "style": style,
                "target_platform": target_platform,
                "success": True
            })

            return result

        except Exception as e:
            # Update error metrics
            generation_time = asyncio.get_event_loop().time() - start_time
            self._update_performance_metrics(False, generation_time, str(e))

            logger.error(f"Enhanced video generation failed: {e}")

            # Return error result with fallback content
            return {
                "success": False,
                "error": str(e),
                "generation_time": generation_time,
                "fallback_content": await self._generate_fallback_content(prompt, duration)
            }

    async def _generate_with_comprehensive_fallbacks(
        self,
        prompt: str,
        duration: int,
        style: str,
        quality: str,
        target_platform: str
    ) -> Dict[str, Any]:
        """Generate video with multiple fallback strategies."""

        strategies = [
            # Primary: Full AI pipeline
            lambda: self._generate_full_ai_pipeline(prompt, duration, style, quality),

            # Fallback 1: Simplified pipeline
            lambda: self._generate_simplified_pipeline(prompt, duration, style),

            # Fallback 2: API-based generation
            lambda: self._generate_api_based(prompt, duration, style),

            # Fallback 3: Template-based generation
            lambda: self._generate_template_based(prompt, duration, style),

            # Last resort: Basic text-to-video
            lambda: self._generate_basic_fallback(prompt, duration)
        ]

        last_error = None

        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"Trying generation strategy {i + 1}")
                result = await strategy()

                if result and result.get("video_path"):
                    logger.info(f"Generation strategy {i + 1} succeeded")
                    return result

            except Exception as e:
                logger.warning(f"Strategy {i + 1} failed: {e}")
                last_error = e
                continue

        # All strategies failed
        raise Exception(f"All generation strategies failed. Last error: {last_error}")

    async def _generate_full_ai_pipeline(
        self,
        prompt: str,
        duration: int,
        style: str,
        quality: str
    ) -> Dict[str, Any]:
        """Full AI pipeline with advanced models."""
        try:
            # Enhanced script generation
            script = await self._generate_enhanced_script(prompt, style, quality)

            # Multi-model image generation
            images = await self._generate_multi_model_images(script, duration, style, quality)

            # Professional voice synthesis
            audio_path = await self._generate_enhanced_voiceover(script, style)

            # Advanced video editing
            video_path = await self._create_enhanced_video(images, audio_path, duration, style, quality)

            return {
                "video_path": video_path,
                "script": script,
                "image_count": len(images),
                "audio_path": audio_path,
                "method": "full_ai_pipeline"
            }

        except Exception as e:
            logger.error(f"Full AI pipeline failed: {e}")
            raise

    async def _generate_enhanced_script(
        self,
        prompt: str,
        style: str,
        quality: str
    ) -> str:
        """Generate enhanced script with multiple models and validation."""
        try:
            # Try multiple LLM models in order of preference
            models_to_try = [
                ("EleutherAI/gpt-j-6B", "best quality, detailed scripts"),
                ("EleutherAI/gpt-neo-2.7B", "good balance of quality and speed"),
                ("microsoft/DialoGPT-large", "conversational, engaging scripts"),
                ("gpt2-large", "fast, reliable fallback"),
                ("distilgpt2", "fastest fallback")
            ]

            for model_name, description in models_to_try:
                try:
                    script = await self._generate_script_with_model(
                        prompt, style, quality, model_name
                    )

                    if script and len(script) > 50:
                        # Validate script quality
                        if self._validate_script_quality(script):
                            logger.info(f"Generated script using {model_name}")
                            return script

                except Exception as e:
                    logger.warning(f"Failed with {model_name}: {e}")
                    continue

            # Fallback script generation
            return self._create_enhanced_fallback_script(prompt, style, quality)

        except Exception as e:
            logger.error(f"Enhanced script generation failed: {e}")
            raise

    async def _generate_script_with_model(
        self,
        prompt: str,
        style: str,
        quality: str,
        model_name: str
    ) -> str:
        """Generate script with specific model."""
        try:
            if model_name not in self.models_loaded:
                tokenizer = AutoTokenizer.from_pretrained(self.model_configs[model_name]["tokenizer"])
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_configs[model_name]["model"],
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None,
                    low_cpu_mem_usage=True
                )
                self.models_loaded[model_name] = (tokenizer, model)

            tokenizer, model = self.models_loaded[model_name]

            # Enhanced prompt engineering based on style and quality
            style_prompts = {
                "cinematic": f"Write a dramatic, cinematic video script about",
                "educational": f"Write an informative, educational video script about",
                "entertainment": f"Write a fun, entertaining video script about",
                "news": f"Write a breaking news style video script about",
                "tutorial": f"Write a step-by-step tutorial video script about",
                "commercial": f"Write an engaging commercial video script about"
            }

            quality_modifiers = {
                "high": "with detailed descriptions, professional language, and compelling narrative",
                "medium": "with clear descriptions and engaging content",
                "low": "with basic descriptions and simple language"
            }

            base_prompt = style_prompts.get(style, "Write a viral video script about")
            quality_modifier = quality_modifiers.get(quality, "")

            full_prompt = f"{base_prompt} {prompt}. Create a script {quality_modifier}.\n\nScript:"

            inputs = tokenizer(full_prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = model.generate(
                    inputs.input_ids,
                    max_length=400 if quality == "high" else 300,
                    num_return_sequences=1,
                    temperature=0.7 if quality == "high" else 0.8,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    no_repeat_ngram_size=3,
                    top_p=0.9
                )

            script = tokenizer.decode(outputs[0], skip_special_tokens=True)
            script = script.replace(full_prompt, "").strip()

            # Clean and format
            script = self._clean_enhanced_script(script)

            return script

        except Exception as e:
            logger.error(f"Error with {model_name}: {e}")
            raise

    def _validate_script_quality(self, script: str) -> bool:
        """Validate script quality and content."""
        if len(script) < 50:
            return False

        # Check for basic quality metrics
        sentences = script.split('.')
        if len(sentences) < 3:
            return False

        # Check for repetitive content
        words = script.lower().split()
        if len(words) > 10:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # Too repetitive
                return False

        return True

    def _clean_enhanced_script(self, script: str) -> str:
        """Clean and format generated script."""
        # Remove common artifacts
        script = script.replace("Script:", "").replace("Video Script:", "").strip()

        # Split into sentences and clean
        sentences = [s.strip() for s in script.split('.') if s.strip()]
        sentences = [s + '.' for s in sentences if not s.endswith('.') and len(s) > 5]

        # Filter out very short or very long sentences
        sentences = [s for s in sentences if 10 <= len(s) <= 200]

        # Limit to reasonable number of sentences
        max_sentences = 8 if len(sentences) > 8 else len(sentences)
        sentences = sentences[:max_sentences]

        # Join back
        clean_script = ' '.join(sentences)

        return clean_script if len(clean_script) > 30 else script

    def _create_enhanced_fallback_script(self, prompt: str, style: str, quality: str) -> str:
        """Create enhanced fallback script."""
        style_templates = {
            "cinematic": [
                f"In a world of endless possibilities, discover the incredible story of {prompt}.",
                f"This groundbreaking phenomenon is changing everything we know about innovation.",
                f"Prepare to be amazed by this incredible journey through the world of {prompt}.",
                f"From humble beginnings to global impact, witness the transformation.",
                f"This is more than just a story—it's a revolution waiting to happen."
            ],
            "educational": [
                f"Today we're diving deep into the fascinating world of {prompt}.",
                f"Understanding this topic is crucial for anyone interested in staying ahead.",
                f"Let's break down the key concepts and explore what makes {prompt} so important.",
                f"From basic principles to advanced applications, we'll cover everything you need to know.",
                f"This comprehensive guide will give you the knowledge to make informed decisions."
            ],
            "entertainment": [
                f"Get ready for an amazing adventure through the exciting world of {prompt}!",
                f"You won't believe what we're about to discover together.",
                f"This is going to be absolutely incredible—let's dive right in!",
                f"Prepare yourself for some mind-blowing insights and entertainment.",
                f"You've never seen anything quite like this before!"
            ]
        }

        templates = style_templates.get(style, style_templates["educational"])
        selected_templates = templates[:3]  # Use first 3 templates

        return ' '.join(selected_templates)

    async def _generate_multi_model_images(
        self,
        script: str,
        duration: int,
        style: str,
        quality: str
    ) -> List[str]:
        """Generate images using multiple models for best quality."""
        try:
            # Determine number of images based on duration and quality
            if quality == "high":
                images_per_second = 1/2  # One image every 2 seconds
            elif quality == "medium":
                images_per_second = 1/3  # One image every 3 seconds
            else:
                images_per_second = 1/4  # One image every 4 seconds

            num_images = max(3, int(duration * images_per_second))

            # Split script into segments
            segments = self._split_script_into_segments(script, num_images)

            # Try multiple Stable Diffusion models
            sd_models = [
                "stabilityai/stable-diffusion-2-1",
                "runwayml/stable-diffusion-v1-5",
                "CompVis/stable-diffusion-v1-4"
            ]

            images = []
            for i, segment in enumerate(segments):
                image_path = None

                for model_name in sd_models:
                    try:
                        image_path = await self._generate_image_with_model(
                            segment, style, quality, model_name, i
                        )
                        if image_path:
                            break
                    except Exception as e:
                        logger.warning(f"Failed with {model_name}: {e}")
                        continue

                if image_path:
                    images.append(image_path)
                else:
                    # Create fallback image
                    images.append(await self._create_fallback_image(i))

                # Prevent GPU memory issues
                if (i + 1) % 3 == 0:
                    await asyncio.sleep(1)

            return images

        except Exception as e:
            logger.error(f"Multi-model image generation failed: {e}")
            raise

    async def _generate_image_with_model(
        self,
        prompt: str,
        style: str,
        quality: str,
        model_name: str,
        index: int
    ) -> Optional[str]:
        """Generate image with specific Stable Diffusion model."""
        try:
            if model_name not in self.models_loaded:
                pipeline = StableDiffusionPipeline.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    safety_checker=None,
                    requires_safety_checker=False
                ).to(self.device)
                self.models_loaded[model_name] = pipeline

            pipeline = self.models_loaded[model_name]

            # Style-specific prompt engineering
            style_modifiers = {
                "cinematic": "cinematic, movie scene, dramatic lighting, professional cinematography, 4k, film grain",
                "educational": "clean, professional, educational, informative, clear, well-lit, diagram style",
                "entertainment": "vibrant, fun, colorful, energetic, engaging, dynamic, cartoon style",
                "news": "professional, news broadcast, serious, informative, clean, broadcast quality",
                "tutorial": "step-by-step, clear, instructional, professional, educational, simple",
                "commercial": "advertising, professional, commercial, sleek, modern, high-end"
            }

            modifier = style_modifiers.get(style, "professional, high quality")

            # Quality settings
            if quality == "high":
                steps = 50
                guidance_scale = 7.5
                height, width = 512, 512
            elif quality == "medium":
                steps = 30
                guidance_scale = 7.0
                height, width = 448, 448
            else:
                steps = 20
                guidance_scale = 6.5
                height, width = 384, 384

            # Create detailed prompt
            full_prompt = f"{modifier}, {prompt}, detailed, high resolution, professional"

            # Negative prompt for better quality
            negative_prompt = "blurry, low quality, distorted, ugly, poorly drawn, cartoon, anime, text, watermark, signature"

            with torch.no_grad():
                image = pipeline(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=steps,
                    guidance_scale=guidance_scale,
                    height=height,
                    width=width
                ).images[0]

            # Save image
            output_dir = Path("/tmp/ai_images")
            output_dir.mkdir(exist_ok=True)
            image_path = output_dir / f"enhanced_{model_name.split('/')[-1]}_{index:03d}.png"
            image.save(image_path)

            return str(image_path)

        except Exception as e:
            logger.error(f"Error with {model_name}: {e}")
            raise

    async def _create_fallback_image(self, index: int) -> str:
        """Create a fallback image when AI generation fails."""
        try:
            output_dir = Path("/tmp/ai_images")
            output_dir.mkdir(exist_ok=True)
            image_path = output_dir / f"fallback_{index:03d}.png"

            # Create a gradient image
            height, width = 512, 512
            img = np.zeros((height, width, 3), dtype=np.uint8)

            # Create gradient based on index
            colors = [
                (255, 100, 100), (100, 255, 100), (100, 100, 255),
                (255, 255, 100), (255, 100, 255), (100, 255, 255)
            ]
            base_color = colors[index % len(colors)]

            for y in range(height):
                for x in range(width):
                    factor = (x + y) / (width + height)
                    img[y, x] = [
                        int(base_color[0] * (0.5 + 0.5 * factor)),
                        int(base_color[1] * (0.5 + 0.5 * factor)),
                        int(base_color[2] * (0.5 + 0.5 * factor))
                    ]

            cv2.imwrite(str(image_path), img)
            return str(image_path)

        except Exception as e:
            logger.error(f"Fallback image creation failed: {e}")
            raise

    async def _generate_enhanced_voiceover(self, script: str, style: str) -> str:
        """Generate enhanced voiceover with multiple options."""
        try:
            # Try Edge TTS first (highest quality)
            try:
                return await self._generate_voiceover_edge_tts_enhanced(script, style)
            except Exception as e:
                logger.warning(f"Edge TTS failed: {e}")

            # Try Coqui TTS
            try:
                return await self._generate_voiceover_coqui_enhanced(script, style)
            except Exception as e:
                logger.warning(f"Coqui TTS failed: {e}")

            # Fallback to silent audio
            return await self._create_silent_audio(script)

        except Exception as e:
            logger.error(f"Enhanced voiceover generation failed: {e}")
            raise

    async def _generate_voiceover_edge_tts_enhanced(self, script: str, style: str) -> str:
        """Enhanced Edge TTS with style-specific voices and settings."""
        try:
            output_dir = Path("/tmp/audio")
            output_dir.mkdir(exist_ok=True)
            audio_path = output_dir / f"enhanced_voiceover_{style}_{int(asyncio.get_event_loop().time())}.mp3"

            # Style-specific voice selection
            voice_mapping = {
                "cinematic": "en-US-AriaRUS",      # Dramatic female voice
                "educational": "en-US-ZiraRUS",    # Professional female voice
                "entertainment": "en-US-BenjaminRUS", # Energetic male voice
                "news": "en-GB-SoniaRUS",          # Authoritative British voice
                "tutorial": "en-US-AriaRUS",       # Clear female voice
                "commercial": "en-US-ZiraRUS"      # Professional female voice
            }

            voice = voice_mapping.get(style, "en-US-AriaRUS")

            # Style-specific speech settings
            rate_mapping = {
                "cinematic": "-5%",     # Slightly slower for drama
                "educational": "+0%",   # Normal speed
                "entertainment": "+10%", # Slightly faster for energy
                "news": "-2%",          # Slightly slower for authority
                "tutorial": "+0%",      # Normal for clarity
                "commercial": "+5%"     # Slightly faster for engagement
            }

            rate = rate_mapping.get(style, "+0%")

            # Style-specific pitch adjustments
            pitch_mapping = {
                "cinematic": "+0Hz",    # Normal pitch
                "educational": "+0Hz",  # Normal pitch
                "entertainment": "+10Hz", # Slightly higher for energy
                "news": "-5Hz",         # Slightly lower for authority
                "tutorial": "+0Hz",     # Normal pitch
                "commercial": "+5Hz"    # Slightly higher for appeal
            }

            pitch = pitch_mapping.get(style, "+0Hz")

            communicate = edge_tts.Communicate(script, voice, rate=rate, pitch=pitch)
            await communicate.save(str(audio_path))

            return str(audio_path)

        except Exception as e:
            logger.error(f"Enhanced Edge TTS failed: {e}")
            raise

    async def _generate_voiceover_coqui_enhanced(self, script: str, style: str) -> str:
        """Enhanced Coqui TTS (placeholder for when installed)."""
        try:
            # This would use Coqui TTS when properly installed
            output_dir = Path("/tmp/audio")
            output_dir.mkdir(exist_ok=True)
            audio_path = output_dir / f"coqui_enhanced_{style}_{int(asyncio.get_event_loop().time())}.wav"

            # Placeholder - create silent audio for now
            await self._create_silent_audio(script)

            return str(audio_path)

        except Exception as e:
            logger.error(f"Enhanced Coqui TTS failed: {e}")
            raise

    async def _create_silent_audio(self, script: str) -> str:
        """Create silent audio matching script duration."""
        try:
            output_dir = Path("/tmp/audio")
            output_dir.mkdir(exist_ok=True)
            audio_path = output_dir / f"silent_{int(asyncio.get_event_loop().time())}.mp3"

            # Estimate duration based on word count
            word_count = len(script.split())
            estimated_duration = max(10, word_count * 0.4)  # ~0.4 seconds per word

            # Create silent audio clip
            silent_audio = AudioFileClip(filename=None, duration=estimated_duration)
            silent_audio.write_audiofile(str(audio_path), verbose=False, logger=None)

            return str(audio_path)

        except Exception as e:
            logger.error(f"Silent audio creation failed: {e}")
            raise

    async def _create_enhanced_video(
        self,
        image_paths: List[str],
        audio_path: str,
        duration: int,
        style: str,
        quality: str
    ) -> str:
        """Create enhanced video with advanced editing."""
        try:
            output_dir = Path("/tmp/videos")
            output_dir.mkdir(exist_ok=True)
            video_path = output_dir / f"enhanced_{style}_{quality}_{int(asyncio.get_event_loop().time())}.mp4"

            # Create video clips with enhanced effects
            clips = []
            image_duration = duration / len(image_paths)

            for i, image_path in enumerate(image_paths):
                if Path(image_path).exists():
                    clip = ImageClip(image_path, duration=image_duration)

                    # Apply style-specific effects
                    clip = await self._apply_enhanced_effects(clip, style, i, len(image_paths))

                    clips.append(clip)

            if not clips:
                raise Exception("No valid image clips created")

            # Concatenate clips
            video_clip = concatenate_videoclips(clips, method="compose")

            # Add enhanced audio
            if Path(audio_path).exists() and audio_path != "/tmp/silent.mp3":
                try:
                    audio_clip = AudioFileClip(audio_path)
                    # Adjust audio duration to match video
                    if audio_clip.duration > duration:
                        audio_clip = audio_clip.subclip(0, duration)
                    elif audio_clip.duration < duration:
                        # Loop audio if too short
                        audio_clip = audio_clip.loop(duration=duration)
                    video_clip = video_clip.set_audio(audio_clip)
                except Exception as e:
                    logger.warning(f"Failed to add enhanced audio: {e}")

            # Apply quality-specific encoding
            codec_settings = self._get_enhanced_codec_settings(quality)

            video_clip.write_videofile(
                str(video_path),
                fps=30 if quality == "high" else 24,
                codec=codec_settings["codec"],
                audio_codec=codec_settings["audio_codec"],
                bitrate=codec_settings["bitrate"],
                preset="slow" if quality == "high" else "medium",
                verbose=False,
                logger=None
            )

            return str(video_path)

        except Exception as e:
            logger.error(f"Enhanced video creation failed: {e}")
            raise

    async def _apply_enhanced_effects(
        self,
        clip: ImageClip,
        style: str,
        index: int,
        total: int
    ) -> ImageClip:
        """Apply enhanced visual effects based on style."""
        try:
            # Base transitions
            if index > 0:
                clip = clip.fadein(0.5)
            if index < total - 1:
                clip = clip.fadeout(0.5)

            # Style-specific effects
            if style == "cinematic":
                # Add dramatic zoom and color grading
                clip = clip.resize(lambda t: 1 + 0.1 * np.sin(2 * np.pi * t / clip.duration))
                # Add subtle rotation for cinematic feel
                clip = clip.rotate(lambda t: 1 * np.sin(2 * np.pi * t / clip.duration))

            elif style == "educational":
                # Clean, professional transitions
                clip = clip.resize(lambda t: 1 + 0.02 * np.sin(2 * np.pi * t / clip.duration))

            elif style == "entertainment":
                # Dynamic effects
                clip = clip.resize(lambda t: 1 + 0.15 * np.sin(4 * np.pi * t / clip.duration))
                clip = clip.rotate(lambda t: 2 * np.sin(4 * np.pi * t / clip.duration))

            elif style == "news":
                # Subtle, professional effects
                clip = clip.resize(lambda t: 1 + 0.01 * np.sin(2 * np.pi * t / clip.duration))

            elif style == "tutorial":
                # Clear, instructional effects
                clip = clip.resize(lambda t: 1 + 0.03 * np.sin(2 * np.pi * t / clip.duration))

            elif style == "commercial":
                # Sleek, modern effects
                clip = clip.resize(lambda t: 1 + 0.08 * np.sin(3 * np.pi * t / clip.duration))

            return clip

        except Exception as e:
            logger.error(f"Enhanced effects application failed: {e}")
            return clip

    def _get_enhanced_codec_settings(self, quality: str) -> Dict[str, str]:
        """Get enhanced codec settings based on quality."""
        settings = {
            "high": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "5000k"
            },
            "medium": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "2500k"
            },
            "low": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "1200k"
            }
        }

        return settings.get(quality, settings["medium"])

    async def _post_process_video(
        self,
        result: Dict[str, Any],
        target_platform: str,
        quality: str
    ) -> Dict[str, Any]:
        """Post-process video for target platform."""
        try:
            video_path = result.get("video_path")
            if not video_path or not Path(video_path).exists():
                return result

            # Platform-specific optimizations
            if target_platform in ["tiktok", "instagram", "youtube_shorts"]:
                result = await self._optimize_for_short_form(result, target_platform)
            elif target_platform in ["youtube", "vimeo"]:
                result = await self._optimize_for_long_form(result, target_platform)
            elif target_platform == "twitter":
                result = await self._optimize_for_twitter(result)

            # Quality-specific enhancements
            if quality == "high":
                result = await self._apply_high_quality_enhancements(result)

            return result

        except Exception as e:
            logger.error(f"Video post-processing failed: {e}")
            return result

    async def _optimize_for_short_form(
        self,
        result: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """Optimize video for short-form platforms."""
        try:
            video_path = result.get("video_path")
            if not video_path:
                return result

            # Load video
            clip = VideoFileClip(video_path)

            # Ensure correct aspect ratio and duration
            if platform == "tiktok":
                target_ratio = 9/16  # 0.5625
                max_duration = 180
            elif platform == "instagram":
                target_ratio = 9/16
                max_duration = 90
            elif platform == "youtube_shorts":
                target_ratio = 9/16
                max_duration = 60
            else:
                target_ratio = 16/9
                max_duration = 60

            # Resize to target aspect ratio
            current_ratio = clip.w / clip.h
            if abs(current_ratio - target_ratio) > 0.1:
                if current_ratio > target_ratio:
                    # Too wide, crop width
                    new_width = int(clip.h * target_ratio)
                    clip = clip.crop(x1=(clip.w - new_width)//2, x2=(clip.w + new_width)//2)
                else:
                    # Too tall, crop height
                    new_height = int(clip.w / target_ratio)
                    clip = clip.crop(y1=(clip.h - new_height)//2, y2=(clip.h + new_height)//2)

            # Trim duration if too long
            if clip.duration > max_duration:
                clip = clip.subclip(0, max_duration)

            # Save optimized video
            optimized_path = video_path.replace(".mp4", f"_{platform}_optimized.mp4")
            clip.write_videofile(
                optimized_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )

            result["video_path"] = optimized_path
            result["optimized_for"] = platform

            return result

        except Exception as e:
            logger.error(f"Short-form optimization failed: {e}")
            return result

    async def _optimize_for_long_form(
        self,
        result: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """Optimize video for long-form platforms."""
        try:
            video_path = result.get("video_path")
            if not video_path:
                return result

            # Load video
            clip = VideoFileClip(video_path)

            # Ensure 16:9 aspect ratio
            target_ratio = 16/9
            current_ratio = clip.w / clip.h

            if abs(current_ratio - target_ratio) > 0.1:
                if current_ratio > target_ratio:
                    # Add black bars to top/bottom
                    new_height = int(clip.w / target_ratio)
                    bg_clip = ColorClip(size=(clip.w, new_height), color=(0,0,0), duration=clip.duration)
                    clip = CompositeVideoClip([bg_clip, clip.set_position('center')])
                else:
                    # Add black bars to sides
                    new_width = int(clip.h * target_ratio)
                    bg_clip = ColorClip(size=(new_width, clip.h), color=(0,0,0), duration=clip.duration)
                    clip = CompositeVideoClip([bg_clip, clip.set_position('center')])

            # Save optimized video
            optimized_path = video_path.replace(".mp4", f"_{platform}_optimized.mp4")
            clip.write_videofile(
                optimized_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )

            result["video_path"] = optimized_path
            result["optimized_for"] = platform

            return result

        except Exception as e:
            logger.error(f"Long-form optimization failed: {e}")
            return result

    async def _optimize_for_twitter(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize video for Twitter."""
        try:
            video_path = result.get("video_path")
            if not video_path:
                return result

            # Load video
            clip = VideoFileClip(video_path)

            # Twitter video specs: max 2:20, various aspect ratios supported
            max_duration = 140  # 2 minutes 20 seconds
            if clip.duration > max_duration:
                clip = clip.subclip(0, max_duration)

            # Save optimized video
            optimized_path = video_path.replace(".mp4", "_twitter_optimized.mp4")
            clip.write_videofile(
                optimized_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )

            result["video_path"] = optimized_path
            result["optimized_for"] = "twitter"

            return result

        except Exception as e:
            logger.error(f"Twitter optimization failed: {e}")
            return result

    async def _apply_high_quality_enhancements(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply high-quality enhancements."""
        try:
            video_path = result.get("video_path")
            if not video_path:
                return result

            # For now, just ensure high bitrate encoding
            # Future enhancements could include:
            # - Color grading
            # - Stabilization
            # - Noise reduction
            # - Subtitle addition

            enhanced_path = video_path.replace(".mp4", "_enhanced.mp4")

            # Re-encode with higher quality settings
            clip = VideoFileClip(video_path)
            clip.write_videofile(
                enhanced_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                bitrate="8000k",
                preset="slow",
                verbose=False,
                logger=None
            )

            result["video_path"] = enhanced_path
            result["quality_enhanced"] = True

            return result

        except Exception as e:
            logger.error(f"High-quality enhancement failed: {e}")
            return result

    async def _validate_system_resources(self) -> None:
        """Validate system has enough resources for generation."""
        try:
            # Check available memory
            if self.device == "cuda":
                if not torch.cuda.is_available():
                    raise Exception("CUDA requested but not available")

                # Check GPU memory
                gpu_memory = torch.cuda.get_device_properties(0).total_memory
                if gpu_memory < 4 * 1024 * 1024 * 1024:  # 4GB
                    logger.warning("Low GPU memory detected, performance may be reduced")

            # Check disk space
            stat = os.statvfs('/tmp')
            free_space = stat.f_bavail * stat.f_frsize
            if free_space < 1 * 1024 * 1024 * 1024:  # 1GB
                raise Exception("Insufficient disk space")

        except Exception as e:
            logger.error(f"System resource validation failed: {e}")
            raise

    def _update_performance_metrics(self, success: bool, generation_time: float, error: str = None) -> None:
        """Update performance metrics."""
        try:
            self.performance_metrics["videos_generated"] += 1

            # Update average generation time
            current_avg = self.performance_metrics["average_generation_time"]
            total_videos = self.performance_metrics["videos_generated"]
            self.performance_metrics["average_generation_time"] = (
                (current_avg * (total_videos - 1)) + generation_time
            ) / total_videos

            # Update success rate
            if success:
                success_count = int(self.performance_metrics["success_rate"] * (total_videos - 1) / 100)
                success_count += 1
                self.performance_metrics["success_rate"] = (success_count / total_videos) * 100
            else:
                self.performance_metrics["errors"].append({
                    "timestamp": asyncio.get_event_loop().time(),
                    "error": error,
                    "generation_time": generation_time
                })

                # Keep only last 100 errors
                if len(self.performance_metrics["errors"]) > 100:
                    self.performance_metrics["errors"] = self.performance_metrics["errors"][-100:]

        except Exception as e:
            logger.error(f"Performance metrics update failed: {e}")

    async def _cleanup_resources(self) -> None:
        """Clean up resources and models."""
        try:
            # Unload all models
            for model_name, model_data in self.models_loaded.items():
                try:
                    if hasattr(model_data, 'to'):
                        model_data.to('cpu')
                    elif isinstance(model_data, tuple):
                        tokenizer, model = model_data
                        model.to('cpu')
                    elif hasattr(model_data, 'device'):
                        model_data.to('cpu')
                except Exception as e:
                    logger.warning(f"Error unloading {model_name}: {e}")

            self.models_loaded.clear()

            # Clear GPU cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Clean up temporary files (keep last 10 videos for debugging)
            await self._cleanup_temp_files()

            logger.info("Enhanced AI service resources cleaned up")

        except Exception as e:
            logger.error(f"Resource cleanup failed: {e}")

    async def _cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        try:
            # Clean old video files
            video_dir = Path("/tmp/videos")
            if video_dir.exists():
                video_files = sorted(video_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime)
                # Keep last 10 videos
                if len(video_files) > 10:
                    for old_file in video_files[:-10]:
                        old_file.unlink()

            # Clean old image files
            image_dir = Path("/tmp/ai_images")
            if image_dir.exists():
                image_files = sorted(image_dir.glob("*.png"), key=lambda x: x.stat().st_mtime)
                # Keep last 50 images
                if len(image_files) > 50:
                    for old_file in image_files[:-50]:
                        old_file.unlink()

            # Clean old audio files
            audio_dir = Path("/tmp/audio")
            if audio_dir.exists():
                audio_files = sorted(audio_dir.glob("*.*"), key=lambda x: x.stat().st_mtime)
                # Keep last 20 audio files
                if len(audio_files) > 20:
                    for old_file in audio_files[:-20]:
                        old_file.unlink()

        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}")

    def _split_script_into_segments(self, script: str, num_segments: int) -> List[str]:
        """Smart script splitting that preserves meaning."""
        sentences = [s.strip() for s in script.split('.') if s.strip()]
        sentences = [s + '.' for s in sentences if not s.endswith('.')]

        if len(sentences) <= num_segments:
            while len(sentences) < num_segments:
                sentences.append("")
            return sentences

        # Group sentences intelligently
        segment_size = len(sentences) // num_segments
        segments = []

        for i in range(num_segments):
            start = i * segment_size
            end = (i + 1) * segment_size if i < num_segments - 1 else len(sentences)
            segment = " ".join(sentences[start:end])
            segments.append(segment)

        return segments

    # Model configurations
    model_configs = {
        "EleutherAI/gpt-j-6B": {"model": "EleutherAI/gpt-j-6B", "tokenizer": "EleutherAI/gpt-j-6B"},
        "EleutherAI/gpt-neo-2.7B": {"model": "EleutherAI/gpt-neo-2.7B", "tokenizer": "EleutherAI/gpt-neo-2.7B"},
        "microsoft/DialoGPT-large": {"model": "microsoft/DialoGPT-large", "tokenizer": "microsoft/DialoGPT-large"},
        "gpt2-large": {"model": "gpt2-large", "tokenizer": "gpt2-large"},
        "distilgpt2": {"model": "distilgpt2", "tokenizer": "distilgpt2"},
    }

    async def generate_captions_enhanced(
        self,
        video_description: str,
        style: str = "general",
        quality: str = "high"
    ) -> Dict[str, Any]:
        """Generate enhanced captions and hashtags."""
        try:
            # Try multiple models for best results
            caption_models = [
                "EleutherAI/gpt-j-6B",
                "EleutherAI/gpt-neo-2.7B",
                "microsoft/DialoGPT-large",
                "gpt2-large"
            ]

            for model_name in caption_models:
                try:
                    result = await self._generate_captions_with_model_enhanced(
                        video_description, style, quality, model_name
                    )
                    if result and result.get("captions"):
                        return result
                except Exception as e:
                    logger.warning(f"Caption generation failed with {model_name}: {e}")
                    continue

            # Fallback
            return self._create_enhanced_fallback_captions(video_description, style, quality)

        except Exception as e:
            logger.error(f"Enhanced caption generation failed: {e}")
            return self._create_enhanced_fallback_captions(video_description, style, quality)

    async def _generate_captions_with_model_enhanced(
        self,
        video_description: str,
        style: str,
        quality: str,
        model_name: str
    ) -> Dict[str, Any]:
        """Generate captions with enhanced model."""
        try:
            if model_name not in self.models_loaded:
                tokenizer = AutoTokenizer.from_pretrained(self.model_configs[model_name]["tokenizer"])
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_configs[model_name]["model"],
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
                )
                self.models_loaded[model_name] = (tokenizer, model)

            tokenizer, model = self.models_loaded[model_name]
            model.to(self.device)

            # Enhanced prompt engineering
            style_prompts = {
                "cinematic": "Write dramatic, cinematic captions for a movie trailer about",
                "educational": "Write informative, educational captions for a documentary about",
                "entertainment": "Write fun, engaging captions for an entertainment video about",
                "news": "Write serious, informative captions for a news video about",
                "tutorial": "Write clear, instructional captions for a tutorial about",
                "commercial": "Write compelling, commercial captions for an advertisement about"
            }

            quality_modifiers = {
                "high": "with professional language, engaging storytelling, and viral potential",
                "medium": "with clear descriptions and engaging content",
                "low": "with basic descriptions and simple language"
            }

            base_prompt = style_prompts.get(style, "Write engaging captions for a video about")
            quality_modifier = quality_modifiers.get(quality, "")

            prompt = f"{base_prompt} {video_description}. Create captions {quality_modifier}.\n\nCaptions:\n1."

            inputs = tokenizer(prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = model.generate(
                    inputs.input_ids,
                    max_length=250 if quality == "high" else 200,
                    num_return_sequences=1,
                    temperature=0.7 if quality == "high" else 0.8,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )

            captions_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            captions_text = captions_text.replace(prompt, "").strip()

            # Parse and enhance captions
            lines = captions_text.split('\n')
            captions = []
            hashtags = []

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Remove numbering and clean
                    line = line.lstrip('123456789. ')
                    if line and len(line) > 10:
                        captions.append(line)
                elif line.startswith('#'):
                    hashtags.append(line)

            # Generate additional hashtags
            if len(hashtags) < 8:
                hashtags.extend(self._generate_enhanced_hashtags(video_description, style))

            # Limit results
            captions = captions[:4]  # Max 4 captions
            hashtags = hashtags[:20]  # Max 20 hashtags

            return {
                "captions": captions,
                "hashtags": hashtags,
                "style": style,
                "quality": quality
            }

        except Exception as e:
            logger.error(f"Enhanced caption generation with {model_name} failed: {e}")
            raise

    def _generate_enhanced_hashtags(self, description: str, style: str) -> List[str]:
        """Generate enhanced hashtags based on description and style."""
        base_hashtags = ["#viral", "#video", "#content", "#amazing", "#awesome"]

        # Style-specific hashtags
        style_hashtags = {
            "cinematic": ["#movie", "#cinematic", "#film", "#drama", "#storytelling"],
            "educational": ["#learn", "#education", "#knowledge", "#tutorial", "#teaching"],
            "entertainment": ["#fun", "#entertainment", "#amazing", "#wow", "#entertaining"],
            "news": ["#news", "#breaking", "#current", "#update", "#information"],
            "tutorial": ["#howto", "#tutorial", "#guide", "#learn", "#stepbystep"],
            "commercial": ["#advertising", "#brand", "#product", "#commercial", "#marketing"]
        }

        style_tags = style_hashtags.get(style, ["#viral", "#content"])
        hashtags.extend(style_tags)

        # Add description-based hashtags
        words = description.lower().split()
        for word in words[:5]:
            if len(word) > 3 and word not in ['about', 'this', 'that', 'with', 'from']:
                hashtags.append(f"#{word}")

        return hashtags

    def _create_enhanced_fallback_captions(self, video_description: str, style: str, quality: str) -> Dict[str, Any]:
        """Create enhanced fallback captions."""
        style_captions = {
            "cinematic": [
                f"In a world of endless possibilities, discover the incredible story of {video_description}.",
                f"This groundbreaking phenomenon is changing everything we know about innovation.",
                f"Prepare to be amazed by this incredible journey through the world of {video_description}.",
                f"From humble beginnings to global impact, witness the transformation."
            ],
            "educational": [
                f"Today we're diving deep into the fascinating world of {video_description}.",
                f"Understanding this topic is crucial for anyone interested in staying ahead.",
                f"Let's break down the key concepts and explore what makes {video_description} so important.",
                f"From basic principles to advanced applications, we'll cover everything you need to know."
            ],
            "entertainment": [
                f"Get ready for an amazing adventure through the exciting world of {video_description}!",
                f"You won't believe what we're about to discover together.",
                f"This is going to be absolutely incredible—let's dive right in!",
                f"Prepare yourself for some mind-blowing insights and entertainment."
            ],
            "news": [
                f"Breaking news: Major developments in {video_description} are shaking up the industry.",
                f"Here's everything you need to know about this game-changing story.",
                f"Stay informed with the latest updates on {video_description}.",
                f"This could change everything—here's what you need to know."
            ],
            "tutorial": [
                f"Welcome to our comprehensive guide on {video_description}.",
                f"Whether you're a beginner or expert, this tutorial will teach you everything.",
                f"Follow along as we break down {video_description} step by step.",
                f"Master {video_description} with this detailed tutorial."
            ],
            "commercial": [
                f"Discover the power of {video_description} today!",
                f"Transform your experience with our premium {video_description} solution.",
                f"Why choose anything else when you can have the best {video_description}?",
                f"Elevate your standards with our exceptional {video_description}."
            ]
        }

        captions = style_captions.get(style, [
            f"Amazing content about {video_description}!",
            f"You won't want to miss this incredible video!",
            f"Discover something truly remarkable!"
        ])

        return {
            "captions": captions,
            "hashtags": ["#viral", "#video", "#content", "#amazing", "#awesome", f"#{video_description.replace(' ', '')}"],
            "style": style,
            "quality": quality
        }