import os
import shutil
from pathlib import Path

from jinja2 import Template

from backend.config import settings
from backend.logging_config import get_logger

logger = get_logger("file_manager")

# Default naming templates
MOVIE_TEMPLATE = "{{ title }} ({{ year }})/{{ title }} ({{ year }}){% if quality %} - {{ quality }}{% endif %}{% if codec %} {{ codec }}{% endif %}.{{ ext }}"
TV_TEMPLATE = "{{ series_title }}/Season {{ '%02d' % season }}/{{ series_title }} - S{{ '%02d' % season }}E{{ '%02d' % episode }}{% if episode_title %} - {{ episode_title }}{% endif %}.{{ ext }}"
RECORDING_TEMPLATE = "{{ channel }} - {{ title }} - {{ date }}.ts"


def hardlink_or_copy(src: str | Path, dst: str | Path) -> bool:
    """Create a hardlink, falling back to copy if cross-device."""
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        os.link(src, dst)
        logger.info("hardlinked", src=str(src), dst=str(dst))
        return True
    except OSError:
        shutil.copy2(src, dst)
        logger.info("copied_fallback", src=str(src), dst=str(dst))
        return False


def move_file(src: str | Path, dst: str | Path) -> None:
    """Atomic move (rename if same fs, copy+delete otherwise)."""
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        src.rename(dst)
    except OSError:
        shutil.copy2(src, dst)
        src.unlink()
    logger.info("moved", src=str(src), dst=str(dst))


def render_filename(template_str: str, **kwargs) -> str:
    """Render a filename from a Jinja2 template and metadata."""
    template = Template(template_str)
    return template.render(**kwargs)


def check_disk_space(path: str | Path) -> dict:
    """Check available disk space."""
    stat = shutil.disk_usage(str(path))
    return {
        "total_bytes": stat.total,
        "used_bytes": stat.used,
        "free_bytes": stat.free,
        "free_percent": round((stat.free / stat.total) * 100, 1),
    }


def ensure_directories() -> None:
    """Create required directory structure."""
    dirs = [
        settings.config_path / "db",
        settings.config_path / "vpn",
        settings.config_path / "indexers",
        settings.config_path / "logs",
        settings.download_path / "torrents",
        settings.download_path / "usenet",
        settings.download_path / "complete",
        settings.media_path / "movies",
        settings.media_path / "tv",
        settings.media_path / "iptv-movies",
        settings.media_path / "iptv-shows",
        settings.media_path / "recordings",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
