from __future__ import annotations

import curses
import subprocess

from .config import Config, save_config
from .engine import build_command, choose_engine
from .library import LibraryItem, scan_library
from .roms import discover_roms, required_roms_ready


HELP = "Enter play  / search  p profile  f fullscreen  c CRT  d doctor  q quit"
MIN_HEIGHT = 8
MIN_WIDTH = 32


def _safe_addnstr(
    stdscr: curses.window,
    row: int,
    column: int,
    text: str,
    limit: int,
    attr: int = curses.A_NORMAL,
) -> None:
    height, width = stdscr.getmaxyx()
    if row < 0 or row >= height or column < 0 or column >= width or limit <= 0:
        return
    safe_limit = min(limit, width - column)
    if safe_limit <= 0:
        return
    try:
        stdscr.addnstr(row, column, text, safe_limit, attr)
    except curses.error:
        # A resize can invalidate coordinates between getmaxyx() and addnstr().
        pass


class Tui:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.items: list[LibraryItem] = scan_library(config.library_paths)
        self.filtered: list[LibraryItem] = self.items[:]
        self.index = 0
        self.offset = 0
        self.message = ""

    def run(self, stdscr: curses.window) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        while True:
            self.draw(stdscr)
            key = stdscr.getch()
            if key in (ord("q"), 27):
                save_config(self.config)
                return
            if key in (curses.KEY_DOWN, ord("j")):
                self.index = min(len(self.filtered) - 1, self.index + 1) if self.filtered else 0
            elif key in (curses.KEY_UP, ord("k")):
                self.index = max(0, self.index - 1)
            elif key in (curses.KEY_NPAGE,):
                self.index = min(len(self.filtered) - 1, self.index + 10) if self.filtered else 0
            elif key in (curses.KEY_PPAGE,):
                self.index = max(0, self.index - 10)
            elif key in (10, 13, curses.KEY_ENTER):
                self.play_selected(stdscr)
            elif key == ord("/"):
                self.search(stdscr)
            elif key == ord("p"):
                profiles = ["accurate", "fast", "crt"]
                self.config.profile = profiles[(profiles.index(self.config.profile) + 1) % len(profiles)]
                self.message = f"Profile: {self.config.profile}"
            elif key == ord("f"):
                self.config.fullscreen = not self.config.fullscreen
                self.message = f"Fullscreen: {'on' if self.config.fullscreen else 'off'}"
            elif key == ord("c"):
                self.config.crt_filter = not self.config.crt_filter
                self.message = f"CRT filter: {'on' if self.config.crt_filter else 'off'}"
            elif key == ord("d"):
                self.doctor_message()
            elif key == curses.KEY_RESIZE:
                continue

    def draw(self, stdscr: curses.window) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            _safe_addnstr(stdscr, 0, 0, " C64 // TERMINAL TOO SMALL ", width, curses.A_REVERSE)
            _safe_addnstr(
                stdscr,
                1,
                0,
                f"Resize to at least {MIN_WIDTH}x{MIN_HEIGHT}. Current: {width}x{height}",
                max(0, width - 1),
            )
            try:
                stdscr.refresh()
            except curses.error:
                pass
            return

        title = " C64 // SIMPLE LINUX FRONT END "
        _safe_addnstr(stdscr, 0, 0, title.ljust(width), width, curses.A_REVERSE)
        status = (
            f"Profile:{self.config.profile}  Region:{self.config.region.upper()}  "
            f"Fullscreen:{'Y' if self.config.fullscreen else 'N'}  CRT:{'Y' if self.config.crt_filter else 'N'}"
        )
        _safe_addnstr(stdscr, 1, 0, status, width - 1)
        _safe_addnstr(stdscr, 2, 0, f"Library: {len(self.filtered)} image(s)", width - 1)

        list_top = 4
        list_height = max(1, height - 7)
        if self.index < self.offset:
            self.offset = self.index
        if self.index >= self.offset + list_height:
            self.offset = self.index - list_height + 1

        if not self.filtered:
            _safe_addnstr(
                stdscr,
                list_top,
                2,
                "No games found. Run: c64 setup --library ~/Games/C64",
                width - 4,
            )
        else:
            for row, item in enumerate(self.filtered[self.offset : self.offset + list_height], start=list_top):
                absolute = self.offset + (row - list_top)
                marker = ">" if absolute == self.index else " "
                line = f"{marker} [{item.kind:<3}] {item.title}  —  {item.path}"
                attr = curses.A_BOLD if absolute == self.index else curses.A_NORMAL
                _safe_addnstr(stdscr, row, 0, line, width - 1, attr)

        footer = self.message or HELP
        _safe_addnstr(stdscr, height - 2, 0, footer.ljust(width), width, curses.A_REVERSE)
        _safe_addnstr(stdscr, height - 1, 0, "QSOLKCB/C64 — no ROM scavenger hunt, no menu maze", width - 1)
        try:
            stdscr.refresh()
        except curses.error:
            pass

    def search(self, stdscr: curses.window) -> None:
        height, width = stdscr.getmaxyx()
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            self.message = f"Resize to at least {MIN_WIDTH}x{MIN_HEIGHT} before searching"
            return
        query = ""
        curses.echo()
        curses.curs_set(1)
        _safe_addnstr(stdscr, height - 2, 0, "Search: ".ljust(width), width, curses.A_REVERSE)
        try:
            stdscr.move(height - 2, len("Search: "))
            query = stdscr.getstr(
                height - 2,
                len("Search: "),
                max(1, width - len("Search: ") - 1),
            ).decode("utf-8", "replace")
        except curses.error:
            self.message = "Search cancelled after terminal resize"
        finally:
            curses.noecho()
            curses.curs_set(0)
        if not query:
            self.filtered = self.items[:]
        else:
            q = query.casefold()
            self.filtered = [item for item in self.items if q in item.title.casefold() or q in str(item.path).casefold()]
        self.index = 0
        self.offset = 0
        if query:
            self.message = f"Search results: {len(self.filtered)}"

    def doctor_message(self) -> None:
        engine = choose_engine(self.config)
        matches = discover_roms(self.config.resolved_rom_dir)
        rom_text = "ROMs ready" if required_roms_ready(matches) else "ROMs missing"
        engine_text = engine.display_name if engine else "engine missing"
        self.message = f"Doctor: {engine_text}; {rom_text}"

    def play_selected(self, stdscr: curses.window) -> None:
        if not self.filtered:
            self.message = "Nothing selected"
            return
        engine = choose_engine(self.config)
        if not engine:
            self.message = "VICE not found. Run c64 doctor."
            return
        matches = discover_roms(self.config.resolved_rom_dir)
        if not required_roms_ready(matches):
            self.message = "ROMs incomplete. Run c64 setup /path/to/roms."
            return
        command = build_command(engine, self.config, matches, self.filtered[self.index].path)
        save_config(self.config)
        curses.def_prog_mode()
        curses.endwin()
        try:
            subprocess.run(command, check=False)
        finally:
            curses.reset_prog_mode()
            stdscr.refresh()
        self.message = "Emulator closed"


def run_tui(config: Config) -> None:
    if not hasattr(curses, "wrapper"):
        raise RuntimeError("This Python build does not include curses support")
    curses.wrapper(Tui(config).run)
