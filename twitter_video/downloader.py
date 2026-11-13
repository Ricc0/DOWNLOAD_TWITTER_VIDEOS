import shutil
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .models import DownloadResult, Outcome, UrlRequest
from .paths import output_template


class FfmpegMissingError(RuntimeError):
    """Raised when the video/audio merger is not installed."""


def ensure_ffmpeg_available() -> None:
    """Require ffmpeg before selecting formats that may need merging."""
    if shutil.which("ffmpeg") is None:
        raise FfmpegMissingError(
            "ffmpeg is required to combine the best video and audio streams. "
            "Install ffmpeg and try again."
        )


def download_post(request: UrlRequest, destination: Path) -> DownloadResult:
    """Download all videos exposed by one public post through yt-dlp."""
    downloaded_media = False
    existing_media = False

    class TrackingYoutubeDL(YoutubeDL):
        def __init__(self, *args, **kwargs):
            self.existing_media = False
            super().__init__(*args, **kwargs)

        def report_file_already_downloaded(self, filename):
            self.existing_media = True
            return super().report_file_already_downloaded(filename)

    def record_progress(status: dict) -> None:
        nonlocal downloaded_media, existing_media
        if status.get("status") != "finished":
            return
        if "downloaded_bytes" in status:
            downloaded_media = True
        else:
            existing_media = True

    options = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "nooverwrites": True,
        "allowed_extractors": ["twitter"],
        "outtmpl": output_template(destination),
        "progress_hooks": [record_progress],
    }
    try:
        with TrackingYoutubeDL(options) as downloader:
            return_code = downloader.download([request.url])
            existing_media = existing_media or downloader.existing_media
    except DownloadError as error:
        return DownloadResult(request.url, Outcome.FAILED, str(error))
    if return_code:
        return DownloadResult(request.url, Outcome.FAILED, "yt-dlp reported an error.")
    if existing_media and not downloaded_media:
        return DownloadResult(request.url, Outcome.SKIPPED, "Already downloaded")
    return DownloadResult(request.url, Outcome.COMPLETED, "Downloaded")
