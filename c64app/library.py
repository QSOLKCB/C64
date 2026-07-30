from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SUPPORTED_EXTENSIONS = {
    ".d64",
    ".d71",
    ".d81",
    ".g64",
    ".g71",
    ".t64",
    ".tap",
    ".prg",
    ".p00",
    ".crt",
    ".vsf",
    ".x64",
}


@dataclass(frozen=True, slots=True)
class LibraryItem:
    path: Path

    @property
    def title(self) -> str:
        return self.path.stem.replace("_", " ").replace("-", " ").strip()

    @property
    def kind(self) -> str:
        return self.path.suffix.lower().lstrip(".").upper()


def is_supported(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def scan_library(paths: Iterable[str | Path]) -> list[LibraryItem]:
    found: dict[str, LibraryItem] = {}
    for raw in paths:
        root = Path(raw).expanduser()
        if root.is_file() and is_supported(root):
            found[str(root.resolve())] = LibraryItem(root.resolve())
            continue
        if not root.is_dir():
            continue
        try:
            candidates = root.rglob("*")
            for candidate in candidates:
                try:
                    if is_supported(candidate):
                        found[str(candidate.resolve())] = LibraryItem(candidate.resolve())
                except OSError:
                    continue
        except OSError:
            continue
    return sorted(found.values(), key=lambda item: (item.title.casefold(), str(item.path)))
