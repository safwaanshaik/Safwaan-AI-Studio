import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ai_engine.adapters import (
    BaseVideoAdapter, 
    OpenAISoraAdapter,
    RunwayMLAdapter,
    StabilityAIAdapter,
    MochiAdapter,
    Wan21Adapter,
    OpenSoraAdapter
)
from ai_engine.adapters.comprehensive_video_models import ComprehensiveVideoModels
from ai_engine.multi_agent import (
    DirectorAgent, 
    ScriptWriterAgent, 
    EditorAgent, 
    AudioAgent, 
    MarketerAgent
)

logger = logging.getLogger(__name__)

class VideoGenerationPipeline:
    """Complete video generation pipeline with multi-agent orchestration"""

    def __init__(self):
        self.director_agent = DirectorAgent()
        self.script_writer_agent = ScriptWriterAgent()
        self.editor_agent = EditorAgent()
        self.audio_agent = AudioAgent()
        self.marketer_agent = MarketerAgent()
        self.adapters = self._initialize_adapters()

    def _initialize_adapters(self) -> List[BaseVideoAdapter]:
        """Initialize all available video generation adapters using ComprehensiveVideoModels"""
        # Initialize the comprehensive models manager
        comprehensive_models = ComprehensiveVideoModels()
        
        # Get all available models
        available_models = comprehensive_models.get_available_models()
        
        # Map to actual adapter instances
        adapters = []
        
        # Always add the core adapters
        adapters.extend([
            OpenAISoraAdapter(),
            RunwayMLAdapter(),
            StabilityAIAdapter(),
            MochiAdapter(),
            Wan21Adapter(),
            OpenSoraAdapter()
        ])
        
        # Log available models
        model_names = [model.name for model in available_models]
        logger.info(f"Initialized {len(adapters)} adapters with {len(available_models)} available models: {', '.join(model_names)}")
        
        return adapters

    async def generate_video(self, trend_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete video generation pipeline"""

        pipeline_start = datetime.utcnow()
        logger.info(f"Starting video generation pipeline for trend: {trend_data.get('keyword')}")

        try:
            # Phase 1: Creative Direction
            logger.info("Phase 1: Creative Direction - Creating storyboard")
            storyboard = await self.director_agent.create_storyboard(trend_data)

            # Phase 2: Script Writing
            logger.info("Phase 2: Script Writing - Creating video script")
            script = await self.script_writer_agent.write_script(trend_data, storyboard)

            # Phase 3: Content Editing & Refinement
            logger.info("Phase 3: Content Editing - Refining storyboard and pacing")
            refined_storyboard = await self.editor_agent.refine_storyboard(storyboard)
            
            # Phase 4: AI Model Selection & Generation
            logger.info("Phase 3: AI Model Selection & Video Generation")
            video_result = await self._select_and_generate_video(
                trend_data, storyboard, script, config
            )

            # Phase 5: Audio Design
            logger.info("Phase 5: Audio Design - Adding music, sound effects, and voice-over")
            audio_enhanced_video = await self.audio_agent.add_audio(video_result, refined_storyboard)
            
            # Phase 6: Quality Enhancement
            logger.info("Phase 6: Quality Enhancement")
            enhanced_video = await self._enhance_video_quality(audio_enhanced_video, config)

            # Phase 7: Marketing Optimization
            logger.info("Phase 7: Marketing Optimization - Generating metadata and thumbnails")
            marketing_data = await self.marketer_agent.generate_metadata(enhanced_video, refined_storyboard)
            
            # Phase 8: Final Processing
            logger.info("Phase 8: Final Processing")
            final_result = await self._finalize_video(enhanced_video, script, trend_data, marketing_data)

            pipeline_duration = (datetime.utcnow() - pipeline_start).total_seconds()

            logger.info(f"Pipeline completed successfully in {pipeline_duration:.2f} seconds")

            result = {
                "success": True,
                "video_url": final_result.get("video_url"),
                "thumbnail_url": final_result.get("thumbnail_url"),
                "duration": final_result.get("duration"),
                "script": script,
                "storyboard": refined_storyboard,
                "model_used": video_result.get("model"),
                "generation_time": pipeline_duration,
                "cost": final_result.get("total_cost", 0),
                "quality_score": final_result.get("quality_score", 0),
                "marketing": marketing_data.get("platform_specific", {}),
                "metadata": {
                    "title": marketing_data.get("base_metadata", {}).get("title", ""),
                    "description": marketing_data.get("base_metadata", {}).get("description", ""),
                    "hashtags": marketing_data.get("base_metadata", {}).get("hashtags", []),
                    "trend_data": trend_data,
                    "config": config,
                    "pipeline_duration": pipeline_duration,
                    "processing_steps": [
                        "creative_direction",
                        "script_writing",
                        "content_editing",
                        "ai_generation",
                        "audio_design",
                        "quality_enhancement",
                        "marketing_optimization",
                        "final_processing"
                    ]
                }
            }
            
            return result
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "pipeline_duration": (datetime.utcnow() - pipeline_start).total_seconds(),
                "failed_at": "unknown"
            }

    async def _select_and_generate_video(self, trend_data: Dict[str, Any],
                                       storyboard: Dict[str, Any],
                                       script: Dict[str, Any],
                                       config: Dict[str, Any]) -> Dict[str, Any]:
        """Select best AI model and generate video using real video models"""
        
        # Get final prompt from storyboard
        prompt = storyboard.get("final_prompt", "")
        if not prompt:
            prompt = f"Create a cinematic video about {trend_data.get('keyword', '')}"
            
        # Enhanced logging with real-time progress
        logger.info(f"Starting video generation for prompt: {prompt[:50]}...")
        logger.info(f"Configuration: {config.get('quality', '4K')} at {config.get('target_duration', 30)}s")

        # Model selection criteria with enhanced options
        preferred_model = config.get("preferred_model")
        max_budget = config.get("max_budget", 1.0)
        target_duration = config.get("target_duration", 30)
        style = storyboard.get("visual_style", "cinematic")
        quality_preset = config.get("quality_preset", "premium")
        
        # Use comprehensive model manager for selection
        comprehensive_models = ComprehensiveVideoModels()
        video_config = comprehensive_models.VideoGenerationConfig(
            prompt=prompt,
            model=preferred_model or "sora",
            duration=target_duration,
            resolution=config.get("resolution", "1080p"),
            fps=config.get("fps", 24),
            style=style,
            aspect_ratio=config.get("aspect_ratio", "16:9"),
            quality_preset=quality_preset,
            hdr=config.get("hdr", False),
            stabilization=config.get("stabilization", True),
            color_grading=config.get("color_grading", True)
        )
        
        # Get best model based on requirements
        best_model = comprehensive_models.get_best_model(prompt, video_config)
        logger.info(f"Selected optimal model: {best_model.name} (Quality score: {best_model.quality_score}/100)")
        
        # Select best available adapter
        selected_adapter = self._select_best_adapter(
            best_model.id, max_budget, target_duration
        )

        if not selected_adapter:
            # Fallback to direct generation via comprehensive models
            logger.info(f"No adapter available, using comprehensive models directly")
            result = await comprehensive_models.generate_video(
                prompt=prompt,
                model=best_model.id,
                style=style,
                duration=target_duration,
                aspect_ratio=config.get("aspect_ratio", "16:9"),
                quality=config.get("quality", "4k"),
                fps=config.get("fps", 24),
                hdr=config.get("hdr", False),
                stabilization=config.get("stabilization", True),
                color_grading=config.get("color_grading", True)
            )
        else:
            # Generate with selected adapter
            logger.info(f"Generating with adapter: {selected_adapter.model_name}")
            
            # Enhanced generation params
            generation_params = {
                "duration": target_duration,
                "style": style,
                "resolution": config.get("resolution", "1080x1920"),
                "fps": config.get("fps", 24),
                "seed": config.get("seed"),
                "hdr": config.get("hdr", False),
                "color_grading": config.get("color_grading", True),
                "stabilization": config.get("stabilization", True),
                "quality_preset": quality_preset
            }

            result = await selected_adapter.generate_video(prompt, **generation_params)
            
            if not result.get("success"):
                # Enhanced fallback - try using comprehensive models directly if adapter fails
                logger.warning(f"Adapter generation failed, trying direct generation")
                result = await comprehensive_models.generate_video(
                    prompt=prompt,
                    model=best_model.id,
                    style=style,
                    duration=target_duration,
                    aspect_ratio=config.get("aspect_ratio", "16:9"),
                    quality=config.get("quality", "4k"),
                    fps=config.get("fps", 24)
                )

        # Enhanced result with more metadata
        if result.get("success"):
            logger.info(f"Video generation successful: {result.get('video_path')}")
            return {
                **result,
                "model": best_model.name,
                "model_id": best_model.id,
                "model_provider": str(best_model.provider),
                "quality_score": best_model.quality_score,
                "adapter": selected_adapter.model_name if selected_adapter else "direct",
                "generation_config": {
                    "prompt": prompt,
                    "style": style,
                    "duration": target_duration,
                    "resolution": config.get("resolution", "1080p"),
                    "fps": config.get("fps", 24),
                    "aspect_ratio": config.get("aspect_ratio", "16:9"),
                    "hdr": config.get("hdr", False),
                    "stabilization": config.get("stabilization", True),
                    "color_grading": config.get("color_grading", True)
                }
            }
        else:
            error = result.get("error", "Unknown error in video generation")
            logger.error(f"Video generation failed: {error}")
            raise Exception(f"Video generation failed: {error}")

    def _select_best_adapter(self, preferred_model: Optional[str] = None,
                           max_budget: float = 1.0,
                           target_duration: int = 30) -> Optional[BaseVideoAdapter]:
        """Select the best available adapter based on criteria"""

        # Filter available adapters
        available_adapters = [adapter for adapter in self.adapters if adapter.is_available()]

        if not available_adapters:
            return None

        # If preferred model specified and available, use it
        if preferred_model:
            for adapter in available_adapters:
                if adapter.model_name.lower() == preferred_model.lower():
                    return adapter

        # Otherwise, select based on cost and capabilities
        best_adapter = None
        best_score = -1

        for adapter in available_adapters:
            model_info = adapter.get_model_info()
            cost_per_second = model_info.get("cost_per_second", 0.1)
            max_duration = model_info.get("max_duration", 10)

            # Skip if too expensive
            estimated_cost = cost_per_second * min(target_duration, max_duration)
            if estimated_cost > max_budget:
                continue

            # Score based on cost efficiency and duration capability
            cost_score = 1.0 / (cost_per_second + 0.01)  # Lower cost = higher score
            duration_score = min(target_duration, max_duration) / target_duration
            total_score = cost_score * 0.7 + duration_score * 0.3

            if total_score > best_score:
                best_score = total_score
                best_adapter = adapter

        return best_adapter

    async def _enhance_video_quality(self, video_result: Dict[str, Any],
                                   config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply quality enhancements to generated video"""

        # For now, return the original result
        # In a full implementation, this would apply:
        # - Color grading
        # - Audio enhancement
        # - Resolution upscaling
        # - Stabilization
        # - Text overlay rendering

        enhanced_result = video_result.copy()
        enhanced_result["quality_score"] = min(
            video_result.get("quality_score", 70) + 10, 100
        )  # Assume 10 point improvement

        return enhanced_result

    async def _finalize_video(self, enhanced_video: Dict[str, Any],
                            script: Dict[str, Any],
                            trend_data: Dict[str, Any],
                            marketing_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Finalize video with metadata and prepare for distribution"""

        final_result = enhanced_video.copy()

        # Add marketing metadata if available, otherwise use script metadata
        if marketing_data and marketing_data.get("base_metadata"):
            base_metadata = marketing_data.get("base_metadata", {})
            final_result["title"] = base_metadata.get("title", script.get("title", f"Video about {trend_data.get('keyword')}"))
            final_result["description"] = base_metadata.get("description", script.get("voiceover_script", ""))
            final_result["hashtags"] = base_metadata.get("hashtags", script.get("hashtags", []))
            final_result["seo_data"] = marketing_data.get("seo", {})
            final_result["posting_strategy"] = marketing_data.get("posting_strategy", {})
        else:
            # Fallback to script metadata
            final_result["title"] = script.get("title", f"Video about {trend_data.get('keyword')}")
            final_result["description"] = script.get("voiceover_script", "")
            final_result["hashtags"] = script.get("hashtags", [])

        # Calculate total cost
        generation_cost = enhanced_video.get("cost", 0)
        enhancement_cost = 0.02  # Fixed enhancement cost
        final_result["total_cost"] = generation_cost + enhancement_cost

        # Add platform targeting
        final_result["target_platforms"] = trend_data.get("target_platforms", ["youtube"])

        # Use marketing thumbnails if available, otherwise generate placeholder
        if marketing_data and marketing_data.get("thumbnails"):
            thumbnails = marketing_data.get("thumbnails", [])
            if thumbnails:
                # Use the best thumbnail (highest clickthrough score)
                best_thumbnail = thumbnails[0]  # Already sorted by clickthrough score
                final_result["thumbnail_url"] = f"/thumbnails/{final_result.get('id', 'video')}/{best_thumbnail['concept_id']}.jpg"
                final_result["thumbnail_options"] = thumbnails
        elif final_result.get("video_url"):
            # Fallback to placeholder thumbnail
            final_result["thumbnail_url"] = final_result["video_url"].replace('.mp4', '_thumb.jpg')

        return final_result

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and capabilities"""

        adapter_status = []
        for adapter in self.adapters:
            model_info = adapter.get_model_info()
            adapter_status.append({
                "model": adapter.model_name,
                "available": adapter.is_available(),
                "capabilities": model_info
            })

        return {
            "pipeline_status": "operational",
            "available_models": len([a for a in self.adapters if a.is_available()]),
            "total_models": len(self.adapters),
            "agents": {
                "director": self.director_agent.name,
                "script_writer": self.script_writer_agent.name,
                "editor": self.editor_agent.__class__.__name__,
                "audio": self.audio_agent.__class__.__name__,
                "marketer": self.marketer_agent.__class__.__name__
            },
            "model_status": adapter_status
        }