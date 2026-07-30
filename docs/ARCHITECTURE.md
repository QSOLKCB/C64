# Architecture

## Design rule

The project fixes the **experience layer** while delegating machine emulation to a mature engine.

```text
                     ┌────────────────────────────┐
                     │        c64 command         │
                     └──────────────┬─────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
        ┌───────▼────────┐  ┌──────▼──────┐   ┌────────▼────────┐
        │ curses library │  │ setup/doctor│   │ direct CLI play │
        │ and launcher   │  │ ROM manager │   │ and dry-run     │
        └───────┬────────┘  └──────┬──────┘   └────────┬────────┘
                └───────────────────┼───────────────────┘
                                    │
                           ┌────────▼────────┐
                           │ engine adapter │
                           └────────┬────────┘
                                    │ subprocess boundary
                         ┌──────────▼──────────┐
                         │ VICE x64sc / x64    │
                         │ native or Flatpak   │
                         └─────────────────────┘
```

## Modules

- `c64app.cli` — command-line contract and user-facing errors
- `c64app.tui` — curses interface and keyboard navigation
- `c64app.config` — XDG paths and atomic JSON configuration
- `c64app.engine` — VICE detection, profile mapping and process launch
- `c64app.roms` — ROM discovery, size validation, import and hashing
- `c64app.library` — recursive image indexing

## Why not fork VICE?

A fork would inherit a large C/C++ codebase, duplicate emulator maintenance, and make upstream accuracy improvements harder to consume. The usability problems described by this project occur mostly before the emulated 6510 executes its first instruction.

The subprocess boundary also keeps licensing clear: this program does not copy or link VICE code. It discovers and invokes a separately installed executable.

## Why Python?

Python's standard library already provides:

- `argparse` for a stable CLI
- `curses` for a native terminal interface
- `pathlib` for filesystem handling
- `zipfile` and `hashlib` for ROM import
- `subprocess` for engine isolation
- `json` for inspectable configuration

There are no runtime package downloads and no virtual environment is required.

## Configuration invariants

- Writes are atomic through a temporary file and rename.
- Unknown JSON keys are ignored for forwards compatibility.
- Paths are expanded at use time.
- The engine can be overridden without mutating config through `C64_ENGINE`.

## ROM invariants

- Required ROMs are identified by role and exact byte size.
- Imported files are renamed to stable canonical names.
- SHA-256 is informational provenance, not a copyright bypass or authenticity guarantee.
- Missing 1541 firmware degrades to virtual drive loading instead of blocking the C64 boot ROM.

## Engine profile contract

Profiles map human goals to a deliberately small set of VICE options. Advanced users can append raw VICE arguments after `--` without making every beginner confront them.
