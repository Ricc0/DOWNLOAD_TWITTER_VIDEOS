from twitter_video.paths import download_directory, output_template
from twitter_video.models import DownloadResult, Outcome, RunSummary


def test_download_directory_creates_twitter_videos_below_downloads(tmp_path):
    target = download_directory(tmp_path)

    assert target == tmp_path / "Downloads" / "Twitter_Videos"
    assert target.is_dir()


def test_output_template_uses_author_post_id_and_media_position(tmp_path):
    assert output_template(tmp_path).endswith(
        "%(uploader_id)s_%(id)s_%(playlist_index)02d.%(ext)s"
    )


def test_run_summary_counts_completed_skipped_and_failed_results():
    summary = RunSummary.from_results(
        [
            DownloadResult("a", Outcome.COMPLETED, "done"),
            DownloadResult("b", Outcome.SKIPPED, "exists"),
            DownloadResult("c", Outcome.FAILED, "unavailable"),
        ]
    )

    assert (summary.completed, summary.skipped, summary.failed) == (1, 1, 1)
