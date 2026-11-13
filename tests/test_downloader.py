import pytest
from yt_dlp.utils import DownloadError

import twitter_video.downloader as downloader
from twitter_video.downloader import FfmpegMissingError, download_post, ensure_ffmpeg_available
from twitter_video.models import Outcome, UrlRequest


def test_ensure_ffmpeg_available_raises_before_downloading_when_not_on_path(monkeypatch):
    monkeypatch.setattr(downloader.shutil, "which", lambda name: None)

    with pytest.raises(FfmpegMissingError, match="ffmpeg"):
        ensure_ffmpeg_available()


def test_download_post_uses_best_mp4_merge_and_never_overwrites(monkeypatch, tmp_path):
    captured = {}

    class RecordingYoutubeDl:
        def __init__(self, options):
            captured.update(options)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def download(self, urls):
            captured["urls"] = urls
            return 0

    monkeypatch.setattr(downloader, "YoutubeDL", RecordingYoutubeDl)

    result = download_post(UrlRequest("https://x.com/a/status/1", None), tmp_path)

    assert result.outcome is Outcome.COMPLETED
    assert captured["format"] == "bv*+ba/b"
    assert captured["merge_output_format"] == "mp4"
    assert captured["noplaylist"] is True
    assert captured["nooverwrites"] is True
    assert "%(uploader_id)s_%(id)s_%(playlist_index)02d.%(ext)s" in captured[
        "outtmpl"
    ]
    assert captured["urls"] == ["https://x.com/a/status/1"]


def test_download_post_returns_failed_result_for_extractor_error(monkeypatch, tmp_path):
    class FailingYoutubeDl:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def download(self, urls):
            raise DownloadError("Private post")

    monkeypatch.setattr(downloader, "YoutubeDL", FailingYoutubeDl)

    result = download_post(UrlRequest("https://x.com/a/status/1", None), tmp_path)

    assert result.outcome is Outcome.FAILED
    assert "Private post" in result.message


def test_download_post_skips_when_yt_dlp_reports_an_existing_file(monkeypatch, tmp_path):
    class ExistingFileYoutubeDl:
        def __init__(self, options):
            self.progress_hooks = options["progress_hooks"]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def download(self, urls):
            self.progress_hooks[0](
                {
                    "status": "finished",
                    "filename": str(tmp_path / "existing.mp4"),
                    "total_bytes": 123,
                }
            )
            return 0

    monkeypatch.setattr(downloader, "YoutubeDL", ExistingFileYoutubeDl)

    result = download_post(UrlRequest("https://x.com/a/status/1", None), tmp_path)

    assert result.outcome is Outcome.SKIPPED
    assert result.message == "Already downloaded"


def test_download_post_skips_when_yt_dlp_checks_existing_merged_output(
    monkeypatch, tmp_path
):
    class ExistingMergedOutputYoutubeDl:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def report_file_already_downloaded(self, filename):
            self.reported_filename = filename

        def download(self, urls):
            self.report_file_already_downloaded(str(tmp_path / "existing.mp4"))
            return 0

    monkeypatch.setattr(downloader, "YoutubeDL", ExistingMergedOutputYoutubeDl)

    result = download_post(UrlRequest("https://x.com/a/status/1", None), tmp_path)

    assert result.outcome is Outcome.SKIPPED
    assert result.message == "Already downloaded"


def test_download_post_limits_extraction_to_x_media_and_reports_return_code(
    monkeypatch, tmp_path
):
    captured = {}

    class FailingReturnCodeYoutubeDl:
        def __init__(self, options):
            captured.update(options)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def download(self, urls):
            return 1

    monkeypatch.setattr(downloader, "YoutubeDL", FailingReturnCodeYoutubeDl)

    result = download_post(UrlRequest("https://x.com/a/status/1", None), tmp_path)

    assert captured["allowed_extractors"] == ["twitter"]
    assert result.outcome is Outcome.FAILED
    assert result.message == "yt-dlp reported an error."
