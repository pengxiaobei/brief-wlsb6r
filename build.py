#!/usr/bin/env python3
"""把 today.json + weekly.html 灌进 template.html，生成 index.html 和当天存档。

设计意图：让自动任务只写结构化的 today.json，不直接改 HTML。
排版和 CSS 全在 template.html 里，任务碰不到，也就改不坏。

用法：python3 build.py
"""

import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
KINDS = {"talk": "在聊", "you": "影响你", "tech": "科技"}


def esc(s):
    """转义 HTML 特殊字符，防止内容里的 < & 把页面搞坏。"""
    return html.escape(str(s), quote=False)


TOP_N = 5  # 前 N 条推飞书；网页给全部，在这里插一条分界


def build_today(items):
    if not items:
        return '    <p class="sub">今天没生成内容。</p>'
    out = ['    <ol class="today">']
    for n, it in enumerate(items):
        kind = it.get("kind", "talk")
        if kind not in KINDS:
            sys.exit(f"kind 只能是 talk/you/tech，收到：{kind!r}")
        if n:
            out.append("")  # 条与条之间留空行，跟手写版保持一致
        # 前 TOP_N 条已经推过飞书了，后面的单独分一段
        if n == TOP_N and len(items) > TOP_N:
            out += ['      <li class="divider">',
                    "        <span>下面是次要的，有空再看</span>",
                    "      </li>",
                    ""]
        out += [
            "      <li>",
            f'        <span class="label {kind}">{KINDS[kind]}</span>',
            f'        <h3>{esc(it["title"])}</h3>',
            f'        <p>{esc(it["body"])}</p>',
            "      </li>",
        ]
    out.append("    </ol>")
    return "\n".join(out)


STAGES = ["刚冒头", "正在起飞", "已经很热", "在降温"]
# 阶段配色：早期用 up，热的用 hot，凉的用 cold
STAGE_TONE = {"刚冒头": "up", "正在起飞": "up", "已经很热": "hot", "在降温": "cold"}
CHANGE_MARK = {"up": "⬆", "down": "⬇", "new": "🆕", "out": "❌"}


def stage_bar(stage):
    cells = "".join(
        f'<i class="on">{s}</i>' if s == stage else f"<i>{s}</i>" for s in STAGES
    )
    return f'        <div class="stage {STAGE_TONE.get(stage, "up")}">\n          {cells}\n        </div>'


def build_weekly(watchlist, weekly):
    """「本周」那一段：先讲这周的变化，再给一张全景板。

    刚冒头排最前，在降温排最后 —— 早期的对读者最有价值。
    """
    out = ['    <div class="trends">']
    changes = weekly.get("changes", [])

    if changes:
        order = {"new": 0, "up": 1, "down": 2, "out": 3}
        for c in sorted(changes, key=lambda x: order.get(x.get("type"), 9)):
            mark = CHANGE_MARK.get(c.get("type"), "·")
            if c.get("type") == "new":
                head = f'{mark} 新进名单：{esc(c["name"])}'
            elif c.get("type") == "out":
                head = f'{mark} 移出名单：{esc(c["name"])}'
            else:
                head = f'{mark} {esc(c["name"])}：{esc(c.get("from", ""))} → {esc(c.get("to", ""))}'
            out += ['', '      <article class="trend">', f"        <h3>{head}</h3>"]
            if c.get("to"):
                out.append(stage_bar(c["to"]))
            out += [
                '        <div class="verdict">',
                f'          <p>{esc(c.get("why", ""))}</p>',
                "        </div>",
                "      </article>",
            ]
    else:
        n = len(watchlist.get("items", []))
        out += [
            "",
            '      <article class="trend">',
            "        <h3>这周没动静</h3>",
            '        <div class="verdict">',
            f"          <p>名单上 {n} 项全部维持原状，没有换阶段的，也没有新冒出来的。</p>",
            "        </div>",
            "      </article>",
        ]

    # 全景板：按阶段分组，让读者随时看得到整个名单
    items = watchlist.get("items", [])
    if items:
        out += ["", '      <article class="trend">', "        <h3>名单全景</h3>", '        <ul class="facts">']
        for st in STAGES:
            names = [esc(i["name"]) for i in items if i.get("stage") == st]
            if names:
                out.append(f"          <li><b>{st}</b>　{'、'.join(names)}</li>")
        out += ["        </ul>", "      </article>"]

    out.append("    </div>")
    return "\n".join(out)


def build_sources(sources):
    if not sources:
        return ""
    out = ['    <ul class="src">']
    for s in sources:
        out.append(f'      <li><a href="{esc(s["url"])}">{esc(s["name"])}</a></li>')
    out.append("    </ul>")
    return "\n".join(out)


def main():
    for f in ("template.html", "today.json"):
        if not (ROOT / f).exists():
            sys.exit(f"缺少 {f}")

    template = (ROOT / "template.html").read_text(encoding="utf-8")
    today = json.loads((ROOT / "today.json").read_text(encoding="utf-8"))

    # 「本周」那段由 watchlist.json + weekly.json 生成，周更任务只写这两个 JSON。
    # 缺文件时退回已有的 weekly.html，保证日更不会因为周更没跑过就崩。
    wl_path, wk_path = ROOT / "watchlist.json", ROOT / "weekly.json"
    if wl_path.exists() and wk_path.exists():
        weekly = build_weekly(
            json.loads(wl_path.read_text(encoding="utf-8")),
            json.loads(wk_path.read_text(encoding="utf-8")),
        )
    else:
        legacy = ROOT / "weekly.html"
        weekly = legacy.read_text(encoding="utf-8").rstrip("\n") if legacy.exists() else ""

    page = template
    page = page.replace("<!--DATE-->", esc(today.get("date", "")))
    page = page.replace("    <!--TODAY-->", build_today(today.get("items", [])))
    page = page.replace("    <!--WEEKLY-->", weekly)
    page = page.replace("<!--NOTE-->", esc(today.get("note", "")))
    page = page.replace("    <!--SOURCES-->", build_sources(today.get("sources", [])))

    left = [p for p in ("<!--DATE-->", "<!--TODAY-->", "<!--WEEKLY-->", "<!--NOTE-->", "<!--SOURCES-->") if p in page]
    if left:
        sys.exit(f"还有占位符没填：{left}")

    (ROOT / "index.html").write_text(page, encoding="utf-8")

    stamp = today.get("stamp")
    if stamp:
        arch = ROOT / "archive"
        arch.mkdir(exist_ok=True)
        (arch / f"{stamp}.html").write_text(page, encoding="utf-8")

    print(f"✓ index.html 已生成（{len(today.get('items', []))} 条，{len(page)} 字节）")
    if stamp:
        print(f"✓ 存档 archive/{stamp}.html")


if __name__ == "__main__":
    main()
