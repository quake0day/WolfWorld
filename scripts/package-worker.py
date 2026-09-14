"""Create or verify the standalone worker download without runtime data."""
from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "public/downloads/wolfworld-worker.zip"
FILES = [".env.example", "Dockerfile", "README.md", "compose.yaml",
         "engine.py", "requirements.txt", "server.py", "test_worker.py"]


def entries():
    result = {f"wolfworld-worker/{name}": (ROOT / "worker" / name).read_bytes()
              for name in FILES}
    result["wolfworld-worker/LICENSE"] = (ROOT / "LICENSE").read_bytes()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = entries()
    if args.check:
        with ZipFile(ARCHIVE) as archive:
            if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
                raise SystemExit("Worker ZIP file list differs from the source manifest")
            for name, content in expected.items():
                if archive.read(name) != content:
                    raise SystemExit(f"Worker ZIP is stale: {name}")
        print(f"Worker ZIP matches {len(expected)} source files")
        return
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(expected.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    print(f"Packaged {len(expected)} files: {ARCHIVE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
