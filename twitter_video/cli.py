import argparse
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .downloader import FfmpegMissingError, download_post, ensure_ffmpeg_available
from .input import read_url_file, validate_post_url
from .models import DownloadResult, Outcome, RunSummary, UrlRequest
from .paths import download_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="twitter-video",
        description="Download videos from public X/Twitter post URLs.",
    )
    parser.add_argument("url", nargs="?", help="Public X/Twitter post URL")
    parser.add_argument("--file", type=Path, help="UTF-8 file with one post URL per line")
    parser.add_argument("--version", action="store_true", help="Show version information")
    return parser


def _print_result(result: DownloadResult) -> None:
    print(f"{result.outcome.value.title()}: {result.url} - {result.message}")


def _print_summary(results: list[DownloadResult]) -> RunSummary:
    summary = RunSummary.from_results(results)
    print(
        f"Completed: {summary.completed} | Skipped: {summary.skipped} | "
        f"Failed: {summary.failed}"
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from yt_dlp.version import __version__ as ytdlp_version

        print(f"twitter-video {__version__} | yt-dlp {ytdlp_version}")
        return 0

    if bool(args.url) == bool(args.file):
        parser.error("provide exactly one post URL or --file PATH")

    results: list[DownloadResult] = []
    if args.url:
        try:
            requests = [UrlRequest(validate_post_url(args.url), None)]
        except ValueError as error:
            print(f"Error: {error}")
            return 2
    else:
        try:
            batch = read_url_file(args.file)
        except OSError as error:
            print(f"Error reading {args.file}: {error}")
            return 2
        requests = list(batch.requests)
        for problem in batch.problems:
            line = f"line {problem.line_number}: " if problem.line_number else ""
            results.append(
                DownloadResult(problem.value, Outcome.FAILED, f"{line}{problem.message}")
            )

    if requests:
        try:
            ensure_ffmpeg_available()
        except FfmpegMissingError as error:
            print(f"Error: {error}")
            return 2
        destination = download_directory()
        for request in requests:
            results.append(download_post(request, destination))

    for result in results:
        _print_result(result)
    summary = _print_summary(results)
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
