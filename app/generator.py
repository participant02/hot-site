"""AI 文章生成器"""
import json
import httpx
from app.config import AI_API_KEY, AI_API_URL, AI_MODEL


def generate_article(topic: str, style: str = "焦虑", api_key: str = None, api_url: str = None, model: str = None) -> dict:
    key = api_key or AI_API_KEY
    url = api_url or AI_API_URL
    mdl = model or AI_MODEL

    if not key:
        return _fallback_article(topic, style)

    system_prompts = {
        "焦虑": "你是一个资深自媒体写手。你的文章风格让读者看完坐不住，焦虑感拉满。但你从不使用套路化的网络用语，而是通过真实案例、数据对比和犀利观点来制造冲击力。",
        "争议": "你是一个观点犀利的评论员。你的文章敢说真话，能挑动读者的情绪。你擅长从反常识的角度切入，让支持者和反对者都想说两句。",
        "中立": "你是一个客观中立的记者。你的文章事实充分，逻辑清晰，让读者觉得可信、有收获。",
        "科普": "你是一个很会讲知识的博主。你能把复杂的事情用大白话讲明白，读者看完觉得\"原来如此\"。",
    }

    style_instructions = {
        "焦虑": "【制造焦虑】用数据说话，用案例扎心。让读者意识到自己可能正在错过、被坑、落后。不要用\"震惊\"\"千万别\"\"注意了\"这种一眼假的营销号词汇，太低级。",
        "争议": "【挑动争议】选一个有争议的角度切入，敢下判断，敢站队。让不同立场的人看了都想留言反驳或支持。",
        "中立": "【客观中立】呈现多方事实和数据，让读者自己判断。不要煽情，不要站队。",
        "科普": "【科普讲解】从一个大家关心的问题出发，层层递进讲清楚背后的原理。用比喻和例子帮助理解。",
    }

    prompt = f"""写一篇关于「{topic}」的文章。

{system_prompts.get(style, system_prompts["焦虑"])}

{style_instructions.get(style, style_instructions["焦虑"])}

【写作规则 - 必须遵守】
1. 标题不超过25字，要有信息量，不要用感叹号堆砌
2. 开头直接用故事、数据或问题切入，不要铺垫
3. 每段不超过5句话，段落之间要有逻辑递进
4. 不要出现这些词：震惊、千万别、注意了、紧急通知、出大事了、赶紧扩散、央视曝光、看完赶紧告诉家人
5. 不要出现"你怎么看？评论区告诉我"这类套路结尾
6. 字数600-900字，信息密度要高
7. 语气像一个活人在说话，不要像AI念稿
8. 可以提供具体的数据（可以编但要有合理性）

用以下JSON格式返回（不要加markdown标记）：
{{
    "title": "文章标题",
    "summary": "一句话摘要（40字以内）",
    "content": "文章正文，用\\n\\n分段",
    "keywords": "3-5个逗号分隔的关键词"
}}
"""

    try:
        r = httpx.post(
            f"{url}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": mdl,
                "messages": [
                    {"role": "system", "content": "你是一个有10年经验的自媒体主编，文字简洁有力，从不写废话。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.85,
                "max_tokens": 3000,
            },
            timeout=120,
        )
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        content = content.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(content)
        return {
            "title": result.get("title", f"关于{topic}，说几点我的看法"),
            "summary": result.get("summary", ""),
            "content": result.get("content", f"关于{topic}的详细内容，正在更新中……"),
            "keywords": result.get("keywords", topic),
        }
    except Exception as e:
        return _fallback_article(topic, style)


def _fallback_article(topic: str, style: str) -> dict:
    title = f"关于{topic}，我说几句"
    summary = f"{topic}这个话题最近讨论很多，我来聊聊自己的看法。"
    paragraphs = [
        f"最近「{topic}」这个话题讨论度很高。网上各种说法都有，我梳理了一下几个关键信息，分享给大家。",
        f"首先，这件事的核心是什么？简单来说，就是一些新的变化正在发生，而很多人可能还没意识到这意味着什么。",
        f"从目前的情况来看，有几个信号值得关注。这些变化可能会直接影响到普通人的生活。",
        f"我觉得，面对这种情况，与其焦虑不如提前了解清楚，做好准备。信息越透明，心里越有底。",
    ]
    content = "\n\n".join(paragraphs)
    return {
        "title": title,
        "summary": summary,
        "content": content,
        "keywords": topic,
    }


def batch_generate(topics: list[str], style: str = "焦虑", **kwargs):
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
