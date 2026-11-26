"""Menghidupkan kembali backend Jalur D (S3 + Lambda + Function URL). Idempotent.

Pemakaian (dari root repo):
    python scripts/sandbox_restore.py --dry-run
    python scripts/sandbox_restore.py [--restore-data | --seed] [--frontend]
"""

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

from sandbox_common import LOCAL, ROOT, AwsError, aws, aws_json, check_credentials, load_config, write_tmp_json

DRY = False
changes = []


def say(msg):
    print(("[dry-run] " if DRY else "") + msg)


def exists(cmd, region):
    return aws(cmd, region, check=False)[0] == 0


def ensure_bucket(cfg, account, base, public=False):
    region = cfg["region"]
    for name in (base, "%s-%s" % (base, account)):
        code, _, err = aws(["s3api", "head-bucket", "--bucket", name], region, check=False)
        if code == 0:
            say("Bucket %s sudah ada, dipakai ulang." % name)
            return name
        if "404" in err or "Not Found" in err:
            say("Membuat bucket %s" % name)
            if not DRY:
                aws(["s3api", "create-bucket", "--bucket", name], region)
                if not public:
                    aws(["s3api", "put-public-access-block", "--bucket", name, "--public-access-block-configuration",
                         "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"], region)
            changes.append("Bucket %s dibuat" % name)
            return name
    sys.exit("Nama bucket %s dan variasinya tidak bisa dipakai (dimiliki akun lain)." % base)


def ensure_zip():
    zip_path = ROOT / "backend" / "dist" / "lambda.zip"
    newest = max(p.stat().st_mtime for p in (ROOT / "backend" / "app").glob("*.py"))
    newest = max(newest, (ROOT / "backend" / "requirements.txt").stat().st_mtime)
    if zip_path.exists() and zip_path.stat().st_mtime >= newest:
        say("Zip Lambda sudah terbaru: %s" % zip_path)
    else:
        say("Membangun zip Lambda (butuh internet)")
        if not DRY:
            subprocess.run([sys.executable, str(ROOT / "backend" / "build_package.py")], check=True, cwd=str(ROOT / "backend"))
    return zip_path


def ensure_lambda(cfg, role_arn, bucket, zip_path):
    region, fn = cfg["region"], cfg["functionName"]
    env_file = write_tmp_json("restore-env.json", {"Variables": {"STORAGE_BACKEND": "s3", "DATA_BUCKET": bucket}})
    if not exists(["lambda", "get-function", "--function-name", fn], region):
        say("Membuat Lambda %s" % fn)
        if not DRY:
            aws(["lambda", "create-function", "--function-name", fn, "--runtime", cfg["runtime"], "--architectures", "x86_64",
                 "--handler", cfg["handler"], "--role", role_arn, "--zip-file", "fileb://" + str(zip_path),
                 "--timeout", str(cfg["timeout"]), "--memory-size", str(cfg["memorySize"]), "--environment", env_file], region)
            aws(["lambda", "wait", "function-active-v2", "--function-name", fn], region)
        changes.append("Lambda %s dibuat" % fn)
        return
    info = aws_json(["lambda", "get-function-configuration", "--function-name", fn], region)
    local_sha = base64.b64encode(hashlib.sha256(zip_path.read_bytes()).digest()).decode() if zip_path.exists() else ""
    if local_sha and info.get("CodeSha256") != local_sha:
        say("Kode Lambda berbeda, memperbarui kode")
        if not DRY:
            aws(["lambda", "update-function-code", "--function-name", fn, "--zip-file", "fileb://" + str(zip_path)], region)
            aws(["lambda", "wait", "function-updated-v2", "--function-name", fn], region)
        changes.append("Kode Lambda diperbarui")
    else:
        say("Kode Lambda sudah sama.")
    variables = (info.get("Environment") or {}).get("Variables", {})
    same = (variables.get("STORAGE_BACKEND") == "s3" and variables.get("DATA_BUCKET") == bucket
            and info.get("Handler") == cfg["handler"] and info.get("MemorySize") == cfg["memorySize"]
            and info.get("Timeout") == cfg["timeout"] and info.get("Role") == role_arn)
    if same:
        say("Konfigurasi Lambda sudah sesuai.")
    else:
        say("Memperbarui konfigurasi Lambda")
        if not DRY:
            aws(["lambda", "update-function-configuration", "--function-name", fn, "--handler", cfg["handler"], "--role", role_arn,
                 "--timeout", str(cfg["timeout"]), "--memory-size", str(cfg["memorySize"]), "--environment", env_file], region)
            aws(["lambda", "wait", "function-updated-v2", "--function-name", fn], region)
        changes.append("Konfigurasi Lambda diperbarui")


def ensure_url(cfg, extra_origins=()):
    region, fn = cfg["region"], cfg["functionName"]
    origins = list(cfg["corsOrigins"]) + [o for o in extra_origins if o not in cfg["corsOrigins"]]
    cors = {"AllowOrigins": origins, "AllowMethods": cfg["corsMethods"], "AllowHeaders": cfg["corsHeaders"]}
    cors_file = write_tmp_json("restore-cors.json", cors)
    existing = None
    code, out, _ = aws(["lambda", "get-function-url-config", "--function-name", fn, "--output", "json"], region, check=False)
    if code == 0:
        existing = json.loads(out)
    if existing is None:
        say("Membuat Function URL (auth NONE)")
        if DRY:
            url = "https://<dry-run>.lambda-url.us-east-1.on.aws"
        else:
            url = aws_json(["lambda", "create-function-url-config", "--function-name", fn, "--auth-type", "NONE",
                            "--cors", cors_file], region)["FunctionUrl"]
        changes.append("Function URL dibuat")
    else:
        url = existing["FunctionUrl"]
        have = existing.get("Cors", {})
        if (sorted(have.get("AllowOrigins", [])) != sorted(cors["AllowOrigins"])
                or sorted(have.get("AllowMethods", [])) != sorted(cors["AllowMethods"])):
            say("Memperbarui CORS Function URL")
            if not DRY:
                aws(["lambda", "update-function-url-config", "--function-name", fn, "--auth-type", "NONE", "--cors", cors_file], region)
            changes.append("CORS Function URL diperbarui")
        else:
            say("Function URL dan CORS sudah sesuai.")
    code, out, _ = aws(["lambda", "get-policy", "--function-name", fn, "--output", "json"], region, check=False)
    policy = json.loads(json.loads(out)["Policy"]) if code == 0 else {"Statement": []}
    sids = {s.get("Sid") for s in policy["Statement"]}
    if "FunctionURLAllowPublicAccess" not in sids:
        say("Menambah izin lambda:InvokeFunctionUrl")
        if not DRY:
            aws(["lambda", "add-permission", "--function-name", fn, "--statement-id", "FunctionURLAllowPublicAccess",
                 "--action", "lambda:InvokeFunctionUrl", "--principal", "*", "--function-url-auth-type", "NONE"], region)
        changes.append("Izin InvokeFunctionUrl ditambah")
    if "FunctionURLInvokeFunction" not in sids:
        say("Menambah izin lambda:InvokeFunction")
        if not DRY:
            aws(["lambda", "add-permission", "--function-name", fn, "--statement-id", "FunctionURLInvokeFunction",
                 "--action", "lambda:InvokeFunction", "--principal", "*", "--invoked-via-function-url"], region)
        changes.append("Izin InvokeFunction ditambah")
    return url.rstrip("/")


def web_origin(cfg, web):
    return "http://%s.s3-website-%s.amazonaws.com" % (web, cfg["region"])


def ensure_website(cfg, web):
    """Membuka akses baca publik HANYA untuk bucket website dan mengaktifkan static website hosting."""
    region = cfg["region"]
    policy = {"Version": "2012-10-17", "Statement": [{"Sid": "PublicReadWebsite", "Effect": "Allow", "Principal": "*",
                                                       "Action": "s3:GetObject", "Resource": "arn:aws:s3:::%s/*" % web}]}
    code, out, _ = aws(["s3api", "get-public-access-block", "--bucket", web, "--output", "json"], region, check=False)
    block = json.loads(out)["PublicAccessBlockConfiguration"] if code == 0 else {}
    if block.get("BlockPublicPolicy") is False and block.get("RestrictPublicBuckets") is False:
        say("Public Access Block bucket website sudah sesuai.")
    else:
        say("Melonggarkan Public Access Block khusus bucket %s (policy publik diizinkan, ACL tetap diblokir)" % web)
        if not DRY:
            aws(["s3api", "put-public-access-block", "--bucket", web, "--public-access-block-configuration",
                 "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false"], region)
        changes.append("Public Access Block bucket website dilonggarkan")
    code, out, _ = aws(["s3api", "get-bucket-policy", "--bucket", web, "--output", "json"], region, check=False)
    if code == 0 and json.loads(json.loads(out)["Policy"]) == policy:
        say("Bucket policy website sudah sesuai.")
    else:
        say("Memasang bucket policy s3:GetObject untuk %s/*" % web)
        if not DRY:
            aws(["s3api", "put-bucket-policy", "--bucket", web, "--policy", write_tmp_json("restore-web-policy.json", policy)], region)
        changes.append("Bucket policy website dipasang")
    wanted = {"IndexDocument": {"Suffix": "index.html"}, "ErrorDocument": {"Key": "404.html"}}
    code, out, _ = aws(["s3api", "get-bucket-website", "--bucket", web, "--output", "json"], region, check=False)
    have = json.loads(out) if code == 0 else {}
    if have.get("IndexDocument") == wanted["IndexDocument"] and have.get("ErrorDocument") == wanted["ErrorDocument"]:
        say("Static website hosting sudah sesuai.")
    else:
        say("Mengaktifkan static website hosting")
        if not DRY:
            aws(["s3api", "put-bucket-website", "--bucket", web, "--website-configuration", write_tmp_json("restore-web.json", wanted)], region)
        changes.append("Static website hosting diaktifkan")


def deploy_frontend(cfg, url, web):
    env_path = ROOT / "frontend" / ".env.production"
    content = "NEXT_PUBLIC_API_URL=%s\n" % url
    current = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if current != content:
        say("Memperbarui frontend/.env.production")
        changes.append(".env.production diperbarui")
    say("Build frontend lalu sinkronkan out/ ke root s3://%s" % web)
    if DRY:
        return
    env_path.write_text(content, encoding="utf-8")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.run([npm, "ci"], check=True, cwd=str(ROOT / "frontend"))
    subprocess.run([npm, "run", "build"], check=True, cwd=str(ROOT / "frontend"))
    _, out, _ = aws(["s3", "sync", str(ROOT / "frontend" / "out"), "s3://%s" % web, "--delete"], cfg["region"])
    if out.strip():
        changes.append("Isi website disinkronkan (%d perubahan)" % len(out.strip().splitlines()))


def verify_website(origin):
    if DRY:
        return None
    try:
        status, body = http("GET", origin + "/")
        return status == 200 and "<html" in body.lower()
    except Exception as e:  # noqa: BLE001
        print("Website belum bisa dibuka: %s" % str(e)[:100])
        return False


def http(method, url, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode()


def verify(url):
    ok = False
    for attempt in range(6):
        try:
            status, body = http("GET", url + "/health")
            ok = status == 200 and json.loads(body).get("storage") == "s3"
            print("Health: HTTP %s %s" % (status, body))
            break
        except Exception as e:  # noqa: BLE001
            print("Health belum siap (percobaan %d): %s" % (attempt + 1, str(e)[:80]))
            time.sleep(8)
    if not ok:
        return False
    return subprocess.run([sys.executable, str(ROOT / "backend" / "tests" / "smoke_test.py"), url]).returncode == 0


def seed(url):
    sample = json.loads((ROOT / "tests" / "sample-loan.json").read_text(encoding="utf-8"))
    for eq in ["ESP32 DevKit", "Oscilloscope Rigol", "Multimeter Fluke", "Raspberry Pi 4"]:
        sample["equipmentName"] = eq
        status, _ = http("POST", url + "/loans", sample)
        print("  POST /loans %s -> %s" % (eq, status))


def main():
    global DRY
    p = argparse.ArgumentParser(description="Restore backend Jalur D di Sandbox")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--restore-data", action="store_true", help="unggah .local/backup/data ke bucket")
    p.add_argument("--seed", action="store_true", help="isi data contoh lewat API")
    p.add_argument("--frontend", action="store_true", help="siapkan bucket website, build, dan unggah frontend")
    a = p.parse_args()
    if a.restore_data and a.seed:
        sys.exit("--restore-data dan --seed tidak boleh dipakai bersamaan.")
    DRY = a.dry_run
    cfg = load_config()
    region = cfg["region"]
    account = check_credentials(region)
    role_arn = aws_json(["iam", "get-role", "--role-name", cfg["roleName"]], region)["Role"]["Arn"]
    print("Account: %s | Role: %s | Region: %s" % (account, role_arn, region))

    bucket = ensure_bucket(cfg, account, cfg["dataBucketBase"])
    zip_path = ensure_zip()
    ensure_lambda(cfg, role_arn, bucket, zip_path)
    web = ensure_bucket(cfg, account, cfg["webBucketBase"], public=True) if a.frontend else None
    url = ensure_url(cfg, [web_origin(cfg, web)] if web else [])

    if a.restore_data:
        data_dir = LOCAL / "backup" / "data"
        say("Mengunggah data dari %s ke s3://%s/loans/" % (data_dir, bucket))
        if not DRY:
            aws(["s3", "sync", str(data_dir), "s3://%s/loans/" % bucket, "--quiet"], region)
        changes.append("Data dipulihkan dari backup")
    if a.seed and not DRY:
        print("Mengisi data contoh:")
        seed(url)
        changes.append("Data contoh ditambahkan")
    site_ok = None
    if a.frontend:
        ensure_website(cfg, web)
        deploy_frontend(cfg, url, web)
        site_ok = verify_website(web_origin(cfg, web))

    result = None
    if not DRY:
        result = verify(url)
        LOCAL.mkdir(exist_ok=True)
        (LOCAL / "last_deploy.json").write_text(json.dumps(
            {"time": datetime.now().isoformat(timespec="seconds"), "accountId": account, "functionUrl": url,
             "dataBucket": bucket, "verified": bool(result)}, indent=2), encoding="utf-8")

    print("\nRingkasan restore")
    print("  Function URL : %s" % url)
    print("  Bucket data  : %s" % bucket)
    print("  Verifikasi   : %s" % ("dry-run, dilewati" if DRY else ("LULUS" if result else "GAGAL")))
    if web:
        print("  Website      : %s (%s)" % (web_origin(cfg, web), "dry-run, dilewati" if DRY else ("LULUS" if site_ok else "GAGAL")))
    print("  Perubahan    : %s" % (", ".join(changes) if changes else "tidak ada, semua sudah sesuai"))
    print("Ingat: Function URL berbeda tiap Start Lab. Perbarui frontend/.env.production, "
          "CORS (sandbox_config.json) dan dokumen yang menyebut URL lama.")


if __name__ == "__main__":
    try:
        main()
    except AwsError as e:
        sys.exit("%s\n%s" % (e, e.stderr))
