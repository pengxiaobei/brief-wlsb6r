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

全自动，跑在 GitHub Actions 上，不依赖任何本地机器。

| 工作流 | 时间 | 改哪些文件 |
|---|---|---|
| `.github/workflows/daily.yml` | 每天 07:00（北京） | `today.json` |
| `.github/workflows/weekly.yml` | 每周一 09:00（北京） | `watchlist.json`、`weekly.json` |

每次运行：跑 Claude 生成内容 → `build.py` 出页面 → 用内置 `GITHUB_TOKEN` 提交 → `notify.py` 发飞书。

**想调文风或选题标准，改 `prompts/` 里那两个文件就行**，不用动工作流。

想手动补跑：仓库 Actions 页面点 "Run workflow"，或者 `gh workflow run daily.yml`。

## 两个 secret

- `CLAUDE_CODE_OAUTH_TOKEN` —— `claude setup-token` 生成，走 Max 订阅，不额外计费
- `FEISHU_WEBHOOK` —— 群机器人地址。**卡片标题必须含「简报」二字**，群里配了关键词校验

## 停更了怎么办

`notify.py` 每次都会检查 `today.json` 的日期是不是今天，不是就发**红色告警卡片**——
所以停更不会静默，飞书里能看到。

收到告警后去仓库 Actions 页面看最近一次运行挂在哪一步。最可能的原因是订阅令牌过期，
重新跑一次 `claude setup-token` 换掉那个 secret 即可。
