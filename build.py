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
        out += [
            "      <li>",
            f'        <span class="label {kind}">{KINDS[kind]}</span>',
            f'        <h3>{esc(it["title"])}</h3>',
            f'        <p>{esc(it["body"])}</p>',
            "      </li>",
        ]
    out.append("    </ol>")
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

    # weekly.html 由周更任务维护；还没有就先留空，不影响日更
    wk_path = ROOT / "weekly.html"
    weekly = wk_path.read_text(encoding="utf-8").rstrip("\n") if wk_path.exists() else ""

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
