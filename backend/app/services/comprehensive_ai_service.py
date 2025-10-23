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

class ComprehensiveAIService:
    """Comprehensive AI service with all open-source models and advanced features."""

    def __init__(self):
        self.session = None
        self.models_loaded = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_configs = {
            # Text Generation Models
            "gpt2": {"model": "gpt2", "tokenizer": "gpt2"},
            "gpt2-medium": {"model": "gpt2-medium", "tokenizer": "gpt2-medium"},
            "gpt2-large": {"model": "gpt2-large", "tokenizer": "gpt2-large"},
            "distilgpt2": {"model": "distilgpt2", "tokenizer": "distilgpt2"},
            "microsoft/DialoGPT-medium": {"model": "microsoft/DialoGPT-medium", "tokenizer": "microsoft/DialoGPT-medium"},
            "microsoft/DialoGPT-large": {"model": "microsoft/DialoGPT-large", "tokenizer": "microsoft/DialoGPT-large"},
            "EleutherAI/gpt-neo-1.3B": {"model": "EleutherAI/gpt-neo-1.3B", "tokenizer": "EleutherAI/gpt-neo-1.3B"},
            "EleutherAI/gpt-neo-2.7B": {"model": "EleutherAI/gpt-neo-2.7B", "tokenizer": "EleutherAI/gpt-neo-2.7B"},
            "EleutherAI/gpt-j-6B": {"model": "EleutherAI/gpt-j-6B", "tokenizer": "EleutherAI/gpt-j-6B"},

            # Image Generation Models
            "stable-diffusion-v1-4": {"model": "CompVis/stable-diffusion-v1-4"},
            "stable-diffusion-v1-5": {"model": "runwayml/stable-diffusion-v1-5"},
            "stable-diffusion-2-1": {"model": "stabilityai/stable-diffusion-2-1"},
            "stable-diffusion-2-1-base": {"model": "stabilityai/stable-diffusion-2-1-base"},
            "openjourney": {"model": "prompthero/openjourney"},
            "anything-v3-better-vae": {"model": "Linaqruf/anything-v3-better-vae"},
            " Realistic_Vision_V2.0": {"model": "SG161222/Realistic_Vision_V2.0"},

            # Audio/TTS Models
            "edge_tts_voices": ["en-US-AriaRUS", "en-US-ZiraRUS", "en-US-BenjaminRUS", "en-GB-SoniaRUS"],
            "coqui_tts_models": ["tts_models/en/ljspeech/tacotron2-DDC", "tts_models/en/ljspeech/tacotron2-DDC_ph"],

            # Video Generation Models
            "modelscope": {"model": "damo-vilab/modelscope-damo-text-to-video-synthesis"},
            "zeroscope": {"model": "cerspense/zeroscope_v2_XL"},
            "videocrafter": {"model": "VideoCrafter/VideoCrafter-1"},
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self._unload_all_models()

    async def generate_video(self, prompt: str, duration: int = 30, style: str = "cinematic") -> str:
        """Generate video using the best available open-source models."""
        try:
            # Step 1: Generate script
            script = await self._generate_script_comprehensive(prompt, style)

            # Step 2: Generate images
            images = await self._generate_images_comprehensive(prompt, script, duration, style)

            # Step 3: Generate voiceover
            audio_path = await self._generate_voiceover_comprehensive(script, style)

            # Step 4: Create video
            video_path = await self._create_video_comprehensive(images, audio_path, duration, style)

            # Step 5: Enhance video
            enhanced_path = await self._enhance_video_comprehensive(video_path, style)

            return enhanced_path

        except Exception as e:
            logger.error(f"Comprehensive video generation failed: {e}")
            # Try fallback
            return await self._generate_fallback_video(prompt, duration)

    async def _generate_script_comprehensive(self, prompt: str, style: str) -> str:
        """Generate script using multiple open-source LLMs."""
        llm_models = [
            "EleutherAI/gpt-j-6B",  # Best quality
            "EleutherAI/gpt-neo-2.7B",  # Good balance
            "microsoft/DialoGPT-large",  # Conversational
            "gpt2-large",  # Fast fallback
            "distilgpt2"  # Fastest fallback
        ]

        for model_name in llm_models:
            try:
                script = await self._generate_with_specific_llm(prompt, style, model_name)
                if script and len(script) > 100:  # Decent length
                    logger.info(f"Generated script using {model_name}")
                    return script
            except Exception as e:
                logger.warning(f"Failed with {model_name}: {e}")
                continue

        # Ultimate fallback
        return self._create_fallback_script(prompt, style)

    async def _generate_with_specific_llm(self, prompt: str, style: str, model_name: str) -> str:
        """Generate script with a specific LLM."""
        try:
            if model_name not in self.models_loaded:
                tokenizer = AutoTokenizer.from_pretrained(self.model_configs[model_name]["tokenizer"])
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_configs[model_name]["model"],
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None
                )
                self.models_loaded[model_name] = (tokenizer, model)

            tokenizer, model = self.models_loaded[model_name]

            style_prompts = {
                "cinematic": "Write a dramatic, cinematic video script about",
                "educational": "Write an informative, educational video script about",
                "entertainment": "Write a fun, entertaining video script about",
                "news": "Write a breaking news style video script about",
                "tutorial": "Write a step-by-step tutorial video script about"
            }

            base_prompt = style_prompts.get(style, "Write a viral video script about")
            full_prompt = f"{base_prompt}: {prompt}\n\nScript:"

            inputs = tokenizer(full_prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = model.generate(
                    inputs.input_ids,
                    max_length=300,
                    num_return_sequences=1,
                    temperature=0.8,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    no_repeat_ngram_size=3
                )

            script = tokenizer.decode(outputs[0], skip_special_tokens=True)
            script = script.replace(full_prompt, "").strip()

            # Clean up the script
            script = self._clean_generated_script(script)

            return script

        except Exception as e:
            logger.error(f"Error with {model_name}: {e}")
            raise

    def _clean_generated_script(self, script: str) -> str:
        """Clean and format generated script."""
        # Remove common artifacts
        script = script.replace("Script:", "").replace("Video Script:", "").strip()

        # Split into sentences and clean
        sentences = [s.strip() for s in script.split('.') if s.strip()]
        sentences = [s for s in sentences if len(s) > 10]  # Remove very short fragments

        # Join back
        clean_script = '. '.join(sentences[:10])  # Limit to 10 sentences

        if not clean_script.endswith('.'):
            clean_script += '.'

        return clean_script if len(clean_script) > 50 else script

    def _create_fallback_script(self, prompt: str, style: str) -> str:
        """Create a fallback script when AI fails."""
        style_templates = {
            "cinematic": f"In a world of endless possibilities, discover the incredible story of {prompt}. This groundbreaking phenomenon is changing everything we know about innovation and creativity.",
            "educational": f"Today we're diving deep into the fascinating world of {prompt}. Understanding this topic is crucial for anyone interested in staying ahead of the curve.",
            "entertainment": f"Get ready for an amazing journey through the exciting world of {prompt}! You won't believe what we're about to discover together.",
            "news": f"Breaking news: Major developments in {prompt} are shaking up the industry. Here's everything you need to know about this game-changing story.",
            "tutorial": f"Welcome to our comprehensive guide on {prompt}. Whether you're a beginner or expert, this step-by-step tutorial will teach you everything you need to know."
        }

        return style_templates.get(style, f"Discover the amazing world of {prompt}. This incredible topic has the potential to change everything!")

    async def _generate_images_comprehensive(self, prompt: str, script: str, duration: int, style: str) -> List[str]:
        """Generate images using multiple Stable Diffusion models."""
        sd_models = [
            "stabilityai/stable-diffusion-2-1",  # Best quality
            "runwayml/stable-diffusion-v1-5",   # Good balance
            "CompVis/stable-diffusion-v1-4",    # Fast fallback
        ]

        for model_name in sd_models:
            try:
                images = await self._generate_with_specific_sd_model(prompt, script, duration, style, model_name)
                if images and len(images) > 0:
                    logger.info(f"Generated {len(images)} images using {model_name}")
                    return images
            except Exception as e:
                logger.warning(f"Failed with {model_name}: {e}")
                continue

        # Fallback to simple images
        return await self._generate_fallback_images(duration)

    async def _generate_with_specific_sd_model(self, prompt: str, script: str, duration: int, style: str, model_name: str) -> List[str]:
        """Generate images with a specific Stable Diffusion model."""
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

            # Create style-specific prompts
            style_modifiers = {
                "cinematic": "cinematic, movie scene, dramatic lighting, professional cinematography, 4k",
                "educational": "clean, professional, educational, informative, clear, well-lit",
                "entertainment": "vibrant, fun, colorful, energetic, engaging, dynamic",
                "news": "professional, news broadcast, serious, informative, clean",
                "tutorial": "step-by-step, clear, instructional, professional, educational"
            }

            modifier = style_modifiers.get(style, "professional, high quality")

            # Split script into segments
            segments = self._split_text_smart(script, duration // 3)
            images = []

            for i, segment in enumerate(segments):
                # Create detailed prompt
                image_prompt = f"{modifier}, {segment}, {prompt}, detailed, high resolution"

                # Add negative prompt for better quality
                negative_prompt = "blurry, low quality, distorted, ugly, poorly drawn, cartoon, anime, text, watermark"

                with torch.no_grad():
                    image = pipeline(
                        prompt=image_prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=25,
                        guidance_scale=7.5,
                        height=512,
                        width=512
                    ).images[0]

                # Save image
                output_dir = Path("/tmp/ai_images")
                output_dir.mkdir(exist_ok=True)
                image_path = output_dir / f"sd_{model_name.split('/')[-1]}_{i:03d}.png"
                image.save(image_path)
                images.append(str(image_path))

                # Small delay to prevent GPU memory issues
                await asyncio.sleep(0.5)

            return images

        except Exception as e:
            logger.error(f"Error with {model_name}: {e}")
            raise

    async def _generate_fallback_images(self, duration: int) -> List[str]:
        """Generate simple fallback images."""
        images = []
        num_images = max(3, duration // 3)

        for i in range(num_images):
            # Create colored gradient images
            img = np.zeros((512, 512, 3), dtype=np.uint8)

            # Different colors for each image
            colors = [
                (255, 100, 100), (100, 255, 100), (100, 100, 255),
                (255, 255, 100), (255, 100, 255), (100, 255, 255)
            ]
            color = colors[i % len(colors)]

            # Create gradient
            for y in range(512):
                for x in range(512):
                    img[y, x] = [
                        int(color[0] * (y / 512)),
                        int(color[1] * (x / 512)),
                        int(color[2] * 0.5)
                    ]

            output_dir = Path("/tmp/ai_images")
            output_dir.mkdir(exist_ok=True)
            image_path = output_dir / f"fallback_{i:03d}.png"
            cv2.imwrite(str(image_path), img)
            images.append(str(image_path))

        return images

    async def _generate_voiceover_comprehensive(self, script: str, style: str) -> str:
        """Generate voiceover using multiple TTS options."""
        # Try Edge TTS first (highest quality)
        try:
            return await self._generate_voiceover_edge_tts(script, style)
        except Exception as e:
            logger.warning(f"Edge TTS failed: {e}")

        # Try Coqui TTS
        try:
            return await self._generate_voiceover_coqui(script, style)
        except Exception as e:
            logger.warning(f"Coqui TTS failed: {e}")

        # Fallback to silent audio
        return "/tmp/silent.mp3"

    async def _generate_voiceover_edge_tts(self, script: str, style: str) -> str:
        """Generate voiceover using Edge TTS with style-specific voices."""
        try:
            output_dir = Path("/tmp/audio")
            output_dir.mkdir(exist_ok=True)
            audio_path = output_dir / f"voiceover_{style}_{int(asyncio.get_event_loop().time())}.mp3"

            # Choose voice based on style
            voice_mapping = {
                "cinematic": "en-US-AriaRUS",      # Dramatic female voice
                "educational": "en-US-ZiraRUS",    # Professional female voice
                "entertainment": "en-US-BenjaminRUS", # Energetic male voice
                "news": "en-GB-SoniaRUS",          # Authoritative British voice
                "tutorial": "en-US-AriaRUS"        # Clear female voice
            }

            voice = voice_mapping.get(style, "en-US-AriaRUS")

            # Adjust speech rate based on style
            rate_mapping = {
                "cinematic": "-10%",     # Slightly slower for drama
                "educational": "+0%",    # Normal speed
                "entertainment": "+10%", # Slightly faster for energy
                "news": "-5%",          # Slightly slower for authority
                "tutorial": "+0%"       # Normal for clarity
            }

            rate = rate_mapping.get(style, "+0%")

            communicate = edge_tts.Communicate(script, voice, rate=rate)
            await communicate.save(str(audio_path))

            return str(audio_path)

        except Exception as e:
            logger.error(f"Edge TTS voiceover failed: {e}")
            raise

    async def _generate_voiceover_coqui(self, script: str, style: str) -> str:
        """Generate voiceover using Coqui TTS."""
        try:
            # This would require Coqui TTS to be installed
            # For production deployment, uncomment and install coqui-tts

            output_dir = Path("/tmp/audio")
            output_dir.mkdir(exist_ok=True)
            audio_path = output_dir / f"coqui_{style}_{int(asyncio.get_event_loop().time())}.wav"

            # Placeholder - implement Coqui TTS here
            # from TTS.api import TTS
            # tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
            # tts.tts_to_file(text=script, file_path=str(audio_path))

            # For now, create silent audio
            silent_audio = AudioFileClip(filename=None, duration=len(script.split()) * 0.1)
            silent_audio.write_audiofile(str(audio_path), verbose=False, logger=None)

            return str(audio_path)

        except Exception as e:
            logger.error(f"Coqui TTS voiceover failed: {e}")
            raise

    async def _create_video_comprehensive(self, image_paths: List[str], audio_path: str, duration: int, style: str) -> str:
        """Create video with style-specific effects."""
        try:
            output_dir = Path("/tmp/videos")
            output_dir.mkdir(exist_ok=True)
            video_path = output_dir / f"comprehensive_{style}_{int(asyncio.get_event_loop().time())}.mp4"

            # Create clips based on style
            clips = []
            image_duration = duration / len(image_paths)

            for i, image_path in enumerate(image_paths):
                if Path(image_path).exists():
                    clip = ImageClip(image_path, duration=image_duration)

                    # Apply style-specific effects
                    if style == "cinematic":
                        # Add dramatic zoom and fade effects
                        clip = self._apply_cinematic_effects(clip, i, len(image_paths))
                    elif style == "educational":
                        # Clean, professional transitions
                        clip = self._apply_educational_effects(clip, i, len(image_paths))
                    elif style == "entertainment":
                        # Fun, dynamic effects
                        clip = self._apply_entertainment_effects(clip, i, len(image_paths))

                    clips.append(clip)

            if not clips:
                raise Exception("No valid image clips created")

            # Concatenate clips
            video_clip = concatenate_videoclips(clips, method="compose")

            # Add audio
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
                    logger.warning(f"Failed to add audio: {e}")

            # Write video with style-specific settings
            codec_settings = self._get_codec_settings(style)

            video_clip.write_videofile(
                str(video_path),
                fps=24,
                codec=codec_settings["codec"],
                audio_codec=codec_settings["audio_codec"],
                bitrate=codec_settings["bitrate"],
                verbose=False,
                logger=None
            )

            return str(video_path)

        except Exception as e:
            logger.error(f"Comprehensive video creation failed: {e}")
            raise

    def _apply_cinematic_effects(self, clip: ImageClip, index: int, total: int) -> ImageClip:
        """Apply cinematic effects to clip."""
        # Add fade transitions
        if index > 0:
            clip = clip.fadein(1.0)
        if index < total - 1:
            clip = clip.fadeout(1.0)

        # Add subtle zoom effect
        clip = clip.resize(lambda t: 1 + 0.05 * (t / clip.duration))

        return clip

    def _apply_educational_effects(self, clip: ImageClip, index: int, total: int) -> ImageClip:
        """Apply educational effects to clip."""
        # Clean crossfade transitions
        if index > 0:
            clip = clip.fadein(0.5)
        if index < total - 1:
            clip = clip.fadeout(0.5)

        return clip

    def _apply_entertainment_effects(self, clip: ImageClip, index: int, total: int) -> ImageClip:
        """Apply entertainment effects to clip."""
        # Quick cuts with bounce effect
        if index > 0:
            clip = clip.fadein(0.2)
        if index < total - 1:
            clip = clip.fadeout(0.2)

        # Add slight rotation for fun effect
        clip = clip.rotate(lambda t: 2 * np.sin(2 * np.pi * t / clip.duration))

        return clip

    def _get_codec_settings(self, style: str) -> Dict[str, str]:
        """Get codec settings based on style."""
        settings = {
            "cinematic": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "8000k"
            },
            "educational": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "4000k"
            },
            "entertainment": {
                "codec": "libx264",
                "audio_codec": "aac",
                "bitrate": "6000k"
            }
        }

        return settings.get(style, settings["educational"])

    async def _enhance_video_comprehensive(self, video_path: str, style: str) -> str:
        """Apply final video enhancements."""
        try:
            enhanced_path = video_path.replace(".mp4", "_enhanced.mp4")

            # For now, just copy (enhancements would require more processing)
            import shutil
            shutil.copy2(video_path, enhanced_path)

            # Future enhancements:
            # - Color grading
            # - Stabilization
            # - Noise reduction
            # - Subtitle addition

            return enhanced_path

        except Exception as e:
            logger.error(f"Video enhancement failed: {e}")
            return video_path

    async def _generate_fallback_video(self, prompt: str, duration: int) -> str:
        """Generate a basic fallback video."""
        try:
            output_dir = Path("/tmp/videos")
            output_dir.mkdir(exist_ok=True)
            video_path = output_dir / f"fallback_{int(asyncio.get_event_loop().time())}.mp4"

            # Create a simple text-based video
            words = prompt.split()
            clips = []

            for i, word in enumerate(words[:min(10, len(words))]):
                # Create text clip
                txt_clip = TextClip(
                    word,
                    fontsize=100,
                    color='white',
                    bg_color='black',
                    size=(1920, 1080),
                    font='Arial-Bold'
                ).set_duration(1.0)

                # Add some basic animation
                txt_clip = txt_clip.resize(lambda t: 1 + 0.2 * np.sin(2 * np.pi * t))
                clips.append(txt_clip)

            if clips:
                video_clip = concatenate_videoclips(clips, method="compose")
                video_clip.write_videofile(
                    str(video_path),
                    fps=24,
                    codec="libx264",
                    verbose=False,
                    logger=None
                )
                return str(video_path)
            else:
                raise Exception("No clips created")

        except Exception as e:
            logger.error(f"Fallback video generation failed: {e}")
            raise

    def _split_text_smart(self, text: str, num_segments: int) -> List[str]:
        """Smart text splitting that preserves sentence boundaries."""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        sentences = [s + '.' for s in sentences if not s.endswith('.')]

        if len(sentences) <= num_segments:
            # Pad with empty strings if needed
            while len(sentences) < num_segments:
                sentences.append("")
            return sentences

        # Group sentences into segments
        segment_size = len(sentences) // num_segments
        segments = []

        for i in range(num_segments):
            start = i * segment_size
            end = (i + 1) * segment_size if i < num_segments - 1 else len(sentences)
            segment = " ".join(sentences[start:end])
            segments.append(segment)

        return segments

    async def _unload_all_models(self):
        """Unload all loaded models to free memory."""
        try:
            for model_name, model_data in self.models_loaded.items():
                try:
                    if hasattr(model_data, 'to'):
                        # Single model
                        model_data.to('cpu')
                    elif isinstance(model_data, tuple):
                        # Tokenizer and model tuple
                        tokenizer, model = model_data
                        model.to('cpu')
                    elif hasattr(model_data, 'device'):
                        # Pipeline
                        model_data.to('cpu')
                except Exception as e:
                    logger.warning(f"Error unloading {model_name}: {e}")

            self.models_loaded.clear()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("All comprehensive AI models unloaded")

        except Exception as e:
            logger.error(f"Error unloading models: {e}")

    async def generate_captions(self, video_description: str, style: str = "general") -> Dict[str, Any]:
        """Generate captions and hashtags using comprehensive AI."""
        try:
            # Try multiple LLMs for caption generation
            caption_models = [
                "EleutherAI/gpt-j-6B",
                "EleutherAI/gpt-neo-2.7B",
                "microsoft/DialoGPT-large",
                "gpt2-large"
            ]

            for model_name in caption_models:
                try:
                    result = await self._generate_captions_with_model(video_description, style, model_name)
                    if result and result.get("captions"):
                        return result
                except Exception as e:
                    logger.warning(f"Caption generation failed with {model_name}: {e}")
                    continue

            # Fallback
            return self._create_fallback_captions(video_description, style)

        except Exception as e:
            logger.error(f"Comprehensive caption generation failed: {e}")
            return self._create_fallback_captions(video_description, style)

    async def _generate_captions_with_model(self, video_description: str, style: str, model_name: str) -> Dict[str, Any]:
        """Generate captions with a specific model."""
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

            style_prompts = {
                "cinematic": "Write dramatic, cinematic captions for a movie trailer about",
                "educational": "Write informative, educational captions for a documentary about",
                "entertainment": "Write fun, engaging captions for an entertainment video about",
                "news": "Write serious, informative captions for a news video about",
                "tutorial": "Write clear, instructional captions for a tutorial about"
            }

            base_prompt = style_prompts.get(style, "Write engaging captions for a video about")
            prompt = f"{base_prompt}: {video_description}\n\nCaptions:\n1."

            inputs = tokenizer(prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = model.generate(
                    inputs.input_ids,
                    max_length=200,
                    num_return_sequences=1,
                    temperature=0.8,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )

            captions_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            captions_text = captions_text.replace(prompt, "").strip()

            # Parse captions and hashtags
            lines = captions_text.split('\n')
            captions = []
            hashtags = []

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Remove numbering
                    line = line.lstrip('123456789. ')
                    if line:
                        captions.append(line)
                elif line.startswith('#'):
                    hashtags.append(line)

            # Generate additional hashtags if needed
            if len(hashtags) < 5:
                hashtags.extend(self._generate_hashtags_from_description(video_description))

            return {
                "captions": captions[:3],
                "hashtags": hashtags[:15]
            }

        except Exception as e:
            logger.error(f"Caption generation with {model_name} failed: {e}")
            raise

    def _generate_hashtags_from_description(self, description: str) -> List[str]:
        """Generate hashtags from description."""
        words = description.lower().split()
        hashtags = []

        # Add common viral hashtags
        base_hashtags = ["#viral", "#video", "#content", "#amazing", "#awesome"]

        # Add description-based hashtags
        for word in words[:5]:
            if len(word) > 3:
                hashtags.append(f"#{word}")

        return base_hashtags + hashtags

    def _create_fallback_captions(self, video_description: str, style: str) -> Dict[str, Any]:
        """Create fallback captions when AI fails."""
        style_captions = {
            "cinematic": [
                f"In a world of endless possibilities, witness the incredible story of {video_description}!",
                f"A groundbreaking phenomenon that's changing everything we know!",
                f"Prepare to be amazed by this incredible journey!"
            ],
            "educational": [
                f"Discover the fascinating world of {video_description}!",
                f"Learn everything you need to know about this important topic!",
                f"Understanding {video_description} is crucial for staying informed!"
            ],
            "entertainment": [
                f"Get ready for an amazing adventure through {video_description}!",
                f"You won't believe what we're about to discover together!",
                f"This is going to be absolutely incredible!"
            ]
        }

        captions = style_captions.get(style, [
            f"Amazing content about {video_description}!",
            f"You won't want to miss this incredible video!",
            f"Discover something truly remarkable!"
        ])

        return {
            "captions": captions,
            "hashtags": ["#viral", "#video", "#content", "#amazing", "#awesome", f"#{video_description.replace(' ', '')}"]
        }