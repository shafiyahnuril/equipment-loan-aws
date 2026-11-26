"""Smoke test untuk API yang sudah di-deploy di AWS.

Script ini hanya memakai library bawaan Python, jadi bisa dijalankan tanpa install apa pun.

Cara pakai:
    python tests/smoke_test.py https://abc123.execute-api.us-east-1.amazonaws.com

Alternatif, isi dulu environment variable API_URL lalu jalankan tanpa argumen.
Output di terminal dipakai sebagai bukti koneksi dan hasil pengujian.
"""

import json
import os
import sys
import urllib.error
import urllib.request

results = []


def call(method, base_url, path, body=None):
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, raw


def check(name, method, base_url, path, expected_status, body=None):
    status, payload = call(method, base_url, path, body)
    passed = status == expected_status
    results.append(passed)
    mark = "PASS" if passed else "FAIL"
    print("[%s] %s" % (mark, name))
    print("       %s %s" % (method, path))
    print("       status %s (diharapkan %s)" % (status, expected_status))
    if payload is not None:
        text = json.dumps(payload, ensure_ascii=False)
        print("       body   %s" % (text if len(text) < 300 else text[:300] + "..."))
    print()
    return payload


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("API_URL")
    if not base_url:
        print("Isi URL API dulu. Contoh:")
        print("  python tests/smoke_test.py https://abc123.execute-api.us-east-1.amazonaws.com")
        sys.exit(2)

    print("Menguji API: %s\n" % base_url)

    check("Health check (Lambda terhubung ke penyimpanan data)", "GET", base_url, "/health", 200)

    created = check(
        "Create peminjaman baru",
        "POST", base_url, "/loans", 201,
        {
            "borrowerName": "Shafiyah Nuril Hayya",
            "borrowerNim": "24/540586/TK/60019",
            "equipmentName": "ESP32 DevKit",
            "quantity": 2,
            "loanDate": "2026-11-27",
            "dueDate": "2026-12-04",
            "notes": "Data uji smoke test",
        },
    )
    loan_id = created["loanId"] if isinstance(created, dict) and "loanId" in created else None
    if not loan_id:
        print("Create gagal, pengujian dihentikan.")
        sys.exit(1)

    check("Read satu data", "GET", base_url, "/loans/" + loan_id, 200)
    check("Read daftar data", "GET", base_url, "/loans", 200)
    check("Update status menjadi RETURNED", "PUT", base_url, "/loans/" + loan_id, 200, {"status": "RETURNED"})
    check("Input tidak valid ditolak (quantity 0)", "POST", base_url, "/loans", 422,
          {"borrowerName": "Uji", "borrowerNim": "12345", "equipmentName": "Sensor",
           "quantity": 0, "loanDate": "2026-11-27", "dueDate": "2026-11-28"})
    check("Delete data uji", "DELETE", base_url, "/loans/" + loan_id, 204)
    check("Data yang sudah dihapus tidak ditemukan", "GET", base_url, "/loans/" + loan_id, 404)

    total, passed = len(results), sum(results)
    print("Ringkasan: %d dari %d pengujian lulus" % (passed, total))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
