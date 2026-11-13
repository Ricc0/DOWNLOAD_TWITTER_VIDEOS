# Twitter Video CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and install a current-user Windows CLI that saves videos from user-supplied public X/Twitter post URLs to `Downloads\Twitter_Videos` without paid X API access.

**Architecture:** A focused Python package parses one URL or a batch file, validates public post URLs, constructs a deterministic output location, and delegates extraction to the maintained `yt-dlp` Python library. A PowerShell bootstrapper creates an isolated virtual environment below `%USERPROFILE%\.local\TwitterVideo`, provides the `twitter-video` command on the current user's PATH, and never requires elevation.

**Tech Stack:** Python 3.10+, standard-library `argparse`, `yt-dlp`, `ffmpeg` (optional system dependency when stream merging is required), pytest, PowerShell 5.1+.

**Spec:** `docs/superpowers/specs/2026-10-10-twitter-video-cli-design.md`

## Global Constraints

- Support public `x.com` and `twitter.com` post URLs only; do not implement logins, cookies, API tokens, proxying, DRM circumvention, or access-control bypass.
- A single URL downloads every video available in that post; a user-supplied text file provides the zero-cost thread workflow, one URL per non-comment line.
- Store every output under `%USERPROFILE%\Downloads\Twitter_Videos`; never overwrite an existing output file.
- Installation is current-user only under `%USERPROFILE%\.local\TwitterVideo`; do not require admin privileges or edit machine-wide PATH.
- Report each URL's result and a final summary; batch failures must not prevent remaining valid URLs from running.
- Use `yt-dlp` as an external versioned dependency and give an actionable `ffmpeg` prerequisite message when merging is needed.
- This directory is not a Git repository. Do not initialize one or fabricate commits; record verification output instead of commit steps.

## Review Focus

- A URL with `?` or `#` suffix remains accepted and sent unchanged to `yt-dlp`; cover in Task 1 URL tests.
- A batch file that combines comments, blank lines, a malformed link, and valid links still attempts every valid link; cover in Task 4 CLI integration tests.
- The current user's Downloads directory may be absent; create `Downloads\Twitter_Videos` before asking the downloader to write; cover in Task 2 path tests.
- Existing media files are skipped rather than overwritten, including during a repeated batch; cover in Task 3 downloader-option tests.
- A best-quality video/audio selection that needs muxing reports missing `ffmpeg` before starting a network transfer; cover in Task 3 adapter tests.

---

## File structure

```text
pyproject.toml                         Project metadata, runtime/development dependencies, console entry point, pytest settings
twitter_video/__init__.py              Package version
twitter_video/models.py                Immutable request/result/summary domain types
twitter_video/input.py                 X/Twitter post URL validation and batch-file parsing
twitter_video/paths.py                 Current-user download directory and deterministic output template
twitter_video/downloader.py            yt-dlp adapter, dependency checks, and per-post download outcome
twitter_video/cli.py                   argparse CLI orchestration and terminal reporting
install.ps1                            Current-user virtualenv and PATH bootstrapper
README.md                              Install, usage, batch-file, update, and limitations instructions
tests/test_input.py                    URL and batch-file parsing tests
tests/test_paths.py                    Current-user destination/template tests
tests/test_downloader.py               Mocked yt-dlp and ffmpeg behavior tests
tests/test_cli.py                      Command orchestration, continuation, summary, and exit-code tests
```

### Task 1: Package foundation and safe URL input

**Files:**
- Create: `pyproject.toml`
- Create: `twitter_video/__init__.py`
- Create: `twitter_video/models.py`
- Create: `twitter_video/input.py`
- Test: `tests/test_input.py`

**Interfaces:**
- Produces: `UrlRequest(url: str, line_number: int | None)`, `InputProblem(value: str, message: str, line_number: int | None)`, `InputBatch(requests: tuple[UrlRequest, ...], problems: tuple[InputProblem, ...])` in `models.py`.
- Produces: `validate_post_url(value: str) -> str` and `read_url_file(path: Path) -> InputBatch` in `input.py`.
- Consumed by: Task 4 uses `validate_post_url` for the positional URL and `read_url_file` for `--file`.

- [ ] **Step 1: Write failing URL-validation tests in `tests/test_input.py`**

```python
def test_validate_post_url_accepts_x_and_twitter_status_urls_with_suffixes():
    assert validate_post_url("https://x.com/jobecoffe/status/2108403966665199628?x=1#video") == \
        "https://x.com/jobecoffe/status/2108403966665199628?x=1#video"
    assert validate_post_url("https://twitter.com/user_name/status/42") == \
        "https://twitter.com/user_name/status/42"

def test_validate_post_url_rejects_non_post_url():
    with pytest.raises(ValueError, match="public X/Twitter post URL"):
        validate_post_url("https://x.com/jobecoffe")
```

- [ ] **Step 2: Run the URL tests to verify they fail**

Run: `python -m pytest tests/test_input.py -v`

Expected: FAIL because the package and `validate_post_url` do not exist.

- [ ] **Step 3: Add project metadata and URL validation**

Create `pyproject.toml` with Python floor `>=3.10`, runtime dependency `yt-dlp`, development extra `pytest`, console script `twitter-video = twitter_video.cli:main`, and pytest test path `tests`. Implement `validate_post_url(value: str) -> str` using parsed scheme/host/path validation: accept only HTTP(S), hosts `x.com`, `www.x.com`, `twitter.com`, or `www.twitter.com`, and a path whose first and third segments are `<username>/status/<numeric-id>`; preserve the original trimmed URL including query/fragment.

- [ ] **Step 4: Write failing batch-file tests in `tests/test_input.py`**

```python
def test_read_url_file_ignores_comments_and_collects_invalid_lines(tmp_path):
    source = tmp_path / "thread.txt"
    source.write_text("# thread\n\nhttps://x.com/a/status/1\nnot-a-url\nhttps://twitter.com/b/status/2\n", encoding="utf-8")

    batch = read_url_file(source)

    assert [request.url for request in batch.requests] == [
        "https://x.com/a/status/1", "https://twitter.com/b/status/2"
    ]
    assert [(problem.line_number, problem.value) for problem in batch.problems] == [(4, "not-a-url")]
```

- [ ] **Step 5: Run the batch-file test to verify it fails**

Run: `python -m pytest tests/test_input.py::test_read_url_file_ignores_comments_and_collects_invalid_lines -v`

Expected: FAIL because `read_url_file` does not exist.

- [ ] **Step 6: Implement domain types and batch parsing**

Implement frozen dataclasses in `models.py`. Implement `read_url_file(path: Path) -> InputBatch` to read UTF-8 text, ignore `line.strip() == ""` and `line.lstrip().startswith("#")`, validate each remaining line independently, append valid `UrlRequest` instances in file order, and accumulate invalid values as `InputProblem` instead of stopping the batch.

- [ ] **Step 7: Run input tests to verify they pass**

Run: `python -m pytest tests/test_input.py -v`

Expected: PASS.

### Task 2: Output paths and result aggregation

**Files:**
- Create: `twitter_video/paths.py`
- Modify: `twitter_video/models.py`
- Test: `tests/test_paths.py`

**Interfaces:**
- Consumes: `UrlRequest` from Task 1.
- Produces: `download_directory(user_profile: Path | None = None) -> Path`, `output_template(destination: Path) -> str`, `DownloadResult`, `Outcome`, and `RunSummary`.
- Consumed by: Task 3 uses destination/template and returns `DownloadResult`; Task 4 prints `RunSummary`.

- [ ] **Step 1: Write failing destination and template tests in `tests/test_paths.py`**

```python
def test_download_directory_creates_twitter_videos_below_downloads(tmp_path):
    target = download_directory(tmp_path)

    assert target == tmp_path / "Downloads" / "Twitter_Videos"
    assert target.is_dir()

def test_output_template_uses_author_post_id_and_media_position(tmp_path):
    assert output_template(tmp_path).endswith("%(uploader_id)s_%(id)s_%(playlist_index)02d.%(ext)s")
```

- [ ] **Step 2: Run path tests to verify they fail**

Run: `python -m pytest tests/test_paths.py -v`

Expected: FAIL because `paths.py` and its functions do not exist.

- [ ] **Step 3: Implement paths and outcome types**

Implement `download_directory` to resolve the supplied profile or `Path.home()`, create `Downloads/Twitter_Videos` with `parents=True, exist_ok=True`, and return it. Implement `output_template` with the exact deterministic pattern `%(uploader_id)s_%(id)s_%(playlist_index)02d.%(ext)s`. Add `Outcome` values `COMPLETED`, `SKIPPED`, and `FAILED`; add `DownloadResult(url: str, outcome: Outcome, message: str, files: tuple[Path, ...] = ())`; and add `RunSummary.from_results(results: Iterable[DownloadResult]) -> RunSummary` counting each outcome.

- [ ] **Step 4: Write failing aggregation test in `tests/test_paths.py`**

```python
def test_run_summary_counts_completed_skipped_and_failed_results():
    summary = RunSummary.from_results([
        DownloadResult("a", Outcome.COMPLETED, "done"),
        DownloadResult("b", Outcome.SKIPPED, "exists"),
        DownloadResult("c", Outcome.FAILED, "unavailable"),
    ])

    assert (summary.completed, summary.skipped, summary.failed) == (1, 1, 1)
```

- [ ] **Step 5: Run path and aggregation tests to verify they pass**

Run: `python -m pytest tests/test_paths.py -v`

Expected: PASS.

### Task 3: Isolated yt-dlp downloader adapter

**Files:**
- Create: `twitter_video/downloader.py`
- Test: `tests/test_downloader.py`

**Interfaces:**
- Consumes: `UrlRequest`, `DownloadResult`, `Outcome`, and `output_template` from Tasks 1–2.
- Produces: `FfmpegMissingError`, `ensure_ffmpeg_available() -> None`, and `download_post(request: UrlRequest, destination: Path) -> DownloadResult`.
- Consumed by: Task 4 invokes `ensure_ffmpeg_available` and `download_post` for each valid request.

- [ ] **Step 1: Write a failing missing-ffmpeg test in `tests/test_downloader.py`**

```python
def test_ensure_ffmpeg_available_raises_before_downloading_when_not_on_path(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(FfmpegMissingError, match="ffmpeg"):
        ensure_ffmpeg_available()
```

- [ ] **Step 2: Run the missing-ffmpeg test to verify it fails**

Run: `python -m pytest tests/test_downloader.py::test_ensure_ffmpeg_available_raises_before_downloading_when_not_on_path -v`

Expected: FAIL because `downloader.py` does not exist.

- [ ] **Step 3: Implement the prerequisite check**

Implement `FfmpegMissingError(RuntimeError)` and `ensure_ffmpeg_available() -> None` using `shutil.which("ffmpeg")`. Its message must say that `ffmpeg` is required to combine the best video/audio streams and must be installed before retrying.

- [ ] **Step 4: Write failing yt-dlp option and success tests in `tests/test_downloader.py`**

```python
def test_download_post_uses_best_mp4_merge_and_never_overwrites(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr(downloader, "YoutubeDL", fake_youtube_dl_that_records_options(captured, return_code=0))

    result = download_post(UrlRequest("https://x.com/a/status/1", None), tmp_path)

    assert result.outcome is Outcome.COMPLETED
    assert captured["format"] == "bv*+ba/b"
    assert captured["merge_output_format"] == "mp4"
    assert captured["noplaylist"] is True
    assert captured["nooverwrites"] is True
    assert "%(uploader_id)s_%(id)s_%(playlist_index)02d.%(ext)s" in captured["outtmpl"]
```

- [ ] **Step 5: Run the downloader option test to verify it fails**

Run: `python -m pytest tests/test_downloader.py::test_download_post_uses_best_mp4_merge_and_never_overwrites -v`

Expected: FAIL because `download_post` does not exist.

- [ ] **Step 6: Implement `download_post` using the yt-dlp Python API**

Import `YoutubeDL` and `DownloadError` from `yt_dlp`. Configure per-post options with format `bv*+ba/b`, `merge_output_format="mp4"`, `noplaylist=True`, `nooverwrites=True`, output template from Task 2, and normal yt-dlp terminal progress. Return `COMPLETED` after `download([request.url])` succeeds. Convert `DownloadError` to a `FAILED` result with the concise error text, without raising, so Task 4 can continue a batch. Do not add cookies, authentication headers, proxy configuration, or private extractor arguments.

- [ ] **Step 7: Write failing failure/skip tests in `tests/test_downloader.py`**

```python
def test_download_post_returns_failed_result_for_extractor_error(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader, "YoutubeDL", fake_youtube_dl_that_raises_download_error("Private post"))

    result = download_post(UrlRequest("https://x.com/a/status/1", None), tmp_path)

    assert result.outcome is Outcome.FAILED
    assert "Private post" in result.message
```

- [ ] **Step 8: Run all downloader tests to verify they pass**

Run: `python -m pytest tests/test_downloader.py -v`

Expected: PASS.

### Task 4: Command-line orchestration and user-facing reporting

**Files:**
- Create: `twitter_video/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 1 input APIs, Task 2 summary/path APIs, and Task 3 downloader APIs.
- Produces: `build_parser() -> argparse.ArgumentParser` and `main(argv: Sequence[str] | None = None) -> int` for the `twitter-video` entry point.

- [ ] **Step 1: Write failing single-URL CLI tests in `tests/test_cli.py`**

```python
def test_main_downloads_single_url_and_prints_success_summary(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "download_directory", lambda: tmp_path)
    monkeypatch.setattr(cli, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(cli, "download_post", lambda request, destination: DownloadResult(request.url, Outcome.COMPLETED, "Downloaded"))

    assert main(["https://x.com/a/status/1"]) == 0
    assert "Completed: 1" in capsys.readouterr().out
```

- [ ] **Step 2: Run the single-URL CLI test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_main_downloads_single_url_and_prints_success_summary -v`

Expected: FAIL because `cli.py` and `main` do not exist.

- [ ] **Step 3: Implement parser and single-URL execution**

Implement an argparse parser with one optional positional `url`, `--file PATH`, and `--version`. Reject missing input and use of both input forms through `parser.error`. For a valid positional URL, call `ensure_ffmpeg_available`, create the download directory, call `download_post`, print its outcome and a summary, and return `0` only for `COMPLETED` or `SKIPPED`.

- [ ] **Step 4: Write failing batch-continuation and invalid-line tests in `tests/test_cli.py`**

```python
def test_main_continues_valid_batch_after_invalid_line_and_download_failure(monkeypatch, capsys, tmp_path):
    source = tmp_path / "thread.txt"
    source.write_text("https://x.com/a/status/1\nbad\nhttps://x.com/a/status/2\n", encoding="utf-8")
    monkeypatch.setattr(cli, "download_directory", lambda: tmp_path)
    monkeypatch.setattr(cli, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(
        cli, "download_post",
        lambda request, destination: DownloadResult(request.url, Outcome.FAILED if request.url.endswith("/1") else Outcome.COMPLETED, "result"),
    )

    assert main(["--file", str(source)]) == 1
    output = capsys.readouterr().out
    assert "line 2" in output
    assert "Completed: 1" in output
    assert "Failed: 2" in output
```

- [ ] **Step 5: Run the batch test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_main_continues_valid_batch_after_invalid_line_and_download_failure -v`

Expected: FAIL because batch orchestration is not implemented.

- [ ] **Step 6: Implement batch execution, result reporting, and exit statuses**

For `--file`, turn every Task 1 `InputProblem` into an immediate `FAILED` `DownloadResult` with a `line N` message, then call `download_post` for every valid request in order even after earlier failures. Run the ffmpeg prerequisite once before processing valid downloads; if it is missing, print the actionable error and return a nonzero status before a network request. Print one result line per input item and `Completed: N | Skipped: N | Failed: N` at the end. Return `1` when any failed result exists; retain `0` when all results completed or skipped.

- [ ] **Step 7: Write failing diagnostic-version test in `tests/test_cli.py`**

```python
def test_version_prints_tool_and_ytdlp_versions(capsys):
    assert main(["--version"]) == 0
    assert "twitter-video" in capsys.readouterr().out
```

- [ ] **Step 8: Implement `--version` and run all CLI tests**

Print the package version and the imported `yt_dlp.version.__version__` without checking URLs or requiring ffmpeg. Run: `python -m pytest tests/test_cli.py -v`

Expected: PASS.

### Task 5: Current-user installer and operating instructions

**Files:**
- Create: `install.ps1`
- Create: `README.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: console script defined in Task 1 and completed CLI from Task 4.
- Produces: an idempotent `twitter-video` command shim under `%USERPROFILE%\.local\TwitterVideo\bin` and user instructions.

- [ ] **Step 1: Write the installer acceptance checklist in `README.md` before implementation**

Document the exact expected effects: a `venv` under `%USERPROFILE%\.local\TwitterVideo`, a `bin\twitter-video.cmd` shim, only that bin directory added once to user PATH, no administrative prompt, a warning (not automatic installation) when `ffmpeg` is unavailable, and no writes outside the current user profile except the source directory being installed from.

- [ ] **Step 2: Implement `install.ps1`**

Require an available `python` or `py` command; if neither exists, terminate with an instruction to install Python for the current user. Create `%USERPROFILE%\.local\TwitterVideo\venv`, install this project into it with pip, create `%USERPROFILE%\.local\TwitterVideo\bin\twitter-video.cmd` that invokes the venv console script, and idempotently append only that bin path to `[Environment]::GetEnvironmentVariable('Path', 'User')`. Detect `ffmpeg` with `Get-Command ffmpeg -ErrorAction SilentlyContinue` and warn if absent. Do not use `Set-ExecutionPolicy`, Administrator checks, machine-level environment variables, scheduled tasks, or network downloads other than pip's declared dependencies.

- [ ] **Step 3: Write user documentation in `README.md`**

Include: the permitted-use boundary for public content, the exact PowerShell install command, a new-terminal note after PATH changes, one single-post example, `--file` content/example for manual threads, output directory, `--version`, `ffmpeg` requirement/error, rerun behavior, expected access-failure cases, and `yt-dlp` update troubleshooting. State precisely that automatic thread discovery is intentionally not implemented in the zero-cost version.

- [ ] **Step 4: Run static installer safety checks**

Run: `Select-String -Path install.ps1 -Pattern 'Program Files|Machine|Set-ExecutionPolicy|ScheduledTask|Start-Process.*Verb RunAs'`

Expected: no matches.

- [ ] **Step 5: Run the automated test suite and package-install check**

Run: `python -m pytest -v`

Expected: PASS.

Run: `python -m pip install .`

Expected: package installs and `twitter-video --version` exits `0`.

### Task 6: Install, verify, and perform a permitted real-world download

**Files:**
- Modify: none unless verification exposes a defect.

**Interfaces:**
- Consumes: installed `twitter-video` command from Task 5.
- Produces: verified current-user installation and downloaded videos in `%USERPROFILE%\Downloads\Twitter_Videos`.

- [ ] **Step 1: Verify prerequisites before user-scoped installation**

Run: `python --version; ffmpeg -version`

Expected: supported Python is present; `ffmpeg` either reports version information or triggers the documented prerequisite path.

- [ ] **Step 2: Install for the current user**

Run: `powershell -ExecutionPolicy Bypass -File .\install.ps1`

Expected: virtual environment and command shim under `%USERPROFILE%\.local\TwitterVideo`; only current-user PATH is modified.

- [ ] **Step 3: Open a fresh PowerShell process and verify the installed command**

Run: `powershell -NoProfile -Command "twitter-video --version"`

Expected: exit `0` and displays both the CLI and `yt-dlp` versions.

- [ ] **Step 4: Manually validate permitted public-post behavior**

Run: `twitter-video <a public X/Twitter post URL the user is authorized to save>`

Expected: all available video media from that one post appears under `%USERPROFILE%\Downloads\Twitter_Videos`, with progress and a completed summary. If the X extractor cannot access the post, retain the CLI's concise failure output and report it; do not introduce cookies, authentication, API credentials, or bypasses.

- [ ] **Step 5: Verify rerun and batch behavior**

Run: `twitter-video --file <a UTF-8 text file containing a permitted public post URL, one invalid line, and another permitted public post URL>`

Expected: valid URLs are attempted in order, invalid line is reported with its line number, existing output is skipped on rerun, and the final summary/exit status reflects failures.

## Plan self-review

- **Spec coverage:** Tasks 1–4 cover accepted inputs, batches, deterministic local output, per-URL results, exit codes, no-overwrite behavior, yt-dlp integration, ffmpeg messaging, and version diagnostics. Task 5 covers current-user installation and documentation. Task 6 covers installation and real-world behavior.
- **Gaps:** No Git commit tasks are included because `git rev-parse --show-toplevel` confirmed the working directory is not a repository; creating one was not authorized or necessary for the tool.
- **Type consistency:** `UrlRequest` flows from input to downloader; `DownloadResult` and `Outcome` flow from downloader to `RunSummary` and CLI; all named signatures match their consuming tasks.
- **Review focus:** Each listed risk is pinned to the named task and test step above.
- **Proportion:** The plan names interfaces, behavior, and tests without reproducing implementation bodies.
