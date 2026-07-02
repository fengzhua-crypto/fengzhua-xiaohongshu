# 小红书页面结构与选择器参考

> 本文档记录小红书 Web 版（www.xiaohongshu.com）的页面 URL 格式和 CSS 选择器。
> 小红书前端会不定期更新，选择器可能失效。如果采集结果为空，优先检查选择器是否需要更新。

## URL 格式

| 页面 | URL 模板 |
|------|----------|
| 首页 | `https://www.xiaohongshu.com` |
| 搜索结果 | `https://www.xiaohongshu.com/search_result?keyword={关键词}&source=web_search_result_notes` |
| 笔记详情 | `https://www.xiaohongshu.com/explore/{笔记ID}` |
| 用户主页 | `https://www.xiaohongshu.com/user/profile/{用户ID}` |
| 话题页 | `https://www.xiaohongshu.com/page/topics/{话题ID}` |

### ID 格式
- 笔记ID：24位十六进制字符串（如 `6682a7b3000000001e00c8b1`）
- 用户ID：24位十六进制字符串（如 `5ff3e6410000000001008400`）

## 搜索结果页选择器

### 笔记卡片容器
```
section.note-item
div.note-item
[class*="note-item"]
```

### 卡片内字段
| 字段 | 选择器（按优先级排列） |
|------|----------------------|
| 标题 | `.title` / `.footer .title` / `.note-title` |
| 作者名 | `.author .name` / `.author-wrapper .name` / `.user .name` |
| 作者主页链接 | `.author a` / `.author-wrapper a` |
| 点赞数 | `.like-wrapper .count` / `.like .count` / `[class*="like"] .count` |
| 封面图 | `img` |
| 笔记链接 | `a[href*="/explore/"]` / `a[href*="/search_result/"]` |

## 笔记详情页选择器

| 字段 | 选择器（按优先级排列） |
|------|----------------------|
| 标题 | `#detail-title` / `.note-content .title` / `[class*="note-title"]` |
| 正文 | `#detail-desc` / `.note-content .desc` / `[class*="desc"]` |
| 作者名 | `.author-wrapper .name` / `.author .name` |
| 作者链接 | `.author-wrapper a` / `.author a` |
| 点赞数 | `.like-wrapper .count` / `[class*="like"] .count` |
| 评论数 | `.chat-wrapper .count` / `[class*="chat"] .count` |
| 收藏数 | `.collect-wrapper .count` / `[class*="collect"] .count` |
| 分享数 | `.share-wrapper .count` / `[class*="share"] .count` |
| 图片 | `.swiper-slide img` / `.media-container img` |
| 视频 | `video` |
| 标签 | `.note-content .tag` / `[class*="tag"] a` / `#detail-desc a` |
| 发布时间 | `.date` / `[class*="date"]` / `time` |

## 用户主页选择器

| 字段 | 选择器（按优先级排列） |
|------|----------------------|
| 用户名 | `.user-info .name` / `.info .name` |
| 简介 | `.user-info .desc` / `.info .desc` |
| 关注数 | `.user-interactions .follows` / `[class*="follow"]` |
| 粉丝数 | `.user-interactions .fans` / `[class*="fans"]` |
| 笔记卡片 | `section.note-item` / `a.note-item` / `[class*="note-item"]` |

## 选择器更新指南

当采集结果为空时，按以下步骤排查：

1. **打开浏览器开发者工具**（F12），手动访问对应页面
2. **检查 DOM 结构**：右键点击目标元素 → 检查，查看实际 class 名
3. **更新选择器**：在 `xhs_scraper.py` 中对应函数的 `eval_on_selector_all` 或 `evaluate` 中更新选择器
4. **使用通配选择器**：如果 class 名包含哈希值（如 `note-item-abc123`），使用 `[class*="note-item"]` 通配匹配
5. **测试**：运行 `python xhs_scraper.py search --keyword "测试" --max 5` 验证

## 数据提取技巧

### 数量解析
小红书显示的数量格式可能为：
- 纯数字：`532`
- 万级：`1.2万`
- 亿级：`3.5亿`

`parse_count()` 函数已处理这些格式。

### 标签提取
标签可能出现在：
1. 正文中的 `#标签名#` 格式
2. 独立的标签元素 `.tag`
3. 链接形式 `a[href*="topic"]`

建议同时用正则和 DOM 查询提取，取并集去重。

### 图片 URL
小红书图片 URL 格式通常为：
```
https://sns-img-bd.xhscdn.com/{hash}
https://ci.xiaohongshu.com/{hash}
```
可直接访问，无需额外鉴权。
