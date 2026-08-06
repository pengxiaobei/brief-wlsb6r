# 每日简报

私人用途。网页：https://pengxiaobei.github.io/brief-wlsb6r/

## 文件各管什么

| 文件 | 谁改 | 说明 |
|---|---|---|
| `template.html` | **没人自动改** | 页面外壳 + 全部 CSS。排版已在真机验证过，别动 |
| `today.json` | 日更任务 | 当天 5 条的结构化内容 |
| `watchlist.json` | 周更任务 | 观察名单状态，周更靠它做 diff |
| `weekly.json` | 周更任务 | 本周的变化日志 |
| `prompts/` | 手改 | 两个任务的提示词。改文风改这里，不用重建任务 |
| `index.html` | `build.py` 生成 | **不要手改**，改了下次会被覆盖 |
| `archive/` | `build.py` 生成 | 每天存一份 |

日更和周更改的是不同文件，不会互相覆盖。

## 改完怎么生效

```bash
python3 build.py
```

它把 `today.json` + `watchlist.json` + `weekly.json` 灌进 `template.html`，生成 `index.html` 和当天存档。
自动任务只写 JSON、不碰 HTML，所以改不坏排版；内容里的特殊字符会被转义，注入不了。

## today.json 长这样

```json
{
  "date": "2026年8月6日 星期四 · 上面 1 分钟，下面 5 分钟",
  "stamp": "2026-08-06",
  "note": "文末那行数据时间说明",
  "items": [
    {"kind": "talk", "title": "一句话标题", "body": "正文 2-4 句，不放链接"}
  ],
  "sources": [{"name": "来源名", "url": "https://..."}]
}
```

`kind` 只能是 `talk`（在聊）、`you`（影响你）、`tech`（科技）三选一。

## 内容规矩

- 日更正好 5 条，大白话，术语就地翻译，**正文不放链接**
- 禁新闻腔：据悉、值得关注、业内人士表示、引发热议
- 周更只报变化，**刚冒头排最前**，在降温排最后
- 不做严肃时政舆论

## 说明

`robots.txt` 和 `noindex` 挡着搜索引擎。仓库是公开的（GitHub Pages 私有站点需要企业版），
网址带随机后缀所以不容易被撞见，但**这不等于私密**。

## 怎么跑起来的

两个云端定时任务，都挂着这个仓库：

| 任务 | 时间 | 改哪些文件 |
|---|---|---|
| 日更 5 条 | 每天 07:00（北京） | `today.json` |
| 周更变化日志 | 每周一 09:00（北京） | `watchlist.json`、`weekly.json` |

任务的提示词很短，只说「读 `prompts/xxx.md` 并严格执行」。
**想调文风或选题标准，改 `prompts/` 里的文件就行，不用动任务配置。**

## ⚠ 会静默失效的地方

云端环境自带的 git 凭据是**只读**的，推不上去，所以两个任务的提示词里嵌了一个细粒度 PAT
（只能写这一个仓库的 Contents）。

**这个令牌有有效期，到期后简报会停止更新，而且不会有任何报错。**

本地有个 `notify-feishu.sh` 每天早上抓 `today.json` 推飞书提醒，
它会检查 `stamp` 是不是今天——不是就推一条红色警告。这是目前唯一的失效预警。

令牌过期后要做的：重新生成一个（Contents: Read and write，只勾这个仓库），
然后更新两个任务提示词里的令牌，以及 `~/.config/daily-brief/gh-token`。
