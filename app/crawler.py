"""热点抓取 - 从多个来源获取今日热点话题"""
import re
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 从多个公开渠道抓取热点关键词
SOURCES = [
    "https://top.baidu.com/board?tab=realtime",
    "https://www.zhihu.com/hot",
    "https://weibo.com/ajax/side/hotSearch",
]


def fetch_baidu_hot():
    """爬取百度热搜"""
    try:
        r = httpx.get("https://top.baidu.com/board?tab=realtime", headers=HEADERS, timeout=10)
        r.encoding = "utf-8"
        # 百度热搜数据在页面 JSON 中
        items = re.findall(r'"word":"(.*?)"', r.text)
        return [{"keyword": w.strip(), "source": "百度", "score": 100 - i * 3} for i, w in enumerate(items[:30])]
    except:
        return []


def fetch_weibo_hot():
    """爬取微博热搜"""
    try:
        r = httpx.get("https://weibo.com/ajax/side/hotSearch", headers=HEADERS, timeout=10)
        data = r.json()
        items = []
        for i, item in enumerate(data.get("data", {}).get("realtime", [])[:30]):
            items.append({
                "keyword": item.get("word", ""),
                "source": "微博",
                "score": item.get("raw_hot", 100 - i * 3),
            })
        return items
    except:
        return []


def fetch_zhihu_hot():
    """爬取知乎热搜"""
    try:
        r = httpx.get("https://www.zhihu.com/hot", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        items = []
        for i, a in enumerate(soup.select('a[href*="question"] h2')[:30]):
            items.append({
                "keyword": a.get_text(strip=True),
                "source": "知乎",
                "score": 100 - i * 3,
            })
        return items
    except:
        return []


def fetch_all_hot():
    """聚合所有来源的热点"""
    all_items = []
    seen = set()

    for fetcher in [fetch_baidu_hot, fetch_weibo_hot, fetch_zhihu_hot]:
        for item in fetcher():
            kw = item["keyword"]
            if kw and kw not in seen and len(kw) > 4:
                seen.add(kw)
                all_items.append(item)

    # 按热度排序
    all_items.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_items[:50]


if __name__ == "__main__":
    for item in fetch_all_hot():
        print(f"[{item['source']}] {item['score']} - {item['keyword']}")
