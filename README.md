# C64 Emulator

**A C64 emulator experience for Linux that does not make you study emulator archaeology first.**

`QSOLKCB/C64` is a zero-dependency Python front end for the proven VICE emulation engine. It gives Linux users one obvious command, a usable terminal interface, automatic engine and ROM discovery, one-step ROM import, a game library, and sane presets.

The goal is not to rewrite thirty years of cycle-accurate C64 work. The goal is to make that work pleasant to use.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ C64 // SIMPLE LINUX FRONT END                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Profile:accurate  Region:PAL  Fullscreen:N  CRT:N                           │
│                                                                              │
│ > [D64] The Last Ninja      —  ~/Games/C64/The Last Ninja.d64               │
│   [PRG] 10 PRINT            —  ~/Games/C64/10print.prg                      │
│   [CRT] EasyFlash Demo      —  ~/Games/C64/EasyFlash Demo.crt               │
│                                                                              │
│ Enter play  / search  p profile  f fullscreen  c CRT  d doctor  q quit      │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Why this exists

Existing projects each solve a different hard problem:

- **VICE / BMC64** provide high compatibility and accurate emulation.
- **Emudore** is a readable from-scratch learning emulator.
- **EMU64** provides a large desktop GUI.
- **RetroDebugger** provides deep inspection and development tooling.
- **c64-kitty** proves a C64 can live directly inside a modern terminal.

What is still missing on Linux is the boring but important layer: *install it, point it at a game, and play it without hunting through menus or hidden directories.*

## Current features

- One command: `c64`
- Curses TUI with library browsing, search and launch
- Direct CLI launch: `c64 play game.d64`
- Automatic detection of native VICE and the VICE Flatpak
- Exact diagnostics through `c64 doctor`
- One-step ROM import from a directory or ZIP archive
- Automatic ROM discovery in common VICE and XDG paths
- SHA-256 fingerprints for imported ROMs
- PAL and NTSC selection
- Accurate, fast and CRT profiles
- Fullscreen and CRT filter toggles
- Recursive library scanning
- No pip packages, Node.js, Electron, Qt, database or background service
- Configuration stored as readable JSON

## Install

Requirements:

- Linux
- Python 3.10 or newer
- VICE (`x64sc`) or the VICE Flatpak

```sh
git clone https://github.com/QSOLKCB/C64.git
cd C64
./install.sh
c64 doctor
```

Install VICE using one of these routes:

```sh
# Ubuntu / Debian
sudo apt install vice

# Flatpak
flatpak install flathub net.sf.VICE
```

> Some Linux distribution packages deliberately omit copyrighted Commodore ROM images. C64 does not pretend this problem does not exist: `c64 doctor` tells you exactly which files are missing, and `c64 setup` imports a legally obtained set in one operation.

## First setup

### 1. Diagnose the machine

```sh
c64 doctor
```

### 2. Import ROMs once

Pass either a directory or a ZIP archive. Filenames do not need to be perfect; C64 checks aliases and exact ROM sizes.

```sh
c64 setup ~/Downloads/my-c64-roms.zip
```

The importer looks for:

| ROM | Size | Required |
|---|---:|:---:|
| KERNAL | 8192 bytes | Yes |
| BASIC | 8192 bytes | Yes |
| character generator | 4096 bytes | Yes |
| 1541 DOS | 16384 bytes | Recommended |

Imported ROMs are placed under `~/.local/share/qsol-c64/roms/` and fingerprinted with SHA-256.

### 3. Add a library

```sh
c64 setup --library ~/Games/C64
```

### 4. Launch the TUI

```sh
c64
```

## CLI

```sh
# Open the TUI
c64

# Launch an image immediately
c64 play "~/Games/C64/Impossible Mission.d64"

# Use a preset
c64 play game.d64 --profile accurate
c64 play game.prg --profile fast
c64 play demo.d64 --profile crt --fullscreen

# Select video standard
c64 play game.d64 --region pal
c64 play game.d64 --region ntsc

# See the exact VICE command without launching it
c64 play game.d64 --dry-run

# Pass an advanced option directly to VICE
c64 play demo.d64 -- --sidenginemodel 256

# List the library without opening curses
c64 library
```

## Profiles

| Profile | Behaviour |
|---|---|
| `accurate` | Uses `x64sc`, true-drive emulation when the 1541 ROM is available, and VIC-II vsync |
| `fast` | Uses the faster engine when available, injects PRG files, disables true-drive emulation and warps during autostart |
| `crt` | Accurate profile plus VICE CRT rendering |

The profiles are intentionally small. A preset should explain a useful choice, not expose every emulator resource in a 400-item settings tree.

## Configuration

```sh
c64 config show
c64 config path
c64 config reset
```

Default paths:

```text
~/.config/qsol-c64/config.json
~/.local/share/qsol-c64/roms/
```

Override the emulator command temporarily:

```sh
C64_ENGINE='/opt/vice/bin/x64sc' c64 play game.d64
```

## ROM policy

No proprietary Commodore ROM image is stored in this repository or downloaded behind the user's back. The software handles discovery, validation, copying and configuration; the user supplies ROMs they are legally entitled to use. See [docs/ROM_POLICY.md](docs/ROM_POLICY.md).

## Architecture

This repository is deliberately a front end, not a fork of VICE. VICE runs as a separate process, so the C64 interface remains small and independently licensed. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Development

```sh
make lint
make test
```

The test suite uses only Python's standard library.

## Roadmap

The first release fixes first-run use. Later releases can add:

- controller setup and automatic joystick-port selection
- per-game profiles
- snapshot management
- disk-directory preview
- `.desktop` file associations
- optional in-terminal Kitty graphics mode
- an SDL front end with a controller-first ten-foot UI
- clean-room replacement-ROM support when compatibility is sufficient
- packaging for AppImage, Flatpak and Debian-family systems

## License

C64 is licensed under the **MIT License**.

VICE is a separate project with its own license and is not redistributed by this repository.
