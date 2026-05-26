"""AI 文章生成器"""
import json
import httpx
from app.config import AI_API_KEY, AI_API_URL, AI_MODEL

# 焦虑/争议风格关键词库，用于辅助 AI 生成
ANXIETY_KEYWORDS = [
    "震惊", "千万别", "注意了", "紧急通知", "马上删", "真相大白",
    "背后原因", "让人后怕", "太危险了", "赶紧扩散", "央视曝光",
    "官方紧急提醒", "出大事了", "看完赶紧告诉家人",
]

# 多领域热点分类
CATEGORIES = [
    "社会", "科技", "财经", "教育", "医疗", "民生", "国际", "房产", "职场"
]


def generate_article(topic: str, style: str = "焦虑", api_key: str = None, api_url: str = None, model: str = None) -> dict:
    """用 AI 生成一篇热点文章"""
    key = api_key or AI_API_KEY
    url = api_url or AI_API_URL
    mdl = model or AI_MODEL

    if not key or key == "sk-your-api-key-here":
        return _fallback_article(topic, style)

    style_instruction = {
        "焦虑": "用制造焦虑和紧迫感的语气，多用'千万别','注意了','震惊'等词汇，让读者产生危机感",
        "争议": "用挑动争议的口吻，表达有冲突的观点，引发读者讨论欲望",
        "中立": "用客观中立的语气，实事求是地报道，给出多方观点",
        "科普": "用通俗易懂的方式科普相关知识，让读者觉得学到了东西",
    }.get(style, "用制造焦虑的语气")

    prompt = f"""你是一个自媒体文章写手，请根据主题「{topic}」写一篇吸引眼球的文章。

要求：
- 风格：{style_instruction}
- 字数：800-1200字
- 标题要吸引人点击，带数字或感叹效果
- 分段清晰，每段不要太长
- 结尾要有互动引导（如"你怎么看？评论区告诉我"）
- 适当使用「震惊」「千万别」「注意了」「真相是」等词汇

请按以下JSON格式返回（不要加markdown标记）：
{{
    "title": "文章标题",
    "summary": "一句话摘要（50字内）",
    "content": "文章正文，用\\n\\n分段",
    "keywords": "关键词1,关键词2,关键词3"
}}
"""

    try:
        r = httpx.post(
            f"{url}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": mdl,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 3000,
            },
            timeout=120,
        )
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        # 清理可能的 markdown 标记
        content = content.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(content)
        return {
            "title": result.get("title", f"关于{topic}的最新消息"),
            "summary": result.get("summary", ""),
            "content": result.get("content", f"关于{topic}的详细内容，正在更新中……"),
            "keywords": result.get("keywords", topic),
        }
    except Exception as e:
        return _fallback_article(topic, style)


def _fallback_article(topic: str, style: str) -> dict:
    """AI API 不可用时的备用文章"""
    title = f"【紧急】{topic}：最新消息引发全网关注，很多人还不知道真相！"
    summary = f"{topic}最新进展来了，看完让人后怕……"
    paragraphs = [
        f"近日，关于「{topic}」的话题在网上引发热议，多个相关词条冲上热搜。",
        f"据了解，这一事件已经引起有关部门的高度重视，相关调查正在展开。专家表示，这件事给所有人都提了个醒，千万不要掉以轻心。",
        f"有知情人士透露，事情远比表面看到的要复杂。很多网友在了解真相后直呼：\"太震惊了！\"",
        f"目前，各方仍在持续关注此事的最新进展。我们将第一时间为大家带来后续报道。",
        f"对此你怎么看？欢迎在评论区留言讨论。也请转发给身边的亲朋好友，让更多人看到！",
    ]
    content = "\n\n".join(paragraphs)
    return {
        "title": title,
        "summary": summary,
        "content": content,
        "keywords": topic,
    }


def batch_generate(topics: list[str], style: str = "焦虑", **kwargs):
    """批量生成多篇文章"""
    results = []
    for topic in topics:
        article = generate_article(topic, style, **kwargs)
        results.append(article)
    return results


if __name__ == "__main__":
    result = generate_article("房价走势", "焦虑")
    print(result["title"])
    print("---")
    print(result["content"][:200])
