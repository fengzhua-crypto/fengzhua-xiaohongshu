---
name: xhs-scraper
description: "小红书数据采集工具。当用户需要搜索小红书笔记、采集用户主页内容、获取笔记详情（标题、正文、点赞、评论、收藏、图片、标签等）时使用此技能。支持关键词搜索、用户主页采集、单条笔记详情采集，结果可导出为 JSON/CSV/Markdown。触发词：小红书采集、爬小红书、小红书搜索、采集笔记、xhs爬虫、小红书数据。"
---

# xhs-scraper — 小红书数据采集

## 概述

基于 Playwright 浏览器自动化的小红书数据采集工具。通过真实浏览器渲染页面绕过反爬机制，支持关键词搜索、用户主页采集、笔记详情采集，数据导出为 JSON / CSV / Markdown 三种格式。

## 前置条件

### 环境准备

首次使用前，必须完成环境安装：

1. **安装 Playwright Python 包**：
   ```bash
   pip install playwright
   ```

2. **安装浏览器内核**：
   ```bash
   playwright install chromium
   ```

如果环境中没有 pip，使用 WorkBuddy 管理的 Python 环境：
```bash
# 使用 managed python 创建 venv
"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m venv "C:\Users\Administrator\.workbuddy\binaries\python\envs\default"
# 安装依赖
"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\pip" install playwright
# 安装浏览器
"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\playwright" install chromium
```

### 首次登录

采集前必须先登录小红书（保存 Cookie），否则无法获取数据：

```bash
python scripts/xhs_scraper.py init
```

此命令会打开一个浏览器窗口，手动扫码登录小红书。登录成功后 Cookie 会自动保存到 `~/.xhs_scraper/storage_state.json`，后续采集无需重复登录。

Cookie 有效期约 7-30 天，过期后重新执行 `init` 即可。

## 使用方式

### 1. 检查会话状态

```bash
python scripts/xhs_scraper.py check
```

输出 JSON 告知会话是否有效。

### 2. 关键词搜索

```bash
# 基础搜索（返回笔记列表：标题、作者、点赞数等）
python scripts/xhs_scraper.py search --keyword "咖啡店运营" --max 20

# 搜索 + 同时采集详情（返回完整内容：正文、图片、标签等）
python scripts/xhs_scraper.py search --keyword "咖啡店运营" --max 10 --detail
```

### 3. 用户主页采集

```bash
# 采集指定用户发布的笔记列表
python scripts/xhs_scraper.py user --user-id "5ff3e6410000000001008400" --max 20

# 采集 + 同时获取详情
python scripts/xhs_scraper.py user --user-id "5ff3e6410000000001008400" --max 10 --detail
```

用户 ID 可从小红书用户主页 URL 获取：`https://www.xiaohongshu.com/user/profile/{用户ID}`

### 4. 单条笔记详情

```bash
python scripts/xhs_scraper.py detail --note-id "6682a7b3000000001e00c8b1"
```

笔记 ID 可从笔记 URL 获取：`https://www.xiaohongshu.com/explore/{笔记ID}`

## 输出说明

所有采集结果输出到 `~/.xhs_scraper/data/` 目录，同时 stdout 输出 JSON 供程序化处理。

### JSON 输出结构

```json
{
  "status": "ok",
  "count": 20,
  "keyword": "咖啡店运营",
  "files": {
    "json": "~/.xhs_scraper/data/search_xxx_20240702_100000.json",
    "csv": "~/.xhs_scraper/data/search_xxx_20240702_100000.csv",
    "md": "~/.xhs_scraper/data/search_xxx_20240702_100000.md"
  },
  "data": [
    {
      "note_id": "6682a7b3000000001e00c8b1",
      "note_url": "https://www.xiaohongshu.com/explore/6682a7b3000000001e00c8b1",
      "title": "咖啡店如何做小红书运营",
      "desc": "分享3年咖啡店小红书运营经验...",
      "author": "咖啡店主理人小王",
      "author_id": "5ff3e6410000000001008400",
      "images": ["https://sns-img-bd.xhscdn.com/xxx"],
      "likes": 1200,
      "comments": 85,
      "collects": 532,
      "shares": 23,
      "tags": ["咖啡店", "小红书运营", "实体店"],
      "publish_time": "2024-06-15",
      "scrape_time": "2024-07-02T10:00:00"
    }
  ]
}
```

### 文件格式说明

| 格式 | 用途 | 说明 |
|------|------|------|
| JSON | 程序化处理 | 完整结构化数据，保留所有字段 |
| CSV | 表格分析 | 扁平化关键字段，可用 Excel/Google Sheets 打开 |
| Markdown | 阅读浏览 | 人类可读格式，含标题、作者、互动数据 |

## 工作流程

当用户请求采集小红书数据时，按以下步骤操作：

1. **检查环境**：确认 Playwright 已安装。如未安装，按「前置条件」中的步骤安装。
2. **检查会话**：运行 `check` 命令确认 Cookie 有效。如无效或无会话，提示用户运行 `init` 登录。
3. **执行采集**：根据用户需求选择 `search` / `user` / `detail` 命令。
4. **读取结果**：从 stdout 的 JSON 中提取 `data` 字段和 `files` 字段。
5. **分析呈现**：将采集结果整理为用户需要的分析报告、表格或其他格式。

## 采集注意事项

1. **控制频率**：单次搜索间隔不少于 10 分钟，单次采集量建议不超过 50 条。
2. **会话过期**：如输出 `{"status": "expired"}`，提示用户重新执行 `init`。
3. **选择器失效**：如采集结果为空但关键词有效，可能是小红书前端更新了 DOM 结构，需参考 `references/xhs_selectors.md` 更新选择器。
4. **验证码**：如遇验证码，headless 模式下无法处理，建议改用 `init` 模式手动操作。

## 参考文档

- `references/xhs_selectors.md` — 页面结构与 CSS 选择器参考（选择器失效时查阅）
- `references/anti_crawler.md` — 反爬机制分析与应对策略

## 合规提示

本工具仅供个人研究分析使用。采集的数据应用于市场调研、竞品分析等合法用途，不得批量搬运他人原创内容。尊重原作者版权，遵守平台服务条款。
