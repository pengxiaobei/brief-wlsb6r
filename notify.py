#!/usr/bin/env python3
"""把 today.json 的完整内容推到飞书群。

本地和 GitHub Actions 共用这一份，避免两边逻辑漂移。

webhook 地址来源，按优先级：
  1. 环境变量 FEISHU_WEBHOOK（CI 里走 secret）
  2. ~/.config/daily-brief/feishu-webhook（本机）

内容日期不是今天时，推的是红色告警卡片而不是正常卡片——
简报停更必须有声音，否则用户只能自己发现。

用法：
    python3 notify.py            # 读 ./today.json
    python3 notify.py 某个.json  # 指定文件
"""

import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

PAGE_URL = "https://pengxiaobei.github.io/brief-wlsb6r/"
KIND = {"talk": "在聊", "you": "影响你", "tech": "科技"}
ROOT = pathlib.Path(__file__).parent


def get_webhook():
    hook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if hook:
        return hook
    f = pathlib.Path.home() / ".config/daily-brief/feishu-webhook"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    sys.exit("找不到 webhook：既没有 FEISHU_WEBHOOK 环境变量，也没有 ~/.config/daily-brief/feishu-webhook")


def build_card(d):
    stale = d.get("stamp") != datetime.date.today().isoformat()
    blocks = []

    if stale:
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"**⚠ 这是 {d.get('stamp')} 的内容，今天没生成成功。**\n"
            "去 GitHub Actions 看一眼哪一步挂了。"}})
        blocks.append({"tag": "hr"})

    items = d.get("items", [])
    for n, it in enumerate(items):
        if n:
            blocks.append({"tag": "hr"})
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"**【{KIND.get(it.get('kind'), '')}】{it.get('title', '')}**\n"
            f"{it.get('body', '')}"}})

    blocks.append({"tag": "hr"})
    blocks.append({"tag": "div", "text": {"tag": "lark_md",
                                          "content": f"[看网页版（含本周趋势）]({PAGE_URL})"}})

    return stale, {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                # 群机器人配了「简报」关键词校验，标题必须含这两个字
                "template": "red" if stale else "turquoise",
                "title": {"tag": "plain_text",
                          "content": ("简报 · 今天没生成成功" if stale
                                      else f"简报 · {d.get('stamp', '')}")},
            },
            "elements": blocks,
        },
    }


def main():
    src = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "today.json")
    if not src.exists():
        sys.exit(f"找不到 {src}")

    try:
        d = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"{src.name} 解析失败：{e}")

    stale, card = build_card(d)
    print(f"内容日期 {d.get('stamp')}，{len(d.get('items', []))} 条"
          + ("（已过期，发告警卡片）" if stale else ""))

    req = urllib.request.Request(
        get_webhook(),
        data=json.dumps(card, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"飞书返回 HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    except Exception as e:
        sys.exit(f"发送失败：{e}")

    if body.get("code") != 0:
        sys.exit(f"飞书拒收：{body}")
    print("✓ 飞书已送达")


if __name__ == "__main__":
    main()
