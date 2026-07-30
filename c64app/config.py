from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

APP_NAME = "qsol-c64"


def _xdg_dir(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value).expanduser() if value else fallback


def config_dir() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", Path.home() / ".config") / APP_NAME


def data_dir() -> Path:
    return _xdg_dir("XDG_DATA_HOME", Path.home() / ".local" / "share") / APP_NAME


def state_dir() -> Path:
    return _xdg_dir("XDG_STATE_HOME", Path.home() / ".local" / "state") / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass(slots=True)
class Config:
    engine: str = "auto"
    rom_dir: str = ""
    library_paths: list[str] = field(default_factory=lambda: [str(Path.home() / "Games" / "C64")])
    profile: str = "accurate"
    region: str = "pal"
    fullscreen: bool = False
    crt_filter: bool = False
    status_bar: bool = True
    extra_args: list[str] = field(default_factory=list)

    @property
    def resolved_rom_dir(self) -> Path:
        if self.rom_dir:
            return Path(self.rom_dir).expanduser()
        return data_dir() / "roms"

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "Config":
        allowed = {name for name in cls.__dataclass_fields__}
        clean = {key: value for key, value in raw.items() if key in allowed}
        return cls(**clean)


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read configuration {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"Configuration {path} must contain a JSON object")
    return Config.from_mapping(raw)


def save_config(config: Config, path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(asdict(config), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)
    return path
