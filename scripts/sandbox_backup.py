"""Menyimpan progres Sandbox: snapshot konfigurasi, data peminjaman, dan zip Lambda.

Hanya membaca dari AWS. Hasil disimpan di .local/ (tidak masuk Git).
Pemakaian:  python scripts/sandbox_backup.py [--dry-run]
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime

from sandbox_common import LOCAL, AwsError, aws, aws_json, check_credentials, load_config


def find_bucket(cfg, account_id):
    for name in (cfg["dataBucketBase"], "%s-%s" % (cfg["dataBucketBase"], account_id)):
        code, _, _ = aws(["s3api", "head-bucket", "--bucket", name], cfg["region"], check=False)
        if code == 0:
            return name
    return None


def main():
    parser = argparse.ArgumentParser(description="Backup progres Sandbox (hanya membaca)")
    parser.add_argument("--dry-run", action="store_true", help="hanya cetak rencana")
    args = parser.parse_args()
    cfg = load_config()
    region = cfg["region"]
    account = check_credentials(region)
    bucket = find_bucket(cfg, account)
    print("Account: %s | Region: %s | Bucket data: %s" % (account, region, bucket or "TIDAK ADA"))
    if args.dry_run:
        print("[dry-run] Akan menyimpan snapshot ke .local/snapshot, data ke .local/backup/data, "
              "dan zip Lambda ke .local/backup/.")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snap_dir = LOCAL / "snapshot"
    data_dir = LOCAL / "backup" / "data"
    snap_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    fn = cfg["functionName"]
    snapshot = {"timestamp": stamp, "accountId": account, "dataBucket": bucket}
    steps = {
        "functionConfiguration": ["lambda", "get-function-configuration", "--function-name", fn],
        "functionUrlConfig": ["lambda", "get-function-url-config", "--function-name", fn],
        "policy": ["lambda", "get-policy", "--function-name", fn],
    }
    for key, cmd in steps.items():
        try:
            snapshot[key] = aws_json(cmd, region)
        except AwsError as e:
            snapshot[key] = {"error": e.stderr[:300]}
            print("Peringatan: %s gagal dibaca" % key)

    # Environment variable disimpan apa adanya karena nilainya hanya nama bucket dan jenis backend.
    count = 0
    if bucket:
        listing = aws_json(["s3api", "list-objects-v2", "--bucket", bucket, "--prefix", "loans/"], region)
        snapshot["objects"] = [{"key": o["Key"], "size": o["Size"]} for o in listing.get("Contents", [])]
        aws(["s3", "sync", "s3://%s/loans/" % bucket, str(data_dir), "--quiet"], region)
        count = len(list(data_dir.glob("*.json")))

    try:
        info = aws_json(["lambda", "get-function", "--function-name", fn], region)
        url = info["Code"]["Location"]
        zip_path = LOCAL / "backup" / "lambda-live.zip"
        urllib.request.urlretrieve(url, str(zip_path))
        snapshot["lambdaZipSha256"] = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        snapshot["lambdaCodeSha256"] = info["Configuration"].get("CodeSha256")
        print("Zip Lambda tersimpan: %s" % zip_path)
    except Exception as e:  # noqa: BLE001
        snapshot["lambdaZipError"] = str(e)[:200]
        print("Zip Lambda tidak bisa diunduh, hanya hash yang dicatat.")

    out = snap_dir / (stamp + ".json")
    out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print("\nRingkasan backup")
    print("  Snapshot : %s" % out)
    print("  Data     : %d file di %s" % (count, data_dir))
    print("Folder .local/ tidak masuk Git. Data berisi nama dan NIM, jangan dibagikan.")


if __name__ == "__main__":
    try:
        main()
    except AwsError as e:
        sys.exit("%s\n%s" % (e, e.stderr))
