from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

from .config import Config, config_path, data_dir, load_config, save_config
from .engine import build_command, choose_engine, detect_engines, launch
from .library import SUPPORTED_EXTENSIONS, scan_library
from .roms import ROM_DEFINITIONS, discover_roms, import_roms, required_roms_ready
from .tui import run_tui


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="c64",
        description="A simple Linux launcher, library and TUI for the VICE C64 engine.",
    )
    parser.add_argument("--version", action="version", version="c64 0.1.0")
    sub = parser.add_subparsers(dest="command")

    play = sub.add_parser("play", help="Autostart a C64 program or disk image")
    play.add_argument("image", type=Path)
    play.add_argument("--profile", choices=("accurate", "fast", "crt"))
    play.add_argument("--region", choices=("pal", "ntsc"))
    play.add_argument("--fullscreen", action=argparse.BooleanOptionalAction, default=None)
    play.add_argument("--crt", action=argparse.BooleanOptionalAction, default=None)
    play.add_argument("--dry-run", action="store_true")
    play.add_argument("extra", nargs=argparse.REMAINDER, help="Arguments after -- are passed to VICE")

    setup = sub.add_parser("setup", help="Detect VICE, import ROMs and configure the game library")
    setup.add_argument("rom_source", nargs="?", type=Path, help="Directory or ZIP containing your legally obtained ROMs")
    setup.add_argument("--library", action="append", type=Path, default=[])
    setup.add_argument("--engine", default=None, help="auto, native, flatpak, or an engine selector")
    setup.add_argument("--region", choices=("pal", "ntsc"))

    sub.add_parser("doctor", help="Explain exactly what is installed and what is missing")

    library = sub.add_parser("library", help="List detected C64 images")
    library.add_argument("paths", nargs="*", type=Path)

    config = sub.add_parser("config", help="Show configuration paths or values")
    config.add_argument("action", choices=("show", "path", "reset"), nargs="?", default="show")

    sub.add_parser("tui", help="Open the terminal user interface")
    return parser


def _print_rom_status(config: Config) -> bool:
    matches = discover_roms(config.resolved_rom_dir)
    print("ROM set:")
    for definition in ROM_DEFINITIONS:
        match = matches[definition.key]
        label = "required" if definition.required else "optional"
        if match.path:
            digest = f"sha256:{match.sha256[:12]}" if match.sha256 else "sha256:unavailable"
            print(f"  [ok]      {definition.key:<8} {match.path}  {digest}")
        else:
            print(f"  [missing] {definition.key:<8} ({label}, {definition.size} bytes)")
    return required_roms_ready(matches)


def cmd_doctor(config: Config) -> int:
    print("C64 doctor")
    print(f"  Config:  {config_path()}")
    print(f"  Data:    {data_dir()}")
    engines = detect_engines()
    if engines:
        for engine in engines:
            print(f"  Engine:  [ok] {engine.display_name} -> {engine.printable()}")
    else:
        print("  Engine:  [missing] Install VICE or its Flatpak package")
        print("           Ubuntu/Debian: sudo apt install vice")
        print("           Flatpak: flatpak install flathub net.sf.VICE")
    roms_ok = _print_rom_status(config)
    existing_libraries = [Path(path).expanduser() for path in config.library_paths if Path(path).expanduser().exists()]
    print(f"  Library: {len(existing_libraries)} configured path(s) exist")
    for path in config.library_paths:
        marker = "ok" if Path(path).expanduser().exists() else "missing"
        print(f"           [{marker}] {Path(path).expanduser()}")
    if not engines:
        return 2
    if not roms_ok:
        print("\nFix ROMs with one command:")
        print("  c64 setup /path/to/your/rom-folder-or.zip")
        return 3
    print("\nEverything required to boot a C64 is ready.")
    return 0


def cmd_setup(config: Config, args: argparse.Namespace) -> int:
    if args.engine:
        config.engine = args.engine
    if args.region:
        config.region = args.region
    if args.library:
        for path in args.library:
            resolved = str(path.expanduser().resolve())
            if resolved not in config.library_paths:
                config.library_paths.append(resolved)
    if args.rom_source:
        print(f"Importing ROMs from {args.rom_source} ...")
        try:
            imported = import_roms(args.rom_source, config.resolved_rom_dir)
        except (OSError, ValueError) as exc:
            print(f"c64: ROM import failed: {exc}", file=sys.stderr)
            return 2
        for key, match in imported.items():
            if match.path:
                digest = f" sha256:{match.sha256[:12]}" if match.sha256 else " sha256:unavailable"
                print(f"  [ok] {key}: {match.path}{digest}")
            else:
                print(f"  [not found] {key}")
    save_config(config)
    print(f"Saved configuration: {config_path()}")
    return cmd_doctor(config)


def cmd_play(config: Config, args: argparse.Namespace) -> int:
    image = args.image.expanduser()
    if not image.is_file():
        print(f"c64: image does not exist: {image}", file=sys.stderr)
        return 2
    if image.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"c64: unsupported image type: {image.suffix or '(none)'}", file=sys.stderr)
        return 2
    engine = choose_engine(config, args.profile)
    if not engine:
        print("c64: VICE engine not found; run `c64 doctor`", file=sys.stderr)
        return 3
    matches = discover_roms(config.resolved_rom_dir)
    if not required_roms_ready(matches):
        print("c64: C64 ROM set incomplete; run `c64 doctor` then `c64 setup SOURCE`", file=sys.stderr)
        return 4
    extra = list(args.extra)
    if extra and extra[0] == "--":
        extra = extra[1:]
    command = build_command(
        engine,
        config,
        matches,
        image,
        profile=args.profile,
        region=args.region,
        fullscreen=args.fullscreen,
        crt_filter=args.crt,
        extra_args=extra,
    )
    if args.dry_run:
        print(shlex.join(command))
        return 0
    return launch(command)


def cmd_library(config: Config, args: argparse.Namespace) -> int:
    paths = args.paths or [Path(path) for path in config.library_paths]
    items = scan_library(paths)
    for item in items:
        print(f"{item.kind:<4} {item.title}\t{item.path}")
    print(f"\n{len(items)} image(s)")
    return 0


def cmd_config(config: Config, args: argparse.Namespace) -> int:
    if args.action == "path":
        print(config_path())
        return 0
    if args.action == "reset":
        path = config_path()
        if path.exists():
            path.unlink()
        print(f"Reset {path}")
        return 0
    import json
    from dataclasses import asdict

    print(json.dumps(asdict(config), indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        config = load_config()
    except RuntimeError as exc:
        print(f"c64: {exc}", file=sys.stderr)
        return 2

    if args.command in (None, "tui"):
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            parser.print_help()
            return 0
        try:
            run_tui(config)
        except KeyboardInterrupt:
            return 130
        except Exception as exc:
            print(f"c64: TUI failed: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.command == "doctor":
        return cmd_doctor(config)
    if args.command == "setup":
        return cmd_setup(config, args)
    if args.command == "play":
        return cmd_play(config, args)
    if args.command == "library":
        return cmd_library(config, args)
    if args.command == "config":
        return cmd_config(config, args)
    parser.error(f"Unknown command: {args.command}")
    return 2
