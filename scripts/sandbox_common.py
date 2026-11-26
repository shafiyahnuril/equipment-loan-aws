"""Fungsi bersama untuk sandbox_backup.py dan sandbox_restore.py.

Memakai AWS CLI lewat subprocess (daftar argumen, tanpa shell) supaya tidak bermasalah
dengan quoting di Windows. Parameter JSON yang rumit dikirim lewat file sementara.
Script ini tidak pernah mencetak atau menyimpan kredensial.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / ".local"
CONFIG_PATH = ROOT / "scripts" / "sandbox_config.json"


class AwsError(Exception):
    def __init__(self, message, stderr=""):
        super().__init__(message)
        self.stderr = stderr


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def aws_path():
    path = shutil.which("aws")
    if not path:
        sys.exit("AWS CLI tidak ditemukan. Pasang AWS CLI v2 lalu buka terminal baru.")
    return path


def aws(args, region="us-east-1", check=True, capture=True):
    """Menjalankan satu perintah aws. Mengembalikan (kode, stdout, stderr)."""
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    cmd = [aws_path()] + list(args) + ["--region", region]
    result = subprocess.run(cmd, capture_output=capture, text=True, env=env, cwd=str(ROOT))
    if check and result.returncode != 0:
        raise AwsError("Perintah aws gagal: aws %s" % " ".join(args[:3]), result.stderr.strip())
    return result.returncode, result.stdout, result.stderr


def aws_json(args, region="us-east-1"):
    _, out, _ = aws(list(args) + ["--output", "json"], region)
    return json.loads(out) if out.strip() else {}


def write_tmp_json(name, data):
    """Menulis JSON ke .local/tmp dan mengembalikan alamat file:// relatif dari root repo."""
    folder = LOCAL / "tmp"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return "file://.local/tmp/" + name


def check_credentials(region):
    """Memastikan kredensial aktif dan mengembalikan Account ID."""
    code, out, err = aws(["sts", "get-caller-identity", "--output", "json"], region, check=False)
    if code != 0:
        sys.exit(
            "Kredensial AWS tidak valid atau sudah kedaluwarsa.\n"
            "Buka AWS Details di halaman Sandbox, salin ulang blok AWS CLI ke "
            "~/.aws/credentials (di luar repo), lalu jalankan script ini lagi.\n"
            "Detail: " + err.strip().splitlines()[-1][:200] if err.strip() else "tanpa pesan"
        )
    return json.loads(out)["Account"]
