import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MV_", env_file=".env")

    upload_dir: Path = Path(__file__).resolve().parent.parent / "uploads"
    frontend_dist: Path = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    max_upload_bytes: int = 20 * 1024 * 1024

    # Audio -> frame images. Uploaded audio and generated frames live in separate temp roots.
    audio_temp_dir: Path = Path(tempfile.gettempdir()) / "music-visualizer" / "audio"
    frames_temp_dir: Path = Path(tempfile.gettempdir()) / "music-visualizer" / "frames"
    max_audio_bytes: int = 200 * 1024 * 1024
    max_frames: int = 30000
    max_windows: int = 60000  # analysis windows per submission (a tiny window spacing can create very many)
    min_window_size: int = 4096  # window sizes are the powers of 2 from min to max
    max_window_size: int = 32768
    min_frame_rate: float = 1
    max_frame_rate: float = 60
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
