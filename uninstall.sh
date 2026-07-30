#!/bin/sh
set -eu
PREFIX=${PREFIX:-"$HOME/.local"}
rm -rf "$PREFIX/lib/qsol-c64"
rm -f "$PREFIX/bin/c64"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/qsol-c64.desktop"
printf '%s\n' "Removed C64 Simple. Configuration and ROMs were left untouched."
