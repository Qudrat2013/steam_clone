"""Пуш локального коммита на GitHub через REST API.

Зачем: у части провайдеров `github.com:443` блокируется, но `api.github.com`
работает. Тогда обычный `git push` невозможен, а этот скрипт выгружает дерево
файлов через API и сдвигает ветку.

Токен берётся в таком порядке:
  1) аргумент  --token
  2) переменная окружения GH_TOKEN
  3) файл .git_token в корне проекта (одна строка; в git не попадает)

Токен нужен с правом «repo»: https://github.com/settings/tokens

Пример:
    python push_to_github_api.py
    python push_to_github_api.py --owner Qudrat2013 --repo steam_clone --branch main
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"


class Api:
    def __init__(self, token, owner, repo):
        self.token = token
        self.owner = owner
        self.repo = repo

    def __call__(self, path, method="GET", payload=None, timeout=300, tries=4):
        url = API + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        last = None
        for attempt in range(1, tries + 1):
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", "Bearer " + self.token)
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("User-Agent", "steam-clone-push")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            req.add_header("Connection", "close")
            if data:
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read().decode("utf-8") or "{}"), r.status
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8")[:600]
                if e.code in (500, 502, 503, 504) and attempt < tries:
                    print("   повтор %d: HTTP %s %s" % (attempt, e.code, path))
                    time.sleep(3 * attempt)
                    last = e
                    continue
                print("!! HTTP", e.code, method, path, body)
                raise
            except Exception as e:      # сеть оборвалась — повторяем
                if attempt < tries:
                    print("   повтор %d: %s" % (attempt, type(e).__name__))
                    time.sleep(3 * attempt)
                    last = e
                    continue
                raise
        raise last


def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def git_bytes(*args):
    return subprocess.run(["git"] + list(args), capture_output=True).stdout


def read_token(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("GH_TOKEN"):
        return os.environ["GH_TOKEN"]
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, ".git_token")
    if os.path.isfile(path):
        return open(path, encoding="utf-8").read().strip()
    return ""



def main():
    ap = argparse.ArgumentParser(description="Пуш на GitHub через API")
    ap.add_argument("--token", default=None)
    ap.add_argument("--owner", default=None)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()

    token = read_token(args.token)
    if not token:
        print("!! Нет токена. Положи его в .git_token или задай GH_TOKEN / --token")
        return 1

    remote_url = git("config", "--get", "remote.origin.url")
    parts = remote_url.replace(".git", "").rstrip("/").split("/")
    owner = args.owner or (parts[-2] if len(parts) >= 2 else "")
    repo = args.repo or (parts[-1] if parts else "")
    if not owner or not repo:
        print("!! Не понял owner/repo — задай --owner и --repo")
        return 1

    api = Api(token, owner, repo)
    ref, _ = api(f"/repos/{owner}/{repo}/git/ref/heads/{args.branch}")
    remote_sha = ref["object"]["sha"]
    remote_commit, _ = api(f"/repos/{owner}/{repo}/git/commits/{remote_sha}")
    local_sha = git("rev-parse", "HEAD")
    print(f"{owner}/{repo} [{args.branch}] remote: {remote_sha[:8]} -> local: {local_sha[:8]}")
    if remote_sha == local_sha:
        print("Уже синхронизировано.")
        return 0

    rtree, _ = api(
        f"/repos/{owner}/{repo}/git/trees/{remote_commit['tree']['sha']}?recursive=1")
    remote_map = {e["path"]: e["sha"] for e in rtree["tree"] if e["type"] == "blob"}

    entries, uploaded = [], 0
    for line in git("ls-tree", "-r", "HEAD").splitlines():
        meta, path = line.split("\t", 1)
        mode, _typ, blob_sha = meta.split()[:3]
        if remote_map.get(path) == blob_sha:
            entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob_sha})
            continue
        blob, _ = api(f"/repos/{owner}/{repo}/git/blobs", "POST", {
            "content": base64.b64encode(
                git_bytes("cat-file", "blob", blob_sha)).decode("ascii"),
            "encoding": "base64",
        })
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
        uploaded += 1
        print("  + %-60s %s" % (path, blob["sha"][:8]))
    print("файлов в коммите: %d | новых блобов: %d" % (len(entries), uploaded))

    author = {"name": git("log", "-1", "--pretty=%an"),
              "email": git("log", "-1", "--pretty=%ae"),
              "date": git("log", "-1", "--pretty=%aI")}
    committer = {"name": git("log", "-1", "--pretty=%cn"),
                 "email": git("log", "-1", "--pretty=%ce"),
                 "date": git("log", "-1", "--pretty=%cI")}

    tree, _ = api(f"/repos/{owner}/{repo}/git/trees", "POST", {"tree": entries})
    commit, _ = api(f"/repos/{owner}/{repo}/git/commits", "POST", {
        "message": git("log", "-1", "--pretty=%B"), "tree": tree["sha"],
        "parents": [remote_sha], "author": author, "committer": committer,
    })
    api(f"/repos/{owner}/{repo}/git/refs/heads/{args.branch}", "PATCH",
        {"sha": commit["sha"], "force": False})
    check, _ = api(f"/repos/{owner}/{repo}/git/ref/heads/{args.branch}")
    print("PUSHED:", check["object"]["sha"][:12])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())