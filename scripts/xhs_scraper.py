#!/usr/bin/env python3
"""
xhs_scraper.py - 小红书数据采集工具
基于 Playwright 浏览器自动化，通过真实浏览器绕过反爬。

使用方式:
  python xhs_scraper.py init                          # 首次登录（手动扫码，保存cookie）
  python xhs_scraper.py check                         # 检查会话状态
  python xhs_scraper.py search --keyword "关键词"      # 关键词搜索笔记
  python xhs_scraper.py user --user-id "用户ID"        # 采集用户主页笔记
  python xhs_scraper.py detail --note-id "笔记ID"      # 采集笔记详情
"""

import argparse
import asyncio
import csv
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

SESSION_DIR = Path.home() / ".xhs_scraper"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

COOKIE_FILE = SESSION_DIR / "cookies.json"
STORAGE_FILE = SESSION_DIR / "storage_state.json"
DATA_DIR = SESSION_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.xiaohongshu.com"
SEARCH_URL = f"{BASE_URL}/search_result?keyword={{}}&source=web_search_result_notes"
NOTE_URL = f"{BASE_URL}/explore/{{}}"
USER_URL = f"{BASE_URL}/user/profile/{{}}"

# 真实浏览器 UA
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def log(msg: str):
    """输出日志到 stderr，不影响 stdout 的 JSON 输出"""
    print(f"[xhs] {msg}", file=sys.stderr, flush=True)

def random_delay(min_s=1.5, max_s=3.5):
    """人类操作间隔"""
    time.sleep(random.uniform(min_s, max_s))

def save_data(items: list, mode: str, keyword: str = ""):
    """保存采集结果到本地文件，返回文件路径"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_part = keyword or mode
    name_part = re.sub(r'[^\w\u4e00-\u9fff]', '_', name_part)[:30]

    json_path = DATA_DIR / f"{mode}_{name_part}_{ts}.json"
    csv_path = DATA_DIR / f"{mode}_{name_part}_{ts}.csv"
    md_path = DATA_DIR / f"{mode}_{name_part}_{ts}.md"

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # CSV（扁平化关键字段）
    if items:
        flat_keys = [
            "note_id", "title", "author", "author_id",
            "likes", "comments", "collects", "shares",
            "tags", "publish_time", "note_url",
        ]
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=flat_keys, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                row = {**item}
                if isinstance(row.get("tags"), list):
                    row["tags"] = ",".join(row["tags"])
                if isinstance(row.get("images"), list):
                    row["images"] = row["images"][0] if row["images"] else ""
                writer.writerow(row)

    # Markdown（可读格式）
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 小红书采集结果\n\n")
        f.write(f"- 采集模式: {mode}\n")
        if keyword:
            f.write(f"- 关键词: {keyword}\n")
        f.write(f"- 采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 笔记数量: {len(items)}\n\n---\n\n")
        for i, item in enumerate(items, 1):
            f.write(f"## {i}. {item.get('title', '无标题')}\n\n")
            f.write(f"- 作者: {item.get('author', '未知')}\n")
            f.write(f"- 点赞: {item.get('likes', '-')} | 评论: {item.get('comments', '-')} | 收藏: {item.get('collects', '-')}\n")
            if item.get("tags"):
                tags = item["tags"] if isinstance(item["tags"], list) else [item["tags"]]
                f.write(f"- 标签: {' '.join('#' + t for t in tags)}\n")
            f.write(f"- 链接: {item.get('note_url', '')}\n")
            if item.get("desc"):
                f.write(f"\n> {item['desc'][:200]}\n")
            f.write("\n---\n\n")

    return json_path, csv_path, md_path

def parse_count(text: str) -> int:
    """解析 '1.2万' '532' 等文本为整数"""
    if not text:
        return 0
    text = text.strip()
    try:
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        if "亿" in text:
            return int(float(text.replace("亿", "")) * 100000000)
        return int(text)
    except (ValueError, TypeError):
        return 0

# ---------------------------------------------------------------------------
# 核心采集器
# ---------------------------------------------------------------------------

class XhsScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """启动浏览器，加载已保存的会话"""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()

        launch_args = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        }

        self.browser = await self.playwright.chromium.launch(**launch_args)

        # 加载已保存的存储状态（cookies + localStorage）
        ctx_kwargs = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": USER_AGENT,
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
        }
        if STORAGE_FILE.exists():
            ctx_kwargs["storage_state"] = str(STORAGE_FILE)
            log("已加载保存的会话状态")

        self.context = await self.browser.new_context(**ctx_kwargs)

        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en'] });
            window.chrome = { runtime: {} };
        """)

        self.page = await self.context.new_page()
        return self

    async def close(self):
        if self.context:
            # 保存最新的会话状态
            await self.context.storage_state(path=str(STORAGE_FILE))
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def wait_for_login(self):
        """打开小红书首页，等待用户手动登录"""
        await self.page.goto(BASE_URL, wait_until="domcontentloaded")
        log("请在打开的浏览器中手动登录小红书（扫码或手机号）")
        log("登录成功后，页面右上角会显示你的头像")
        log("等待登录完成...")

        # 最多等 120 秒
        for _ in range(120):
            await asyncio.sleep(1)
            # 检查是否登录成功（页面有用户头像/侧边栏）
            content = await self.page.content()
            if "login" not in self.page.url and ("user-avatar" in content or "side-bar" in content or "user-info" in content):
                log("检测到登录成功！")
                break
        else:
            log("登录超时（120秒），尝试保存当前状态...")

        # 保存会话
        await self.context.storage_state(path=str(STORAGE_FILE))
        cookies = await self.context.cookies()
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        log(f"会话已保存到 {STORAGE_FILE}")

    async def check_login(self) -> bool:
        """检查当前会话是否有效"""
        await self.page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # 如果被重定向到登录页，说明会话已失效
        if "login" in self.page.url:
            return False

        # 检查页面是否包含登录态特征
        content = await self.page.content()
        if "请登录" in content or "扫码登录" in content:
            return False

        return True

    async def human_scroll(self, times: int = 3, min_wait: float = 1.0, max_wait: float = 2.5):
        """模拟人类滚动浏览"""
        for _ in range(times):
            await self.page.mouse.wheel(0, random.randint(400, 800))
            await asyncio.sleep(random.uniform(min_wait, max_wait))

    async def extract_note_links(self) -> list:
        """从当前页面提取笔记链接"""
        links = await self.page.eval_on_selector_all(
            'a[href*="/explore/"], a[href*="/search_result/"]',
            '''els => els.map(el => ({
                href: el.href,
                text: el.textContent?.trim() || ""
            }))'''
        )
        # 过滤出笔记链接
        note_links = []
        seen = set()
        for link in links:
            href = link.get("href", "")
            # 提取笔记ID
            match = re.search(r'/(?:explore|search_result)/([a-f0-9]{24})', href)
            if match:
                note_id = match.group(1)
                if note_id not in seen:
                    seen.add(note_id)
                    note_links.append({
                        "note_id": note_id,
                        "note_url": f"{BASE_URL}/explore/{note_id}",
                    })
        return note_links

    async def search(self, keyword: str, max_results: int = 20) -> list:
        """关键词搜索笔记"""
        url = SEARCH_URL.format(keyword)
        log(f"搜索: {keyword}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 模拟人类滚动加载更多
        results = []
        scroll_count = 0
        max_scrolls = (max_results // 10) + 3

        while len(results) < max_results and scroll_count < max_scrolls:
            await self.human_scroll(times=2)
            await asyncio.sleep(1)

            # 提取笔记卡片信息
            cards = await self.page.eval_on_selector_all(
                'section.note-item, div.note-item, [class*="note-item"]',
                '''els => els.map(el => {
                    const getText = (sel) => el.querySelector(sel)?.textContent?.trim() || "";
                    const getHref = (sel) => el.querySelector(sel)?.href || "";
                    const link = el.querySelector('a[href*="/explore/"], a[href*="/search_result/"]');
                    return {
                        title: getText('.title, .footer .title, .note-title'),
                        author: getText('.author .name, .author-wrapper .name, .user .name'),
                        author_href: getHref('.author a, .author-wrapper a'),
                        likes: getText('.like-wrapper .count, .like .count, [class*="like"] .count'),
                        cover: el.querySelector('img')?.src || "",
                        note_href: link?.href || "",
                    };
                })'''
            )

            for card in cards:
                href = card.get("note_href", "")
                match = re.search(r'/(?:explore|search_result)/([a-f0-9]{24})', href)
                if not match:
                    continue
                note_id = match.group(1)
                if any(r["note_id"] == note_id for r in results):
                    continue

                author_id = ""
                author_href = card.get("author_href", "")
                if author_href:
                    author_match = re.search(r'/user/profile/([a-f0-9]+)', author_href)
                    if author_match:
                        author_id = author_match.group(1)

                results.append({
                    "note_id": note_id,
                    "note_url": f"{BASE_URL}/explore/{note_id}",
                    "title": card.get("title", ""),
                    "author": card.get("author", ""),
                    "author_id": author_id,
                    "likes": parse_count(card.get("likes")),
                    "cover": card.get("cover", ""),
                    "scrape_time": datetime.now().isoformat(),
                })

                if len(results) >= max_results:
                    break

            scroll_count += 1
            log(f"已获取 {len(results)}/{max_results} 条结果")

        log(f"搜索完成，共 {len(results)} 条")
        return results[:max_results]

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> list:
        """采集用户主页的笔记列表"""
        url = USER_URL.format(user_id)
        log(f"访问用户主页: {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 提取用户信息
        user_info = await self.page.eval_on_selector_all(
            '.user-info, .info, [class*="user-info"]',
            '''els => els.map(el => el.textContent?.trim() || "")'''
        )

        # 滚动加载笔记
        results = []
        scroll_count = 0
        max_scrolls = (max_posts // 10) + 3

        while len(results) < max_posts and scroll_count < max_scrolls:
            await self.human_scroll(times=2)
            await asyncio.sleep(1)

            cards = await self.page.eval_on_selector_all(
                'section.note-item, div.note-item, a.note-item, [class*="note-item"]',
                '''els => els.map(el => {
                    const getText = (sel) => el.querySelector(sel)?.textContent?.trim() || "";
                    const link = el.tagName === 'A' ? el : el.querySelector('a[href*="/explore/"], a[href*="/search_result/"]');
                    return {
                        title: getText('.title, .footer .title, .note-title'),
                        likes: getText('.like-wrapper .count, .like .count, [class*="like"] .count'),
                        note_href: link?.href || el.href || "",
                        cover: el.querySelector('img')?.src || "",
                    };
                })'''
            )

            for card in cards:
                href = card.get("note_href", "")
                match = re.search(r'/(?:explore|search_result)/([a-f0-9]{24})', href)
                if not match:
                    continue
                note_id = match.group(1)
                if any(r["note_id"] == note_id for r in results):
                    continue

                results.append({
                    "note_id": note_id,
                    "note_url": f"{BASE_URL}/explore/{note_id}",
                    "title": card.get("title", ""),
                    "author_id": user_id,
                    "likes": parse_count(card.get("likes")),
                    "cover": card.get("cover", ""),
                    "scrape_time": datetime.now().isoformat(),
                })

                if len(results) >= max_posts:
                    break

            scroll_count += 1
            log(f"已获取 {len(results)}/{max_posts} 条笔记")

        log(f"用户主页采集完成，共 {len(results)} 条")
        return results[:max_posts]

    async def get_note_detail(self, note_id: str) -> dict:
        """采集单条笔记的详细信息"""
        url = NOTE_URL.format(note_id)
        log(f"采集笔记详情: {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 等待内容加载
        try:
            await self.page.wait_for_selector(
                '#detail-title, .note-content, [class*="note-content"], .title',
                timeout=10000
            )
        except Exception:
            log("等待笔记内容超时，尝试提取已有内容...")

        # 提取笔记详情
        detail = await self.page.evaluate('''() => {
            const getText = (sel) => {
                const el = document.querySelector(sel);
                return el?.textContent?.trim() || "";
            };
            const getAllText = (sel) => {
                return Array.from(document.querySelectorAll(sel)).map(el => el.textContent?.trim() || "");
            };

            // 标题
            const title = getText('#detail-title, .note-content .title, [class*="note-title"], .title');

            // 正文描述
            const desc = getText('#detail-desc, .note-content .desc, [class*="desc"], .content, .note-text');

            // 作者
            const author = getText('.author-wrapper .name, .author .name, [class*="author"] .name, .username');

            // 作者主页链接
            const authorLink = document.querySelector('.author-wrapper a, .author a, [class*="author"] a');
            const authorHref = authorLink?.href || "";

            // 互动数据
            const likes = getText('.like-wrapper .count, [class*="like"] .count, .like .count');
            const comments = getText('.chat-wrapper .count, [class*="chat"] .count, .comment .count');
            const collects = getText('.collect-wrapper .count, [class*="collect"] .count, .collect .count');
            const shares = getText('.share-wrapper .count, [class*="share"] .count, .share .count');

            // 图片
            const images = Array.from(document.querySelectorAll(
                '.swiper-slide img, .media-container img, [class*="swiper"] img, .note-image img, img[class*="note"]'
            )).map(img => img.src).filter(src => src && !src.includes('avatar'));

            // 视频
            const video = document.querySelector('video');
            const videoUrl = video?.src || "";

            // 标签
            const tagEls = document.querySelectorAll(
                '.note-content .tag, [class*="tag"] a, .desc a[href*="topic"], #detail-desc a'
            );
            const tags = Array.from(tagEls).map(el => {
                let t = el.textContent?.trim() || "";
                return t.replace(/^#/, "").trim();
            }).filter(Boolean);

            // 发布时间
            const timeEl = document.querySelector('.date, .bottom-container .date, [class*="date"], time');
            const publishTime = timeEl?.textContent?.trim() || "";

            return {
                title, desc, author, authorHref,
                likes, comments, collects, shares,
                images, videoUrl, tags, publishTime
            };
        }''')

        # 解析作者ID
        author_id = ""
        author_href = detail.get("authorHref", "")
        if author_href:
            author_match = re.search(r'/user/profile/([a-f0-9]+)', author_href)
            if author_match:
                author_id = author_match.group(1)

        # 提取笔记内容中的话题标签（如果上面的提取没拿到）
        tags = detail.get("tags", [])
        if not tags and detail.get("desc"):
            tags = re.findall(r'#([^#\s]+)#?', detail["desc"])

        result = {
            "note_id": note_id,
            "note_url": url,
            "title": detail.get("title", ""),
            "desc": detail.get("desc", ""),
            "author": detail.get("author", ""),
            "author_id": author_id,
            "images": detail.get("images", []),
            "video_url": detail.get("videoUrl", ""),
            "likes": parse_count(detail.get("likes")),
            "comments": parse_count(detail.get("comments")),
            "collects": parse_count(detail.get("collects")),
            "shares": parse_count(detail.get("shares")),
            "tags": tags,
            "publish_time": detail.get("publishTime", ""),
            "scrape_time": datetime.now().isoformat(),
        }

        log(f"笔记详情采集完成: {result['title'][:30]}")
        return result

    async def batch_detail(self, note_ids: list) -> list:
        """批量采集笔记详情"""
        results = []
        for i, note_id in enumerate(note_ids):
            log(f"进度: {i+1}/{len(note_ids)}")
            try:
                detail = await self.get_note_detail(note_id)
                results.append(detail)
            except Exception as e:
                log(f"笔记 {note_id} 采集失败: {e}")
                results.append({
                    "note_id": note_id,
                    "note_url": NOTE_URL.format(note_id),
                    "error": str(e),
                    "scrape_time": datetime.now().isoformat(),
                })
            # 采集间隔
            if i < len(note_ids) - 1:
                random_delay(2.0, 4.0)
        return results

# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

async def cmd_init(args):
    """首次登录"""
    async with XhsScraper(headless=False) as scraper:
        await scraper.start()
        await scraper.wait_for_login()
    print(json.dumps({"status": "ok", "message": "登录成功，会话已保存"}, ensure_ascii=False))

async def cmd_check(args):
    """检查会话状态"""
    if not STORAGE_FILE.exists():
        print(json.dumps({"status": "no_session", "message": "未找到会话文件，请先执行 init"}, ensure_ascii=False))
        return
    async with XhsScraper(headless=True) as scraper:
        await scraper.start()
        ok = await scraper.check_login()
    if ok:
        print(json.dumps({"status": "ok", "message": "会话有效"}, ensure_ascii=False))
    else:
        print(json.dumps({"status": "expired", "message": "会话已过期，请重新执行 init"}, ensure_ascii=False))

async def cmd_search(args):
    """关键词搜索"""
    async with XhsScraper(headless=True) as scraper:
        await scraper.start()
        if not await scraper.check_login():
            print(json.dumps({"status": "expired", "message": "会话已过期，请重新执行 init"}, ensure_ascii=False))
            return
        results = await scraper.search(args.keyword, args.max)

    # 是否采集详情
    if args.detail and results:
        note_ids = [r["note_id"] for r in results]
        async with XhsScraper(headless=True) as scraper:
            await scraper.start()
            details = await scraper.batch_detail(note_ids)
        results = details

    paths = save_data(results, "search", args.keyword)
    output = {
        "status": "ok",
        "count": len(results),
        "keyword": args.keyword,
        "files": {
            "json": str(paths[0]),
            "csv": str(paths[1]),
            "md": str(paths[2]),
        },
        "data": results,
    }
    print(json.dumps(output, ensure_ascii=False))

async def cmd_user(args):
    """用户主页采集"""
    async with XhsScraper(headless=True) as scraper:
        await scraper.start()
        if not await scraper.check_login():
            print(json.dumps({"status": "expired", "message": "会话已过期，请重新执行 init"}, ensure_ascii=False))
            return
        results = await scraper.get_user_posts(args.user_id, args.max)

    if args.detail and results:
        note_ids = [r["note_id"] for r in results]
        async with XhsScraper(headless=True) as scraper:
            await scraper.start()
            details = await scraper.batch_detail(note_ids)
        results = details

    paths = save_data(results, "user", args.user_id)
    output = {
        "status": "ok",
        "count": len(results),
        "user_id": args.user_id,
        "files": {
            "json": str(paths[0]),
            "csv": str(paths[1]),
            "md": str(paths[2]),
        },
        "data": results,
    }
    print(json.dumps(output, ensure_ascii=False))

async def cmd_detail(args):
    """单条笔记详情"""
    async with XhsScraper(headless=True) as scraper:
        await scraper.start()
        if not await scraper.check_login():
            print(json.dumps({"status": "expired", "message": "会话已过期，请重新执行 init"}, ensure_ascii=False))
            return
        result = await scraper.get_note_detail(args.note_id)

    paths = save_data([result], "detail", args.note_id)
    output = {
        "status": "ok",
        "files": {
            "json": str(paths[0]),
            "csv": str(paths[1]),
            "md": str(paths[2]),
        },
        "data": result,
    }
    print(json.dumps(output, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(
        description="小红书数据采集工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python xhs_scraper.py init
  python xhs_scraper.py search --keyword "咖啡店运营" --max 20
  python xhs_scraper.py search --keyword "咖啡店运营" --max 10 --detail
  python xhs_scraper.py user --user-id "5ff3e6410000000001008400" --max 20
  python xhs_scraper.py detail --note-id "6682a7b3000000001e00c8b1"
        """
    )

    sub = parser.add_subparsers(dest="command", help="采集模式")

    # init
    sub.add_parser("init", help="首次登录，手动扫码保存会话")

    # check
    sub.add_parser("check", help="检查会话是否有效")

    # search
    p_search = sub.add_parser("search", help="关键词搜索笔记")
    p_search.add_argument("--keyword", "-k", required=True, help="搜索关键词")
    p_search.add_argument("--max", "-m", type=int, default=20, help="最大采集数量（默认20）")
    p_search.add_argument("--detail", "-d", action="store_true", help="同时采集每条笔记的详情")

    # user
    p_user = sub.add_parser("user", help="采集用户主页笔记")
    p_user.add_argument("--user-id", "-u", required=True, help="小红书用户ID")
    p_user.add_argument("--max", "-m", type=int, default=20, help="最大采集数量（默认20）")
    p_user.add_argument("--detail", "-d", action="store_true", help="同时采集每条笔记的详情")

    # detail
    p_detail = sub.add_parser("detail", help="采集单条笔记详情")
    p_detail.add_argument("--note-id", "-n", required=True, help="小红书笔记ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "init":
            asyncio.run(cmd_init(args))
        elif args.command == "check":
            asyncio.run(cmd_check(args))
        elif args.command == "search":
            asyncio.run(cmd_search(args))
        elif args.command == "user":
            asyncio.run(cmd_user(args))
        elif args.command == "detail":
            asyncio.run(cmd_detail(args))
    except KeyboardInterrupt:
        log("用户中断")
        sys.exit(130)
    except Exception as e:
        log(f"错误: {e}")
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
