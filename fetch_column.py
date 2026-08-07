#!/usr/bin/env python3
"""把「猫笔刀」最新那篇公众号文章抓下来，落成纯文本给日更任务读。

为什么单独一个脚本、不让 Claude 自己去 WebFetch：
  - 微信原文（mp.weixin.qq.com）对非微信环境有验证墙，直接读会拿到「环境异常」
  - WebFetch 会先把页面压成 markdown 再让小模型转述，对着一个 170KB 的 XML 不可靠
  这里用 urllib 直接拿 RSS、按标签取全文，抓取是确定性的，模型只负责总结。

源是 wechat2rss 的公开实例（https://wechat2rss.xlab.app/list/ 里的「猫笔刀」）。
公众号本身每晚 22:20 前后发一篇，feed 平均 6 小时延迟，所以早上 07:00 那轮取到的
永远是「昨晚那篇」。

**它是免费的第三方服务，随时可能挂。** 所以这个脚本任何情况下都不让工作流失败：
抓不到就打印原因、不写文件、退出码 0，当天简报少这一块而已，其余照常。

用法：
    python3 fetch_column.py          # 写 column_raw.txt（抓不到就不写）
"""

import datetime
import html
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEED = "https://wechat2rss.xlab.app/feed/33d986064f59be5263de2ca822fb3e0bdd59eb81.xml"
WHO = "猫笔刀"
OUT = pathlib.Path(__file__).parent / "column_raw.txt"

# 超过这个钟点数就当他这两天没更新，宁可不放也不要把前天的当「昨晚」端上来。
# 他 22:20 发，07:00 那轮取到时约 9 小时；隔了一天没发的话会是 32 小时以上。
MAX_AGE_HOURS = 30

CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


def strip_html(raw):
    """去标签、还原实体、把空白压平。RSS 里的正文是一整坨 HTML。"""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.S | re.I)
    text = re.sub(r"<(br|/p|/div)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def main():
    try:
        req = urllib.request.Request(FEED, headers={"User-Agent": "daily-brief/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            xml = resp.read()
    except Exception as e:
        print(f"· 拉 {WHO} 的 feed 失败：{e}")
        print("· 今天这一块跳过，不影响其余内容")
        return

    try:
        items = ET.fromstring(xml).find("channel").findall("item")
    except Exception as e:
        print(f"· feed 解析失败：{e}")
        return
    if not items:
        print("· feed 里一条都没有，跳过")
        return

    it = items[0]
    title = (it.findtext("title") or "").strip()

    # pubDate 形如 "Thu, 06 Aug 2026 22:24:00 +0800"
    try:
        pub = datetime.datetime.strptime(it.findtext("pubDate").strip(),
                                         "%a, %d %b %Y %H:%M:%S %z")
    except Exception as e:
        print(f"· pubDate 解析失败（{it.findtext('pubDate')!r}）：{e}")
        return

    age = (datetime.datetime.now(datetime.timezone.utc) - pub).total_seconds() / 3600
    if age > MAX_AGE_HOURS:
        print(f"· 最新一篇《{title}》是 {pub:%Y-%m-%d %H:%M}，已经 {age:.0f} 小时前了")
        print(f"· 超过 {MAX_AGE_HOURS} 小时就不当「昨晚那篇」用，跳过")
        return

    node = it.find("content:encoded", CONTENT_NS)
    body = strip_html(node.text or "") if node is not None else ""
    if len(body) < 200:
        print(f"· 《{title}》正文只有 {len(body)} 字，大概率没取全，跳过")
        return

    # 开头那行「原创 moomoocat 2026-08-06 22:24 新加坡」是 RSS 加的页眉，不是正文
    body = re.sub(r"^原创\s+\S+\s+[\d-]+\s+[\d:]+\s*\S*\s*、?\s*", "", body)

    OUT.write_text(
        f"公众号：{WHO}\n"
        f"标题：{title}\n"
        f"发布时间：{pub:%Y-%m-%d %H:%M}\n"
        f"链接：{it.findtext('link') or ''}\n"
        f"---- 正文 ----\n{body}\n",
        encoding="utf-8",
    )
    print(f"✓ {WHO}《{title}》{pub:%m-%d %H:%M}，正文 {len(body)} 字 → {OUT.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 兜底：这一块再怎么样也不能拖垮整个日更
        print(f"· 抓 {WHO} 时出了意外：{e}", file=sys.stderr)
