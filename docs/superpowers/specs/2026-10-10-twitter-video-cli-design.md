# Twitter Video CLI — Design

## Goal

Provide a no-cost command-line tool for one Windows user to save videos from public X (formerly Twitter) posts that the user is permitted to download. It runs locally, makes no API calls to X's paid developer platform, and does not use an X account, cookies, or stored credentials.

## User and success criteria

The tool is personal and single-user. A successful run accepts either one public post URL or a text file containing several public post URLs, then saves every video available in each post to the user's Downloads folder. It should make the ordinary case easy to run from PowerShell and make failures understandable without exposing credentials or stopping an unrelated batch item.

## Scope

### Included

- Public `x.com` and `twitter.com` post URLs.
- All videos in an individual post, including posts that contain multiple videos.
- Batch downloading from a user-provided text file with one URL per line. This is the zero-cost workflow for a thread.
- The best available video/audio combination that can be produced as MP4 locally.
- Files stored under `%USERPROFILE%\Downloads\Twitter_Videos`.
- Progress, a per-URL result, and an end-of-run completed/failed summary.
- Existing-file detection so an identical file is not downloaded twice.
- A current-user installation only, without administrator privileges.

### Explicitly excluded

- Automatic discovery of later posts in a thread. Reliably discovering them requires paid or otherwise unsupported access to X data; the user supplies the related URLs in a file instead.
- Posts that are private, deleted, unavailable in the user's region, or require authentication.
- Login, cookies, API tokens, proxy support, DRM circumvention, and bypassing X access controls.
- A GUI, web server, cloud storage, or background service.

## Command-line interface

```powershell
# One post
twitter-video https://x.com/user/status/123

# A thread or list of posts, one URL per line
twitter-video --file C:\path\to\thread.txt
```

The positional form accepts exactly one post URL. `--file` accepts a UTF-8 text file, ignores blank lines and lines beginning with `#`, preserves the listed order, and processes every remaining URL independently. The two forms are mutually exclusive.

Successful files use a deterministic, collision-resistant name based on author, post ID, media position, and extension, for example `jobecoffe_2108403966665199628_01.mp4`. The downloader will skip an existing output file with that same name.

## Architecture

The codebase is a small Python package with these bounded responsibilities:

| Component | Responsibility |
| --- | --- |
| `cli` | Parse command arguments, print progress/summary, and map expected failures to exit codes. |
| `input` | Validate supported X/Twitter post URLs and read `--file` input. |
| `download` | Invoke the local `yt-dlp` dependency with fixed safe options and translate its outcome into per-post results. |
| `paths` | Determine the current user's Downloads folder and construct `%USERPROFILE%\Downloads\Twitter_Videos` output paths. |
| `models` | Small immutable result types for completed, skipped, and failed downloads. |

`yt-dlp` remains an external, versioned dependency rather than copied source. It provides the X media extractor and transfer logic. `ffmpeg` is detected before a download: it is required when the best video and audio streams need merging. The CLI emits a concrete installation message when it is missing.

## Installation and user scope

An `install.ps1` bootstrapper installs the package and its Python dependencies into a virtual environment beneath:

```text
%USERPROFILE%\.local\TwitterVideo
```

It creates a current-user command shim named `twitter-video` and adds only that shim directory to the current user's PATH. It does not write to Program Files, change machine-wide PATH, require elevation, add scheduled tasks, or create an X account. Python must already be available to the current user; otherwise the bootstrapper stops with an actionable prerequisite message.

Downloads are always written to:

```text
%USERPROFILE%\Downloads\Twitter_Videos
```

The command creates that directory on first use.

## Download behavior and errors

For each accepted URL, the downloader asks `yt-dlp` for all native video media in that post and selects the best compatible MP4 output. A post may yield zero, one, or multiple files. The user sees live transfer progress as supplied by `yt-dlp`.

Expected errors are categorized as follows:

| Condition | User-facing behavior |
| --- | --- |
| Invalid or non-post URL | Reject before a network request and explain the accepted URL format. |
| Blank/comment line in `--file` | Ignore it. |
| Private, deleted, unavailable, or no-video post | Mark that URL failed with the extractor's concise reason; continue batch processing. |
| Network or temporary X failure | Mark the URL failed and preserve a clear retry suggestion; continue the batch. |
| Missing `ffmpeg` when a merge is needed | Stop before transfer with an installation instruction. |
| Existing target file | Mark it skipped; do not overwrite it. |

Exit status is `0` only when every requested URL succeeds or is already present. It is nonzero for bad invocation, missing prerequisites, or any failed URL; the completion summary stays visible in all cases.

## Testing and verification

Automated tests will cover URL validation, list-file parsing, output path construction, naming, duplicate handling, result aggregation, and CLI exit-status behavior. The downloader adapter will be mocked in unit tests so tests do not make X requests.

Manual verification will use a public post that the user is authorized to save and will check: a single-video post, a multi-video post, a batch containing a successful and an unavailable link, correct output directory, rerun skip behavior, and the missing-`ffmpeg` message where applicable.

## Constraints and maintenance

X can alter access patterns without notice. The program must report extractor failures plainly and make the installed `yt-dlp` version visible in a diagnostic command or failure message. Updating `yt-dlp` is the first supported response when public-post extraction stops working; no workaround that uses private data, credentials, access-control bypass, or a paid X API is in scope.
