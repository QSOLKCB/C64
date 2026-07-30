from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .roms import RomMatch, vice_rom_args


@dataclass(frozen=True, slots=True)
class Engine:
    kind: str
    command: tuple[str, ...]
    display_name: str

    def printable(self) -> str:
        return shlex.join(self.command)


def _flatpak_has_vice() -> bool:
    if not shutil.which("flatpak"):
        return False
    result = subprocess.run(
        ["flatpak", "info", "net.sf.VICE"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def detect_engines() -> list[Engine]:
    engines: list[Engine] = []
    override = os.environ.get("C64_ENGINE")
    if override:
        command = tuple(shlex.split(override))
        if command:
            engines.append(Engine("custom", command, f"Custom: {override}"))
    for executable, label in (("x64sc", "VICE x64sc (accurate)"), ("x64", "VICE x64 (fast)")):
        resolved = shutil.which(executable)
        if resolved:
            engines.append(Engine("native", (resolved,), label))
    if _flatpak_has_vice():
        engines.append(
            Engine("flatpak", ("flatpak", "run", "--command=x64sc", "net.sf.VICE"), "VICE Flatpak x64sc")
        )
    return engines


def choose_engine(config: Config, profile: str | None = None) -> Engine | None:
    engines = detect_engines()
    if not engines:
        return None
    requested = config.engine
    if requested not in ("", "auto"):
        for engine in engines:
            if requested in {engine.kind, engine.command[0], engine.display_name}:
                return engine
    profile = profile or config.profile
    if profile == "fast":
        for engine in engines:
            if Path(engine.command[-1]).name == "x64" or engine.command[0].endswith("/x64"):
                return engine
    for engine in engines:
        if "x64sc" in " ".join(engine.command):
            return engine
    return engines[0]


def build_command(
    engine: Engine,
    config: Config,
    matches: dict[str, RomMatch],
    image: Path | None = None,
    *,
    profile: str | None = None,
    region: str | None = None,
    fullscreen: bool | None = None,
    crt_filter: bool | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    profile = profile or config.profile
    region = region or config.region
    fullscreen = config.fullscreen if fullscreen is None else fullscreen
    crt_filter = config.crt_filter if crt_filter is None else crt_filter

    command = list(engine.command)
    command.extend(vice_rom_args(matches))
    command.extend(["-model", "c64"])
    command.append("-pal" if region == "pal" else "-ntsc")

    if profile == "fast":
        command.extend(["+drive8truedrive", "-autostartprgmode", "1", "-autostart-warp"])
    elif matches.get("dos1541") and matches["dos1541"].path:
        command.extend(["-drive8truedrive", "-autostart-handle-tde", "-VICIIvsync"])
    else:
        command.extend(["+drive8truedrive", "-VICIIvsync"])

    command.extend(["-VICIIfilter", "1" if crt_filter or profile == "crt" else "0"])
    command.append("-VICIIfull" if fullscreen else "+VICIIfull")
    command.append("-VICIIshowstatusbar" if config.status_bar else "+VICIIshowstatusbar")

    command.extend(config.extra_args)
    if extra_args:
        command.extend(extra_args)
    if image is not None:
        command.extend(["-autostart", str(image.resolve())])
    return command


def launch(command: list[str]) -> int:
    try:
        completed = subprocess.run(command, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Could not launch emulator: {exc}") from exc
    return completed.returncode
