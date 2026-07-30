from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from c64app.cli import _print_rom_status
from c64app.config import Config, load_config, save_config
from c64app.engine import Engine, build_command
from c64app.library import scan_library
from c64app.roms import ROM_DEFINITIONS, RomMatch, import_roms, required_roms_ready


class ConfigTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            expected = Config(profile="crt", fullscreen=True, library_paths=["/games"])
            save_config(expected, path)
            actual = load_config(path)
            self.assertEqual(actual.profile, "crt")
            self.assertTrue(actual.fullscreen)
            self.assertEqual(actual.library_paths, ["/games"])


class RomTests(unittest.TestCase):
    def _write_rom_directory(self, root: Path) -> None:
        for definition in ROM_DEFINITIONS:
            (root / definition.aliases[0]).write_bytes(bytes(definition.size))

    def test_import_by_filename_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source = Path(source_tmp)
            self._write_rom_directory(source)
            matches = import_roms(source, Path(dest_tmp))
            self.assertTrue(required_roms_ready(matches))
            self.assertTrue(matches["dos1541"].path and matches["dos1541"].path.exists())

    def test_zip_import_strips_member_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "roms.zip"
            destination = root / "destination"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for definition in ROM_DEFINITIONS:
                    archive.writestr(
                        f"../../nested/{definition.aliases[0]}",
                        bytes(definition.size),
                    )
                archive.writestr("../../outside.txt", b"not a ROM")

            matches = import_roms(archive_path, destination)

            self.assertTrue(required_roms_ready(matches))
            self.assertEqual(matches["kernal"].path, (destination / "C64" / "kernal").resolve())
            self.assertFalse((root / "outside.txt").exists())

    def test_zip_import_enforces_extraction_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "roms.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("kernal", bytes(8192))

            with patch("c64app.roms.ZIP_MAX_EXTRACTED_BYTES", 4096):
                with self.assertRaisesRegex(ValueError, "safe extraction limit"):
                    import_roms(archive_path, root / "destination")

    def test_import_keeps_path_when_hash_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source = Path(source_tmp)
            self._write_rom_directory(source)
            with patch("c64app.roms.sha256_file", side_effect=OSError("read failed")):
                matches = import_roms(source, Path(dest_tmp))

            self.assertTrue(required_roms_ready(matches))
            self.assertIsNotNone(matches["kernal"].path)
            self.assertIsNone(matches["kernal"].sha256)


class CliTests(unittest.TestCase):
    def test_rom_status_handles_missing_hash(self) -> None:
        matches = {
            definition.key: RomMatch(
                definition,
                Path("/roms") / definition.canonical_name,
                None,
            )
            for definition in ROM_DEFINITIONS
        }
        with patch("c64app.cli.discover_roms", return_value=matches), patch("builtins.print"):
            self.assertTrue(_print_rom_status(Config()))


class LibraryTests(unittest.TestCase):
    def test_scan_filters_and_sorts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "z_game.prg").write_bytes(b"x")
            (root / "a-game.d64").write_bytes(b"x")
            (root / "ignore.txt").write_text("no")
            items = scan_library([root])
            self.assertEqual([item.title for item in items], ["a game", "z game"])


class CommandTests(unittest.TestCase):
    def _matches(self, include_drive: bool = True) -> dict[str, RomMatch]:
        matches: dict[str, RomMatch] = {}
        for definition in ROM_DEFINITIONS:
            path = Path("/roms") / definition.canonical_name
            if definition.key == "dos1541" and not include_drive:
                path = None
            matches[definition.key] = RomMatch(definition, path, "0" * 64 if path else None)
        return matches

    def test_accurate_command(self) -> None:
        command = build_command(
            Engine("native", ("x64sc",), "VICE"),
            Config(),
            self._matches(),
            Path("game.d64"),
        )
        self.assertIn("-drive8truedrive", command)
        self.assertIn("-autostart", command)
        self.assertIn("-dos1541", command)

    def test_fast_command_without_drive_rom(self) -> None:
        command = build_command(
            Engine("native", ("x64",), "VICE fast"),
            Config(profile="fast"),
            self._matches(include_drive=False),
            Path("game.prg"),
        )
        self.assertIn("+drive8truedrive", command)
        self.assertIn("-autostartprgmode", command)


if __name__ == "__main__":
    unittest.main()
