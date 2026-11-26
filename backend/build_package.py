"""Membuat file dist/lambda.zip yang siap diunggah ke AWS Lambda.

Cara pakai (dari folder backend):
    python build_package.py

Dependency diunduh dalam versi Linux x86_64 untuk Python 3.12 walaupun script ini
dijalankan di Windows atau macOS. Hal ini penting karena pydantic-core berisi kode
biner yang harus cocok dengan lingkungan Lambda.
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
ZIP_PATH = DIST_DIR / "lambda.zip"

PYTHON_VERSION = "3.12"
PLATFORM = "manylinux2014_x86_64"


def install_dependencies() -> None:
    command = [
        sys.executable, "-m", "pip", "install",
        "-r", str(ROOT / "requirements.txt"),
        "--target", str(BUILD_DIR),
        "--platform", PLATFORM,
        "--python-version", PYTHON_VERSION,
        "--implementation", "cp",
        "--only-binary=:all:",
        "--upgrade",
        "--quiet",
    ]
    print("Mengunduh dependency untuk Lambda (Linux x86_64, Python %s)..." % PYTHON_VERSION)
    subprocess.run(command, check=True)


def copy_source() -> None:
    shutil.copytree(
        ROOT / "app",
        BUILD_DIR / "app",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def make_zip() -> None:
    DIST_DIR.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(BUILD_DIR.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(BUILD_DIR))


def main() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    BUILD_DIR.mkdir()

    install_dependencies()
    copy_source()
    make_zip()

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print("Selesai. File: %s (%.1f MB)" % (ZIP_PATH, size_mb))
    print("Handler Lambda: app.main.handler")
    if size_mb > 50:
        print("Peringatan: ukuran di atas 50 MB, unggah lewat S3 atau kurangi dependency.")


if __name__ == "__main__":
    main()
