"""Recover ONLY existing v0.9 binary artwork into current checkout.

Never replace the current source, HTML, Python, JSON or documentation.
The v0.9 shard restorer verifies SHA-256 before this script reads the ZIP.
This is a compatibility fallback, NOT recovery of missing v0.10 pixel art.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'ProfMonkeyDesktop-v0.9-full.zip'
ALLOWED_TOP = {'assets', 'site', 'docs'}
ALLOWED_EXT = {'.png', '.gif', '.wav', '.ico', '.jpg', '.jpeg', '.webp'}
PREFIX = ('profmonkey-desktop',)
MAX_SINGLE_FILE = 12_000_000
MAX_TOTAL_BYTES = 80_000_000


def restore() -> tuple[int, int]:
    subprocess.run([sys.executable, str(ROOT / 'releases/v0.9/restore.py')],
                   check=True, cwd=ROOT)
    copied = skipped = consumed = 0
    with zipfile.ZipFile(ARCHIVE) as z:
        for item in z.infolist():
            if item.is_dir():
                continue
            raw = PurePosixPath(item.filename)
            parts = raw.parts
            if (len(parts) < 3 or parts[0] != PREFIX[0]
                    or parts[1] not in ALLOWED_TOP or
                    raw.suffix.lower() not in ALLOWED_EXT):
                continue
            if (raw.is_absolute() or '..' in parts or item.file_size > MAX_SINGLE_FILE):
                raise ValueError('unsafe archive binary path/size')
            consumed += item.file_size
            if consumed > MAX_TOTAL_BYTES:
                raise ValueError('archive exceeds binary recovery limit')
            path = ROOT.joinpath(*parts[1:])
            if path.is_file():
                skipped += 1
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive create avoids overwriting independently authored artwork.
            with z.open(item) as stream, path.open('xb') as dest:
                while chunk := stream.read(1024 * 1024):
                    dest.write(chunk)
            copied += 1
    print(f'Restored {copied} binary assets; preserved {skipped} existing assets')
    return copied, skipped


if __name__ == '__main__':
    restore()
