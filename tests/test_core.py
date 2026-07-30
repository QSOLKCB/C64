from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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
    def test_import_by_filename_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source = Path(source_tmp)
            for definition in ROM_DEFINITIONS:
                (source / definition.aliases[0]).write_bytes(bytes(definition.size))
            matches = import_roms(source, Path(dest_tmp))
            self.assertTrue(required_roms_ready(matches))
            self.assertTrue(matches["dos1541"].path and matches["dos1541"].path.exists())


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
