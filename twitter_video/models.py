from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class UrlRequest:
    url: str
    line_number: int | None


@dataclass(frozen=True)
class InputProblem:
    value: str
    message: str
    line_number: int | None


@dataclass(frozen=True)
class InputBatch:
    requests: tuple[UrlRequest, ...]
    problems: tuple[InputProblem, ...]


class Outcome(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class DownloadResult:
    url: str
    outcome: Outcome
    message: str
    files: tuple[Path, ...] = ()


@dataclass(frozen=True)
class RunSummary:
    completed: int
    skipped: int
    failed: int

    @classmethod
    def from_results(cls, results: Iterable[DownloadResult]) -> "RunSummary":
        completed = 0
        skipped = 0
        failed = 0
        for result in results:
            if result.outcome is Outcome.COMPLETED:
                completed += 1
            elif result.outcome is Outcome.SKIPPED:
                skipped += 1
            elif result.outcome is Outcome.FAILED:
                failed += 1
        return cls(completed=completed, skipped=skipped, failed=failed)
