import twitter_video.cli as cli
from twitter_video.cli import main
from twitter_video.models import DownloadResult, Outcome


def test_main_downloads_single_url_and_prints_success_summary(
    monkeypatch, capsys, tmp_path
):
    monkeypatch.setattr(cli, "download_directory", lambda: tmp_path)
    monkeypatch.setattr(cli, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(
        cli,
        "download_post",
        lambda request, destination: DownloadResult(
            request.url, Outcome.COMPLETED, "Downloaded"
        ),
    )

    assert main(["https://x.com/a/status/1"]) == 0
    assert "Completed: 1" in capsys.readouterr().out


def test_main_continues_valid_batch_after_invalid_line_and_download_failure(
    monkeypatch, capsys, tmp_path
):
    source = tmp_path / "thread.txt"
    source.write_text(
        "https://x.com/a/status/1\nbad\nhttps://x.com/a/status/2\n", encoding="utf-8"
    )
    monkeypatch.setattr(cli, "download_directory", lambda: tmp_path)
    monkeypatch.setattr(cli, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(
        cli,
        "download_post",
        lambda request, destination: DownloadResult(
            request.url,
            Outcome.FAILED if request.url.endswith("/1") else Outcome.COMPLETED,
            "result",
        ),
    )

    assert main(["--file", str(source)]) == 1
    output = capsys.readouterr().out
    assert "line 2" in output
    assert "Completed: 1" in output
    assert "Failed: 2" in output


def test_version_prints_tool_and_ytdlp_versions(capsys):
    assert main(["--version"]) == 0
    output = capsys.readouterr().out
    assert "twitter-video" in output
    assert "yt-dlp" in output


def test_print_result_uses_ascii_separator_for_windows_terminal_compatibility(capsys):
    cli._print_result(
        DownloadResult("https://x.com/a/status/1", Outcome.COMPLETED, "Downloaded")
    )

    assert (
        capsys.readouterr().out
        == "Completed: https://x.com/a/status/1 - Downloaded\n"
    )
