"""Reassemble the v0.9 source ZIP from GitHub-compatible binary shards.

Only stdlib required. Run: python releases/v0.9/restore.py
"""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PARTS = sorted((ROOT / "releases" / "v0.9").glob("source.zip.part*"))
SHA256 = "e474a1ea31293f5ea0dff2d4ffd89b72d473ec9391554acdab6323e7ea794e50"
SIZE = 7038766

if __name__ == "__main__":
    if len(PARTS) != 20:
        raise SystemExit(f"Expected 20 parts, found {len(PARTS)}")
    output = ROOT / "ProfMonkeyDesktop-v0.9-full.zip"
    digest = hashlib.sha256()
    size = 0
    with output.open("wb") as dest:
        for source in PARTS:
            with source.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    dest.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
    if size != SIZE or digest.hexdigest() != SHA256:
        output.unlink(missing_ok=True)
        raise SystemExit("ERROR: archive parts damaged or out of order")
    with zipfile.ZipFile(output) as z:
        bad = z.testzip()
        if bad is not None:
            output.unlink(missing_ok=True)
            raise SystemExit(f"ERROR: corrupt ZIP entry: {bad}")
    print(f"OK: {output} ({size} bytes); SHA-256 verified")
    print("Extract ZIP then run setup_windows.bat on Windows.")
