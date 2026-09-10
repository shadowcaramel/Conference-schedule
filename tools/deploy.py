# -*- coding: utf-8 -*-
"""Publish site/ to the conference FTP (on demand — not after every edit).

Test locally first (open site/index.html or python -m http.server). Then:

    python tools/deploy.py --dry-run   # show what would change
    python tools/deploy.py             # upload files whose size differs
    python tools/deploy.py --build     # rebuild from Excel, then upload
    python tools/deploy.py --all       # overwrite every public file

Credentials: environment FTP_HOST / FTP_USER / FTP_PASS, or gitignored .ftp.env
in the repo root (copy from .ftp.env.example). Never commit the password.
"""
from __future__ import annotations

import os
import subprocess
import sys
from ftplib import FTP, error_perm
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROGRAMME_XLSX, ROOT, SITE_DIR, utf8_stdout  # noqa: E402

utf8_stdout()

ENV_FILE = ROOT / ".ftp.env"
SKIP_NAMES = {".nojekyll", "desktop.ini", "thumbs.db", ".ds_store"}
PUBLIC_URL_DEFAULT = "http://nucleus.togudv.ru/timetable/"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip('"').strip("'")
    for key in ("FTP_HOST", "FTP_PORT", "FTP_USER", "FTP_PASS", "FTP_PUBLIC_URL"):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def require_creds(env: dict[str, str]) -> tuple[str, int, str, str, str]:
    host = env.get("FTP_HOST", "").strip()
    user = env.get("FTP_USER", "").strip()
    password = env.get("FTP_PASS", "")
    url = env.get("FTP_PUBLIC_URL", PUBLIC_URL_DEFAULT).strip() or PUBLIC_URL_DEFAULT
    try:
        port = int(env.get("FTP_PORT", "21") or "21")
    except ValueError:
        port = 21
    missing = [n for n, v in (("FTP_HOST", host), ("FTP_USER", user), ("FTP_PASS", password)) if not v]
    if missing:
        print("Нет учётных данных FTP: " + ", ".join(missing))
        print(f"Скопируйте {ENV_FILE.name}.example → {ENV_FILE.name} и заполните пароль "
              "(файл в .gitignore, в git не попадёт).")
        raise SystemExit(1)
    return host, port, user, password, url


def skip_file(path: Path) -> bool:
    return path.name.lower() in SKIP_NAMES


def local_files() -> list[tuple[str, Path, int]]:
    out: list[tuple[str, Path, int]] = []
    for path in sorted(SITE_DIR.rglob("*")):
        if not path.is_file() or skip_file(path):
            continue
        rel = path.relative_to(SITE_DIR).as_posix()
        out.append((rel, path, path.stat().st_size))
    return out


def parse_mlsd_line(line: str) -> tuple[str, str, str] | None:
    facts, _, name = line.partition(" ")
    if name in (".", "..") or not name:
        return None
    parsed = dict(part.split("=", 1) for part in facts.rstrip(";").split(";") if "=" in part)
    return parsed.get("type", ""), parsed.get("size") or parsed.get("sizd") or "", name


def remote_tree(ftp: FTP) -> dict[str, int]:
    found: dict[str, int] = {}

    def walk(prefix: str) -> None:
        lines: list[str] = []
        ftp.retrlines("MLSD " + (prefix or "."), lines.append)
        for line in lines:
            parsed = parse_mlsd_line(line)
            if not parsed:
                continue
            typ, size, name = parsed
            path = f"{prefix}/{name}" if prefix else name
            if typ == "dir":
                walk(path)
            elif typ == "file" and size.isdigit():
                found[path] = int(size)

    walk("")
    return found


def ensure_dir(ftp: FTP, remote_dir: str) -> None:
    parts = [p for p in remote_dir.split("/") if p]
    cwd = ftp.pwd()
    try:
        for part in parts:
            try:
                ftp.cwd(part)
            except error_perm:
                ftp.mkd(part)
                ftp.cwd(part)
    finally:
        ftp.cwd(cwd)


def warn_if_stale() -> None:
    data_js = SITE_DIR / "data.js"
    if not PROGRAMME_XLSX.exists() or not data_js.exists():
        return
    if PROGRAMME_XLSX.stat().st_mtime > data_js.stat().st_mtime:
        print("ПРЕДУПРЕЖДЕНИЕ: data/programme.xlsx новее, чем site/data.js. "
              "Локально: python tools/build.py  —  на сервер: python tools/deploy.py --build")


def connect(host: str, port: int, user: str, password: str) -> FTP:
    ftp = FTP()
    ftp.connect(host, port, timeout=60)
    ftp.login(user, password)
    ftp.encoding = "utf-8"
    ftp.set_pasv(True)
    ftp.sendcmd("TYPE I")
    return ftp


def upload(ftp: FTP, local: Path, remote: str) -> int:
    parent = str(Path(remote).parent.as_posix())
    if parent not in ("", "."):
        ensure_dir(ftp, parent)
    with local.open("rb") as fh:
        ftp.storbinary("STOR " + remote, fh)
    try:
        got = ftp.size(remote)
    except Exception:
        got = None
    return int(got) if got is not None else -1


def run_build() -> int:
    cmd = [sys.executable, str(ROOT / "tools" / "build.py")]
    print("Сборка: " + " ".join(cmd))
    return subprocess.call(cmd)


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    force_all = "--all" in argv
    do_build = "--build" in argv
    if do_build:
        code = run_build()
        if code != 0:
            print("Сборка не удалась — на FTP ничего не отправлено.")
            return code

    warn_if_stale()
    host, port, user, password, public_url = require_creds(load_env())
    files = local_files()
    if not files:
        print(f"В {SITE_DIR} нет файлов для публикации.")
        return 1

    print(f"FTP {host}:{port}  пользователь {user}")
    if dry_run:
        print("Режим просмотра (--dry-run): загрузка не выполняется.")

    ftp = connect(host, port, user, password)
    try:
        remote = remote_tree(ftp)
        planned: list[tuple[str, Path, int, str]] = []
        for rel, path, size in files:
            old = remote.get(rel)
            if force_all or old is None:
                reason = "новый" if old is None else "принудительно"
                planned.append((rel, path, size, reason))
            elif old != size:
                planned.append((rel, path, size, f"размер {old} → {size}"))
            else:
                print(f"  без изменений  {rel}")

        if not planned:
            print("На сервере уже актуальные файлы site/. Excel и исходники не публикуются.")
            return 0

        print(f"К загрузке: {len(planned)}")
        uploaded = 0
        for rel, path, size, reason in planned:
            print(f"  {'будет' if dry_run else 'загрузка':8} {rel}  ({size} байт, {reason})")
            if dry_run:
                continue
            got = upload(ftp, path, rel)
            if got != size:
                print(f"ОШИБКА: {rel}: локально {size}, на сервере {got}")
                return 1
            uploaded += 1
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()

    if dry_run:
        print("Просмотр закончен. Чтобы отправить: python tools/deploy.py")
        return 0
    print(f"Готово: загружено {uploaded} файл(ов). Excel не отправлялся.")
    print("Проверьте: " + public_url.rstrip("/") + "/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
