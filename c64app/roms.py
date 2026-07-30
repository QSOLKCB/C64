from __future__ import annotations

import hashlib
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import data_dir


@dataclass(frozen=True, slots=True)
class RomDefinition:
    key: str
    canonical_name: str
    size: int
    machine_subdir: str
    aliases: tuple[str, ...]
    required: bool = True


ROM_DEFINITIONS: tuple[RomDefinition, ...] = (
    RomDefinition("kernal", "kernal", 8192, "C64", ("kernal", "kernal.rom", "901227-03.bin")),
    RomDefinition("basic", "basic", 8192, "C64", ("basic", "basic.rom", "901226-01.bin")),
    RomDefinition("chargen", "chargen", 4096, "C64", ("chargen", "chargen.rom", "characters.rom", "901225-01.bin")),
    RomDefinition(
        "dos1541",
        "dos1541",
        16384,
        "DRIVES",
        ("dos1541", "dos1541.rom", "1541.rom", "325302-01+901229-05.bin"),
        required=False,
    ),
)


@dataclass(slots=True)
class RomMatch:
    definition: RomDefinition
    path: Path | None
    sha256: str | None = None

    @property
    def ok(self) -> bool:
        return self.path is not None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def known_search_roots(custom_root: Path | None = None) -> list[Path]:
    roots: list[Path] = []
    if custom_root:
        roots.append(custom_root)
    roots.extend(
        [
            data_dir() / "roms",
            Path.home() / ".local" / "share" / "vice",
            Path.home() / ".vice",
            Path("/usr/share/vice"),
            Path("/usr/lib/vice"),
            Path("/usr/local/share/vice"),
            Path("/usr/local/lib/vice"),
            Path("/app/share/vice"),
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        key = str(root.expanduser())
        if key not in seen:
            seen.add(key)
            unique.append(root.expanduser())
    return unique


def _candidate_dirs(root: Path, definition: RomDefinition) -> Iterable[Path]:
    yield root / definition.machine_subdir
    yield root / definition.machine_subdir.lower()
    yield root


def find_rom(definition: RomDefinition, roots: Iterable[Path]) -> RomMatch:
    for root in roots:
        for directory in _candidate_dirs(root, definition):
            if not directory.is_dir():
                continue
            for alias in definition.aliases:
                candidate = directory / alias
                try:
                    if candidate.is_file() and candidate.stat().st_size == definition.size:
                        return RomMatch(definition, candidate.resolve(), sha256_file(candidate))
                except OSError:
                    continue
            try:
                files = list(directory.iterdir())
            except OSError:
                continue
            for candidate in files:
                try:
                    if candidate.is_file() and candidate.stat().st_size == definition.size:
                        lowered = candidate.name.lower()
                        if any(alias.split(".")[0] in lowered for alias in definition.aliases):
                            return RomMatch(definition, candidate.resolve(), sha256_file(candidate))
                except OSError:
                    continue
    return RomMatch(definition, None, None)


def discover_roms(custom_root: Path | None = None) -> dict[str, RomMatch]:
    roots = known_search_roots(custom_root)
    return {definition.key: find_rom(definition, roots) for definition in ROM_DEFINITIONS}


def required_roms_ready(matches: dict[str, RomMatch]) -> bool:
    return all(matches[d.key].ok for d in ROM_DEFINITIONS if d.required)


def _collect_source_files(source: Path) -> tuple[Path, list[Path]]:
    if source.is_dir():
        return source, [p for p in source.rglob("*") if p.is_file()]
    if source.is_file() and zipfile.is_zipfile(source):
        temp_dir = Path(tempfile.mkdtemp(prefix="qsol-c64-roms-"))
        with zipfile.ZipFile(source) as archive:
            archive.extractall(temp_dir)
        return temp_dir, [p for p in temp_dir.rglob("*") if p.is_file()]
    raise ValueError(f"ROM source must be a directory or ZIP archive: {source}")


def import_roms(source: Path, destination_root: Path | None = None) -> dict[str, RomMatch]:
    destination_root = destination_root or (data_dir() / "roms")
    extraction_root, files = _collect_source_files(source.expanduser())
    try:
        copied: dict[str, RomMatch] = {}
        for definition in ROM_DEFINITIONS:
            selected: Path | None = None
            for candidate in files:
                try:
                    if candidate.stat().st_size != definition.size:
                        continue
                except OSError:
                    continue
                lowered = candidate.name.lower()
                if lowered in {a.lower() for a in definition.aliases}:
                    selected = candidate
                    break
            if selected is None:
                for candidate in files:
                    try:
                        if candidate.stat().st_size == definition.size and any(
                            alias.split(".")[0] in candidate.name.lower() for alias in definition.aliases
                        ):
                            selected = candidate
                            break
                    except OSError:
                        continue
            if selected is None:
                copied[definition.key] = RomMatch(definition, None, None)
                continue
            target_dir = destination_root / definition.machine_subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / definition.canonical_name
            shutil.copyfile(selected, target)
            copied[definition.key] = RomMatch(definition, target.resolve(), sha256_file(target))
        return copied
    finally:
        if extraction_root != source and extraction_root.name.startswith("qsol-c64-roms-"):
            shutil.rmtree(extraction_root, ignore_errors=True)


def vice_rom_args(matches: dict[str, RomMatch]) -> list[str]:
    args: list[str] = []
    option_map = {"kernal": "-kernal", "basic": "-basic", "chargen": "-chargen", "dos1541": "-dos1541"}
    for key, option in option_map.items():
        match = matches.get(key)
        if match and match.path:
            args.extend([option, str(match.path)])
    return args
