"""Package only this documentation folder; never modify unrelated workspace files."""
import hashlib
import json
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
DEST = PACK.parent / (PACK.name + ".zip")


def main():
    files = sorted(p for p in PACK.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != "checksums.json")
    checksums = {str(p.relative_to(PACK)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    manifest = PACK / "source/checksums.json"
    manifest.write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
    files.append(manifest)
    with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        for path in files:
            archive.write(path, str(path.relative_to(PACK.parent)))
    with zipfile.ZipFile(DEST) as archive:
        assert archive.testzip() is None
        assert len(archive.infolist()) == len(files)
    print(f"Packaged {len(files)} files: {DEST} ({DEST.stat().st_size / 1048576:.2f} MiB)")


if __name__ == "__main__":
    main()
