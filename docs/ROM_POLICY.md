# ROM policy

## The problem

A C64 emulator needs machine firmware. On some Linux distributions the VICE package is built without Commodore ROM images because those images are not freely redistributable. Users then encounter a broken first launch and are expected to discover filenames, byte sizes and hidden search paths themselves.

## What C64 does

C64 removes the scavenger hunt without redistributing proprietary data:

1. Searches common VICE, XDG and installation paths automatically.
2. Identifies files by role, known aliases and exact size.
3. Imports a directory or ZIP archive with one command.
4. Stores files in a stable per-user location.
5. Supplies the resolved paths explicitly to VICE.
6. Reports a SHA-256 fingerprint so users can identify what was imported.

## What C64 does not do

- It does not contain Commodore ROM images.
- It does not silently scrape or download ROMs.
- It does not claim that possession of a ROM is lawful in every jurisdiction.
- It does not treat a matching byte size as proof of authenticity.

## Expected files

| Role | Canonical filename | Exact size |
|---|---|---:|
| C64 KERNAL | `C64/kernal` | 8192 bytes |
| C64 BASIC | `C64/basic` | 8192 bytes |
| C64 character generator | `C64/chargen` | 4096 bytes |
| 1541 drive DOS | `DRIVES/dos1541` | 16384 bytes |

The first three are required to boot. The 1541 ROM is recommended for true-drive compatibility. When it is absent, C64 tells VICE to use virtual drive loading rather than failing mysteriously.

## Future replacement ROMs

A clean-room open replacement ROM could eventually provide a legally redistributable first-boot mode. It should only become the default when it passes a published compatibility suite and the project can clearly explain which commercial games, demos and fast loaders remain incompatible.
