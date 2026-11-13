from pathlib import Path
import re
from urllib.parse import urlsplit

from .models import InputBatch, InputProblem, UrlRequest


_POST_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}
_USERNAME = re.compile(r"^[A-Za-z0-9_]+$")
_POST_ID = re.compile(r"^\d+$")


def validate_post_url(value: str) -> str:
    """Return a supported public X/Twitter post URL or raise ValueError."""
    candidate = value.strip()
    parsed = urlsplit(candidate)
    segments = [segment for segment in parsed.path.split("/") if segment]

    valid = (
        parsed.scheme in {"http", "https"}
        and parsed.hostname is not None
        and parsed.hostname.lower() in _POST_HOSTS
        and len(segments) == 3
        and _USERNAME.fullmatch(segments[0]) is not None
        and segments[1] == "status"
        and _POST_ID.fullmatch(segments[2]) is not None
    )
    if not valid:
        raise ValueError("Expected a public X/Twitter post URL.")
    return candidate


def read_url_file(path: Path) -> InputBatch:
    """Read URL requests and non-fatal validation problems from a UTF-8 file."""
    requests: list[UrlRequest] = []
    problems: list[InputProblem] = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        try:
            requests.append(UrlRequest(validate_post_url(value), line_number))
        except ValueError as error:
            problems.append(InputProblem(value, str(error), line_number))

    return InputBatch(tuple(requests), tuple(problems))
