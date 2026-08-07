#!/usr/bin/env python3
"""每天早上 08:00 往飞书群推一条卡片，把人引到网页版。

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
# 卡片只推最重要的那一条。读者现在会在碎片时间主动开网页，
# 飞书的职责已经从「简报本体」降级成「今天开始了，有空去看看」的钩子。
TOP_N = 1
ROOT = pathlib.Path(__file__).parent


def get_webhook():
    hook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if hook:
        return hook
    f = pathlib.Path.home() / ".config/daily-brief/feishu-webhook"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    sys.exit("找不到 webhook：既没有 FEISHU_WEBHOOK 环境变量，也没有 ~/.config/daily-brief/feishu-webhook")


def beijing_today():
    """按北京时间算今天几号。

    不能用 date.today()：CI runner 默认跑在 UTC，早上 8 点推送时 UTC 还是前一天，
    会把当天的内容误判成过期，天天推一张红色告警卡。
    这里写死 +8，跟运行环境的时区无关。
    """
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    return now.date().isoformat()


def build_card(d):
    stale = d.get("stamp") != beijing_today()
    blocks = []

    if stale:
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"**⚠ 这是 {d.get('stamp')} 的内容，今天没生成成功。**\n"
            "去 GitHub Actions 看一眼哪一步挂了。"}})
        blocks.append({"tag": "hr"})

    # 推 08:00 这一刻最重要的那条。items 已按重要性排序（见 prompts/daily.md）。
    all_items = d.get("items", [])
    items = all_items[:TOP_N]
    rest = len(all_items) - len(items)

    for n, it in enumerate(items):
        if n:
            blocks.append({"tag": "hr"})
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"**【{KIND.get(it.get('kind'), '')}】{it.get('title', '')}**\n"
            f"{it.get('body', '')}"}})

    blocks.append({"tag": "hr"})
    # 白天还会跑 11:30 和 17:00 两轮，所以这里说的是「今天还会更新」，不是「就这些了」
    tail = f"今天还有 {rest} 条，白天陆续更新，" if rest > 0 else "白天陆续更新，"
    blocks.append({"tag": "div", "text": {"tag": "lark_md",
                                          "content": f"{tail}[看网页版]({PAGE_URL})"}})

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
