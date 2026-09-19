"""Загрузка файлов на PythonAnywhere через их API + перезагрузка веб-приложения.

Нужен, чтобы положить на хостинг артефакт, который не хранится в git
(сборка лаунчера SteamCloneLauncher.exe ~35 МБ).

Токен: PythonAnywhere -> Account -> API token -> "Create a new API token".

Примеры:
    # залить exe лаунчера и перезагрузить сайт
    python upload_to_pythonanywhere.py МОЙ_ЛОГИН ТОКЕН

    # произвольный файл
    python upload_to_pythonanywhere.py МОЙ_ЛОГИН ТОКЕН ^
        --local build_dist\\SteamCloneLauncher.exe ^
        --remote /home/МОЙ_ЛОГИН/steam_clone/static/downloads/SteamCloneLauncher.exe

    # EU-аккаунт
    python upload_to_pythonanywhere.py МОЙ_ЛОГИН ТОКЕН --host eu

Переменные окружения вместо аргументов: PA_USER, PA_TOKEN, PA_HOST.
"""
import argparse
import io
import os
import sys
import urllib.error
import urllib.request
import uuid


def api_base(host, username):
    host = {"www": "www.pythonanywhere.com", "eu": "eu.pythonanywhere.com",
            "us": "www.pythonanywhere.com"}.get(host, host)
    return host, f"https://{host}/api/v0/user/{username}/"


def upload(username, token, host, local_path, remote_path, timeout=900):
    if not os.path.isfile(local_path):
        print("!! нет файла:", local_path)
        return False
    hname, base = api_base(host, username)
    url = base + "files/path" + remote_path

    boundary = "----steamclone" + uuid.uuid4().hex
    size = os.path.getsize(local_path)
    print("-> %s (%d байт) => %s%s" % (local_path, size, hname, remote_path))

    body = io.BytesIO()
    body.write(("--%s\r\n" % boundary).encode())
    body.write((
        'Content-Disposition: form-data; name="content"; filename="%s"\r\n'
        % os.path.basename(local_path)).encode())
    body.write(b"Content-Type: application/octet-stream\r\n\r\n")
    with open(local_path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 256)
            if not chunk:
                break
            body.write(chunk)
    body.write(("\r\n--%s--\r\n" % boundary).encode())

    data = body.getvalue()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", "Token " + token)
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    req.add_header("Content-Length", str(len(data)))
    req.add_header("User-Agent", "steam-clone-uploader")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            print("   ответ:", resp.status, resp.read().decode("utf-8", "replace")[:200])
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print("   ОШИБКА", e.code, e.read().decode("utf-8", "replace")[:400])
        return False
    except Exception as e:
        print("   ОШИБКА сети:", type(e).__name__, e)
        return False


def reload_webapp(username, token, host, domain=None):
    domain = domain or f"{username}.pythonanywhere.com"
    hname, base = api_base(host, username)
    for url in (base + f"webapps/{domain}/reload/",
                f"https://{hname}/api/v1/user/{username}/websites/{domain}/reload/"):
        req = urllib.request.Request(url, data=b"", method="POST")
        req.add_header("Authorization", "Token " + token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                print("RELOAD:", resp.status, domain)
                return True
        except urllib.error.HTTPError as e:
            print("   reload %s -> %s %s" % (url.rsplit("/", 3)[-3], e.code,
                                             e.read().decode("utf-8", "replace")[:150]))
        except Exception as e:
            print("   reload ошибка сети:", type(e).__name__, e)
    print("!! не удалось перезагрузить", domain)
    return False


def main():
    ap = argparse.ArgumentParser(description="Загрузка файлов на PythonAnywhere")
    ap.add_argument("username", nargs="?", default=os.environ.get("PA_USER", ""))
    ap.add_argument("token", nargs="?", default=os.environ.get("PA_TOKEN", ""))
    ap.add_argument("--host", default=os.environ.get("PA_HOST", "www"),
                    help="www (US) или eu")
    ap.add_argument("--local", default="static/downloads/SteamCloneLauncher.exe")
    ap.add_argument("--remote", default=None,
                    help="абсолютный путь на сервере (по умолчанию .../steam_clone/static/downloads/)")
    ap.add_argument("--domain", default=None, help="домен веб-приложения")
    ap.add_argument("--no-reload", action="store_true")
    args = ap.parse_args()

    if not args.username or not args.token:
        print(__doc__)
        print("!! нужен логин и API-токен PythonAnywhere")
        return 1

    remote = args.remote or (
        f"/home/{args.username}/steam_clone/static/downloads/"
        + os.path.basename(args.local))
    ok = upload(args.username, args.token, args.host, args.local, remote)
    if ok and not args.no_reload:
        reload_webapp(args.username, args.token, args.host, args.domain)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
