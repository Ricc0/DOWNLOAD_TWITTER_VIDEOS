from pathlib import Path


def download_directory(user_profile: Path | None = None) -> Path:
    """Create and return the current user's fixed video download directory."""
    profile = user_profile if user_profile is not None else Path.home()
    destination = profile / "Downloads" / "Twitter_Videos"
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def output_template(destination: Path) -> str:
    """Return yt-dlp's deterministic output template inside *destination*."""
    return str(destination / "%(uploader_id)s_%(id)s_%(playlist_index)02d.%(ext)s")
