# fengzhua-xiaohongshu

基于 Playwright 浏览器自动化的小红书数据采集工具。通过真实浏览器渲染页面绕过反爬机制，支持关键词搜索、用户主页采集、笔记详情采集。

## 功能

- **关键词搜索** — 按关键词搜索小红书笔记，采集标题、作者、点赞数等
- **用户主页采集** — 批量采集指定用户发布的笔记列表
- **笔记详情** — 深度采集单条笔记：正文、图片、视频、标签、互动数据
- **多格式导出** — 自动导出 JSON / CSV / Markdown 三种格式

## 快速开始

### 1. 安装依赖

```bash
pip install -r scripts/requirements.txt
playwright install chromium
```

### 2. 首次登录（扫码，保存 Cookie）

```bash
python scripts/xhs_scraper.py init
```

会弹出浏览器窗口，用手机小红书扫码登录。登录成功后 Cookie 自动保存，后续 7-30 天无需重复登录。

### 3. 开始采集

```bash
# 关键词搜索
python scripts/xhs_scraper.py search --keyword "咖啡店运营" --max 20

# 搜索 + 采集详情（正文/图片/标签）
python scripts/xhs_scraper.py search --keyword "咖啡店运营" --max 10 --detail

# 采集用户主页笔记
python scripts/xhs_scraper.py user --user-id "5ff3e6410000000001008400" --max 20

# 采集单条笔记详情
python scripts/xhs_scraper.py detail --note-id "6682a7b3000000001e00c8b1"
```

### 4. 检查会话状态

```bash
python scripts/xhs_scraper.py check
```

## 如何获取 ID

| 类型 | 获取方式 |
|------|----------|
| 笔记 ID | 打开笔记 → 浏览器地址栏 `xiaohongshu.com/explore/` 后面的字符串 |
| 用户 ID | 打开用户主页 → `xiaohongshu.com/user/profile/` 后面的字符串 |

## 数据输出

采集结果保存到 `~/.xhs_scraper/data/` 目录：

| 格式 | 用途 |
|------|------|
| JSON | 完整结构化数据，程序化处理 |
| CSV | Excel / Google Sheets 打开，表格分析 |
| Markdown | 人类可读，含标题/作者/互动数据 |

### 采集字段

```
note_id, note_url, title, desc, author, author_id,
images[], video_url, likes, comments, collects, shares,
tags[], publish_time, scrape_time
```

## 反爬策略

| 反爬机制 | 应对方式 |
|----------|----------|
| 登录验证 | 手动扫码登录 + Cookie 持久化 |
| 浏览器指纹检测 | 注入脚本隐藏 webdriver 标识 |
| 请求签名 (X-s/X-t) | 不走 API，浏览器渲染页面后提取 DOM |
| 频率限制 | 随机延迟 1.5-3.5s + 模拟人类滚动 |

详细分析见 [references/anti_crawler.md](references/anti_crawler.md)

## 采集频率建议

| 场景 | 建议频率 | 单次量级 |
|------|----------|----------|
| 关键词搜索 | 每小时不超过 5 次 | ≤ 20 条/次 |
| 用户主页采集 | 每天不超过 10 个用户 | ≤ 20 条/用户 |
| 笔记详情 | 每分钟不超过 10 条 | - |

## 目录结构

```
fengzhua-xiaohongshu/
├── scripts/
│   ├── xhs_scraper.py      # 主采集脚本
│   └── requirements.txt     # Python 依赖
├── references/
│   ├── xhs_selectors.md     # 页面选择器参考
│   └── anti_crawler.md      # 反爬策略分析
├── SKILL.md                 # WorkBuddy Skill 定义文件
├── .gitignore
└── README.md
```

## 作为 WorkBuddy Skill 使用

如果你使用 [WorkBuddy](https://www.codebuddy.cn)，可以将此仓库直接作为 Skill 使用：

1. 将仓库克隆到 `~/.workbuddy/skills/` 目录下
2. 在 WorkBuddy 对话中直接说"帮我搜索小红书上关于XXX的内容"
3. WorkBuddy 会自动加载 SKILL.md 并执行采集

## 合规提示

本工具仅供个人研究分析使用。采集的数据应用于市场调研、竞品分析等合法用途，不得批量搬运他人原创内容。尊重原作者版权，遵守平台服务条款。

## License

MIT
