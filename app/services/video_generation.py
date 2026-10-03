import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


class VideoProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, target: Path, seed: int) -> None: ...


class HuggingFaceWanProvider(VideoProvider):
    def generate(self, prompt, target, seed):
        from huggingface_hub import InferenceClient

        settings = get_settings()
        if not settings.hf_token:
            raise RuntimeError("HF_TOKEN is required for hosted Wan video generation")
        client = InferenceClient(provider=settings.hf_video_provider, api_key=settings.hf_token)
        video = client.text_to_video(
            prompt,
            model=settings.hf_video_model,
            num_frames=settings.hf_video_frames,
            num_inference_steps=settings.hf_video_inference_steps,
            guidance_scale=settings.hf_video_guidance_scale,
            negative_prompt=[settings.hf_video_negative_prompt],
            seed=seed,
        )
        target.write_bytes(video)


class MockVideoProvider(VideoProvider):
    """Fast development fixture, available only when ALLOW_MOCK_MEDIA=true."""

    def generate(self, prompt, target, seed):
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x172033:s=480x832:r=24:d=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)],
            check=True,
            capture_output=True,
            timeout=120,
        )


def video_provider() -> VideoProvider:
    settings = get_settings()
    if settings.video_provider == "mock" and settings.allow_mock_media:
        return MockVideoProvider()
    if settings.video_provider != "huggingface":
        raise ValueError("VIDEO_PROVIDER must be 'huggingface'")
    return HuggingFaceWanProvider()


def generate_scene_clips(project: dict, folder: Path) -> list[Path]:
    clips = []
    provider = video_provider()
    prefix = "Editorial illustration for a news explainer, clearly synthetic, no text or logos. "
    for index, scene in enumerate(project.get("scenes") or []):
        target = folder / f"scene-{index:03}.mp4"
        if not target.exists():
            prompt = prefix + str(scene.get("visual_prompt") or scene.get("on_screen_text") or project.get("title", "News story"))
            provider.generate(prompt, target, seed=10_000 + index)
        clips.append(target)
    if not clips:
        raise ValueError("The project has no scenes to generate")
    return clips
