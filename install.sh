#!/bin/sh
set -eu

PREFIX=${PREFIX:-"$HOME/.local"}
APP_DIR="$PREFIX/lib/qsol-c64"
BIN_DIR="$PREFIX/bin"
DESKTOP_DIR=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR"
rm -rf "$APP_DIR/c64app"
cp -R "$SOURCE_DIR/c64app" "$APP_DIR/c64app"
cp "$SOURCE_DIR/c64" "$APP_DIR/c64"
chmod 755 "$APP_DIR/c64"

cat > "$BIN_DIR/c64" <<EOF
#!/bin/sh
exec python3 "$APP_DIR/c64" "\$@"
EOF
chmod 755 "$BIN_DIR/c64"

cat > "$DESKTOP_DIR/qsol-c64.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=C64 Simple
Comment=Simple C64 launcher and library for Linux
Exec=$BIN_DIR/c64 tui
Terminal=true
Categories=Game;Emulator;
Keywords=C64;Commodore;VICE;Emulator;
EOF

printf '%s\n' "Installed C64 Simple to $APP_DIR"
printf '%s\n' "Launcher: $BIN_DIR/c64"
case ":${PATH:-}:" in
  *":$BIN_DIR:"*) : ;;
  *) printf '%s\n' "Add $BIN_DIR to PATH, then run: c64 doctor" ;;
esac
