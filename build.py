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


def group_by_round(items):
    """按 at（哪一轮进来的）把 items 切成连续的几段。

    增量轮是把整批新条目插到最前面的，所以同一轮的条目天然相邻——
    按相邻分组就够，不用排序，那会打乱轮内的重要性顺序。

    老数据没有 at 字段时全部落进同一段，页面就跟改动前一模一样。
    """
    groups = []
    for it in items:
        at = it.get("at")
        if groups and groups[-1][0] == at:
            groups[-1][1].append(it)
        else:
            groups.append([at, [it]])
    return groups


def build_item(it):
    kind = it.get("kind", "talk")
    if kind not in KINDS:
        sys.exit(f"kind 只能是 talk/you/tech，收到：{kind!r}")
    out = [
        "      <li>",
        f'        <span class="label {kind}">{KINDS[kind]}</span>',
        f'        <h3>{esc(it["title"])}</h3>',
        f'        <p>{esc(it["body"])}</p>',
    ]
    # 后面几轮跑出来的新进展：原文不动，变化挂在下面，读者不用整条重读
    for u in it.get("updates", []):
        at = u.get("at", "")
        out += [
            '        <div class="update">',
            f'          <span>{esc(at)} 更新</span>' if at else '          <span>更新</span>',
            f'          <p>{esc(u.get("text", ""))}</p>',
            "        </div>",
        ]
    out.append("      </li>")
    return out


def build_today(items):
    if not items:
        return '    <p class="sub">今天没生成内容。</p>'

    groups = group_by_round(items)
    blocks = []  # 每个元素是一段 HTML 行；最后统一用空行隔开，跟手写版保持一致
    for gi, (at, group) in enumerate(groups):
        if gi:
            # 上一轮和这一轮之间画条线，读者一眼看出往下是早先看过的
            blocks.append(['      <li class="divider">',
                           f'        <span>{esc(at)} 发的</span>' if at else "        <span>更早</span>",
                           "      </li>"])
        elif len(groups) > 1 and at:
            # 只有一轮时不出现任何分段标记 —— 首轮当天的页面跟改动前完全一致
            blocks.append(['      <li class="newmark">',
                           f'        <span>{esc(at)} 新增</span>',
                           "      </li>"])
        for it in group:
            blocks.append(build_item(it))

    out = ['    <ol class="today">']
    for n, b in enumerate(blocks):
        if n:
            out.append("")
        out += b
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


def build_column(col):
    """「猫笔刀昨晚说了什么」那一段。

    没抓到（他没更新、或者 wechat2rss 挂了）时返回空串 —— 整块从页面上消失，
    而不是留个空标题。这是别人的观点，不是简报自己的内容，缺了就该干净地缺掉。
    """
    if not col or not col.get("points"):
        return ""

    who = esc(col.get("who", ""))

    # 模型很容易在这里写超 —— 提示词说的是每条最多两句、60 字。
    # 不拦（拦了整轮就废了），但要在 CI 日志里留个声，长期超标才看得见。
    long = [p for p in col["points"] if len(p) > 90]
    if long:
        print(f"· 提醒：{who or '专栏'}那块有 {len(long)}/{len(col['points'])} 条超过 90 字，"
              f"最长 {max(len(p) for p in long)} 字 —— 碎片时间读着会累")

    head = [
        '  <section class="part">',
        f"    <h2>{who}昨晚说了什么</h2>",
    ]
    meta = " · ".join(p for p in (
        f'《{esc(col["title"])}》' if col.get("title") else "",
        esc(col.get("when", "")),
    ) if p)
    if meta:
        head.append(f'    <p class="sub">{meta}</p>')
    head += ["", '    <ul class="facts column">']
    head += [f"      <li>{esc(p)}</li>" for p in col["points"]]
    head += ["    </ul>", "  </section>"]
    return "\n".join(head)


def build_updated(today):
    """报头第二行：更新到哪一轮了、今天一共几条。

    一天跑三轮，读者打开第一眼想知道的就是「跟上次比有没有新的」。
    """
    runs = today.get("runs", [])
    parts = []
    if runs:
        parts.append(f"最后更新 {esc(runs[-1])}")
    if today.get("items"):
        parts.append(f"共 {len(today['items'])} 条")
    return " · ".join(parts)


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

    # 页面靠这个串判断自己旧没旧：stamp 换了是新的一天，runs 变长是当天又跑了一轮
    built = f"{today.get('stamp', '')}/{len(today.get('runs', []))}"

    page = template
    page = page.replace("<!--DATE-->", esc(today.get("date", "")))
    page = page.replace("<!--UPDATED-->", build_updated(today))
    page = page.replace("    <!--TODAY-->", build_today(today.get("items", [])))
    page = page.replace("  <!--COLUMN-->", build_column(today.get("column")))
    page = page.replace("    <!--WEEKLY-->", weekly)
    page = page.replace("<!--NOTE-->", esc(today.get("note", "")))
    page = page.replace("    <!--SOURCES-->", build_sources(today.get("sources", [])))
    # 用 json.dumps 而不是 esc：这里落在 JS 字符串字面量的位置，得连引号一起给，
    # 顺便把内容里万一出现的引号转义掉，免得整段脚本被搞坏。
    page = page.replace("<!--BUILT-->", json.dumps(built))

    left = [p for p in ("<!--DATE-->", "<!--UPDATED-->", "<!--TODAY-->", "<!--COLUMN-->",
                        "<!--WEEKLY-->", "<!--NOTE-->", "<!--SOURCES-->", "<!--BUILT-->") if p in page]
    if left:
        sys.exit(f"还有占位符没填：{left}")

    (ROOT / "index.html").write_text(page, encoding="utf-8")

    stamp = today.get("stamp")
    if stamp:
        arch = ROOT / "archive"
        arch.mkdir(exist_ok=True)
        (arch / f"{stamp}.html").write_text(page, encoding="utf-8")

    runs = today.get("runs", [])
    updates = sum(len(i.get("updates", [])) for i in today.get("items", []))
    print(f"✓ index.html 已生成（{len(today.get('items', []))} 条"
          f"，{updates} 条新进展，跑过 {'/'.join(runs) or '—'}，{len(page)} 字节）")
    if stamp:
        print(f"✓ 存档 archive/{stamp}.html")


if __name__ == "__main__":
    main()
