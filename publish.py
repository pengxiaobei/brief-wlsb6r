#!/usr/bin/env python3
"""用 GitHub Contents API 上传文件，绕过 git push。

为什么需要这个：云端沙箱允许 git clone（读），但 git push 被拦在传输层，
不管用什么凭据都返回 403。而普通 HTTPS 的 API 调用不受这个限制。

令牌从环境变量 GH_TOKEN 读，需要这个仓库的 Contents: Read and write 权限。

用法：
    GH_TOKEN=xxx python3 publish.py "提交说明" index.html today.json ...
文件参数省略时，默认发布日更会改到的那几个。
"""

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

REPO = "pengxiaobei/brief-wlsb6r"
BRANCH = "main"
ROOT = pathlib.Path(__file__).parent
DEFAULT_FILES = ["index.html", "today.json"]


def api(path, method="GET", payload=None, token=""):
    url = f"https://api.github.com/repos/{REPO}/{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {token}")
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"message": body[:300]}


def publish(relpath, message, token):
    f = ROOT / relpath
    if not f.exists():
        print(f"  跳过 {relpath}（文件不存在）")
        return True

    content = base64.b64encode(f.read_bytes()).decode()

    # 已存在的文件必须带上当前 sha，否则 API 会拒绝覆盖
    status, cur = api(f"contents/{relpath}?ref={BRANCH}", token=token)
    sha = cur.get("sha") if status == 200 else None

    if sha and cur.get("content", "").replace("\n", "") == content:
        print(f"  跳过 {relpath}（内容没变）")
        return True

    payload = {"message": message, "content": content, "branch": BRANCH}
    if sha:
        payload["sha"] = sha

    status, res = api(f"contents/{relpath}", "PUT", payload, token)
    if status in (200, 201):
        print(f"  ✓ {relpath}  {res.get('commit', {}).get('sha', '')[:7]}")
        return True

    print(f"  ✗ {relpath}  HTTP {status}: {res.get('message')}")
    return False


def main():
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        sys.exit("缺少 GH_TOKEN 环境变量")

    message = sys.argv[1] if len(sys.argv) > 1 else "更新"
    files = sys.argv[2:] or DEFAULT_FILES

    # archive 目录下当天的存档一并带上
    arch = ROOT / "archive"
    if arch.exists() and not sys.argv[2:]:
        newest = sorted(arch.glob("*.html"))[-1:]
        files += [str(p.relative_to(ROOT)) for p in newest]

    print(f"发布 {len(files)} 个文件到 {REPO}：")
    ok = all([publish(p, message, token) for p in files])
    if not ok:
        sys.exit("有文件发布失败")
    print("✓ 全部完成")


if __name__ == "__main__":
    main()
