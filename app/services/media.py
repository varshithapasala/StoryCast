import json
import math
import shutil
import subprocess
import wave
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: dict, target: Path) -> float: ...


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return float(result.stdout.strip())


class HuggingFaceKokoroProvider(TTSProvider):
    def synthesize(self, text, voice, target):
        from huggingface_hub import InferenceClient

        settings = get_settings()
        if not settings.hf_token:
            raise RuntimeError("HF_TOKEN is required for hosted Kokoro narration")
        language = voice.get("language", "en")
        voice_name = voice.get("name") or (settings.kokoro_voice_hi if language == "hi" else settings.kokoro_voice_en)
        client = InferenceClient(provider=settings.hf_tts_provider, api_key=settings.hf_token)
        audio = client.text_to_speech(
            text,
            model=settings.hf_tts_model,
            extra_body={"voice": voice_name, "speed": float(voice.get("speed", 1))},
        )
        target.write_bytes(audio)
        return _duration(target)


class MockToneProvider(TTSProvider):
    """Deterministic test fixture, available only when ALLOW_MOCK_MEDIA=true."""

    def synthesize(self, text, voice, target):
        duration = max(3, min(90, len(text.split()) / 2.5))
        rate = 16000
        with wave.open(str(target), "wb") as output:
            output.setparams((1, 2, rate, int(duration * rate), "NONE", ""))
            frames = bytearray()
            for index in range(int(duration * rate)):
                value = int(1400 * math.sin(2 * math.pi * 220 * index / rate))
                frames.extend(value.to_bytes(2, "little", signed=True))
            output.writeframes(frames)
        return duration


def tts_provider(name: str | None = None):
    settings = get_settings()
    selected = name or settings.tts_provider
    if selected == "mock" and settings.allow_mock_media:
        return MockToneProvider()
    if selected != "huggingface":
        raise ValueError("TTS_PROVIDER must be 'huggingface'")
    return HuggingFaceKokoroProvider()


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def make_captions(script: str, duration: float, target: Path) -> list[dict]:
    words = script.split()
    phrases = [" ".join(words[index:index + 7]) for index in range(0, len(words), 7)]
    weight = sum(len(phrase.split()) for phrase in phrases) or 1
    cursor = 0.0
    captions = []
    for index, phrase in enumerate(phrases):
        length = duration * len(phrase.split()) / weight
        captions.append({"id": index + 1, "text": phrase, "start": round(cursor, 3), "end": round(cursor + length, 3)})
        cursor += length
    target.write_text(json.dumps(captions, ensure_ascii=False, indent=2), encoding="utf-8")
    blocks = [f"{item['id']}\n{_srt_time(item['start'])} --> {_srt_time(item['end'])}\n{item['text']}" for item in captions]
    target.with_suffix(".srt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return captions


def _run_ffmpeg(command: list[str], timeout: int = 900) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required and was not found in PATH")
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-3000:]}")


def _subtitle_filter(path: Path) -> str:
    escaped = str(path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    return f"subtitles='{escaped}':force_style='FontName=Arial,FontSize=18,Outline=2,Shadow=1,Alignment=2,MarginV=90'"


def render_video(project: dict, audio: Path, captions: Path, clips: list[Path], target: Path, duration: float) -> None:
    if not clips:
        raise ValueError("At least one generated scene clip is required")
    settings = get_settings()
    scenes = project.get("scenes") or []
    requested = [max(1.0, float(scene.get("duration_seconds", 5))) for scene in scenes[:len(clips)]]
    requested.extend([5.0] * (len(clips) - len(requested)))
    scale = duration / sum(requested)
    normalized = []
    video_filter = (
        f"scale={settings.output_width}:{settings.output_height}:force_original_aspect_ratio=increase,"
        f"crop={settings.output_width}:{settings.output_height},fps={settings.output_fps}"
    )
    for index, (clip, seconds) in enumerate(zip(clips, requested)):
        segment = target.parent / f"segment-{index:03}.mp4"
        _run_ffmpeg([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(clip), "-t", f"{seconds * scale:.3f}",
            "-an", "-vf", video_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", str(segment),
        ])
        normalized.append(segment)
    concat_file = target.parent / "scene-clips.txt"
    concat_file.write_text("\n".join(f"file '{path.resolve().as_posix()}'" for path in normalized), encoding="utf-8")
    silent = target.parent / "visuals.mp4"
    _run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent)])
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", str(silent), "-i", str(audio), "-vf", _subtitle_filter(captions.with_suffix(".srt")),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(target),
    ])
