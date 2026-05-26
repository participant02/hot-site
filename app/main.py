"""热点网站 - FastAPI 主应用"""
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import init_db, get_db, Article, Keyword
from app.crawler import fetch_all_hot
from app.generator import generate_article
from app.config import SITE_NAME, SITE_URL, SITE_DESC, BAIDU_AD_SCRIPT, GOOGLE_AD_SCRIPT

app = FastAPI()

# 静态文件
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 模板
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# 中文时区
CST = timezone(timedelta(hours=8))


@app.on_event("startup")
def startup():
    init_db()


# ==================== 公共路由 ====================

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    articles = db.query(Article).filter(Article.status == "published").order_by(Article.published_at.desc()).limit(20).all()
    hot_keywords = db.query(Keyword).filter(Keyword.is_active == True).order_by(Keyword.hot_score.desc()).limit(10).all()
    return templates.TemplateResponse(request, "index.html", {
        "articles": articles,
        "hot_keywords": hot_keywords,
        "site_name": SITE_NAME,
        "site_desc": SITE_DESC,
        "baidu_ad": BAIDU_AD_SCRIPT,
        "google_ad": GOOGLE_AD_SCRIPT,
    })


@app.get("/article/{article_id}", response_class=HTMLResponse)
def article_detail(article_id: int, request: Request, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        return HTMLResponse("文章不存在", status_code=404)

    # 增加阅读量
    article.view_count += 1
    db.commit()

    # 推荐文章
    related = db.query(Article).filter(
        Article.status == "published", Article.id != article.id
    ).order_by(func.random()).limit(6).all()

    return templates.TemplateResponse(request, "article.html", {
        "article": article,
        "related": related,
        "site_name": SITE_NAME,
        "baidu_ad": BAIDU_AD_SCRIPT,
        "google_ad": GOOGLE_AD_SCRIPT,
    })


@app.get("/category/{cat}")
def category_page(cat: str, request: Request, db: Session = Depends(get_db)):
    articles = db.query(Article).filter(
        Article.status == "published", Article.category == cat
    ).order_by(Article.published_at.desc()).all()
    return templates.TemplateResponse(request, "index.html", {
        "articles": articles,
        "site_name": SITE_NAME,
        "current_cat": cat,
    })


@app.get("/sitemap.xml", response_class=HTMLResponse)
def sitemap(request: Request, db: Session = Depends(get_db)):
    articles = db.query(Article).filter(Article.status == "published").order_by(Article.published_at.desc()).all()
    return templates.TemplateResponse(request, "sitemap.xml", {
        "articles": articles,
        "site_url": SITE_URL,
    })


# ==================== 管理后台 ====================

@app.get("/admin", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {})


@app.post("/admin")
def admin_login(request: Request, password: str = Form(...), db: Session = Depends(get_db)):
    if password != "admin888":
        return templates.TemplateResponse(request, "admin/login.html", {
            "error": "密码错误"
        })
    resp = RedirectResponse(url="/admin/dashboard", status_code=302)
    resp.set_cookie("admin_token", "logged_in", max_age=86400 * 7)
    return resp


def check_admin(request: Request):
    token = request.cookies.get("admin_token")
    if token != "logged_in":
        return False
    return True


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    total = db.query(func.count(Article.id)).scalar()
    published = db.query(func.count(Article.id)).filter(Article.status == "published").count()
    draft = db.query(func.count(Article.id)).filter(Article.status == "draft").count()
    total_views = db.query(func.sum(Article.view_count)).scalar() or 0
    ai_count = db.query(func.count(Article.id)).filter(Article.is_ai_generated == True).scalar()
    keywords_count = db.query(func.count(Keyword.id)).scalar()

    recent = db.query(Article).order_by(Article.created_at.desc()).limit(10).all()
    hot_kws = db.query(Keyword).order_by(Keyword.hot_score.desc()).limit(10).all()

    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "total": total, "published": published, "draft": draft,
        "total_views": total_views, "ai_count": ai_count,
        "keywords_count": keywords_count,
        "recent": recent, "hot_kws": hot_kws,
        "site_name": SITE_NAME,
    })


@app.get("/admin/articles", response_class=HTMLResponse)
def admin_articles(request: Request, page: int = 1, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    per_page = 20
    total = db.query(func.count(Article.id)).scalar()
    articles = db.query(Article).order_by(Article.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse(request, "admin/articles.html", {
        "articles": articles,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })


@app.get("/admin/generate", response_class=HTMLResponse)
def admin_generate_page(request: Request, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    hot_topics = fetch_all_hot()
    keywords = db.query(Keyword).filter(Keyword.is_active == True).order_by(Keyword.hot_score.desc()).all()
    return templates.TemplateResponse(request, "admin/generate.html", {
        "hot_topics": hot_topics,
        "keywords": keywords,
    })


@app.post("/admin/generate")
def admin_generate(
    request: Request,
    topic: str = Form(...),
    style: str = Form("焦虑"),
    auto_publish: bool = Form(False),
    db: Session = Depends(get_db),
):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    existing = db.query(Article).filter(Article.title.contains(topic[:10])).first()
    if existing:
        return templates.TemplateResponse(request, "admin/generate.html", {
            "message": f"⚠️ 相似主题已存在: 《{existing.title}》",
            "hot_topics": fetch_all_hot(),
            "keywords": db.query(Keyword).filter(Keyword.is_active == True).all(),
        })

    result = generate_article(topic, style)

    article = Article(
        title=result["title"],
        content=result["content"],
        summary=result["summary"],
        keywords=result["keywords"],
        category="热点",
        status="published" if auto_publish else "draft",
        source="ai_generated",
        is_ai_generated=True,
        published_at=datetime.now(CST) if auto_publish else None,
    )
    db.add(article)
    db.commit()

    for kw in result["keywords"].split(","):
        kw = kw.strip()
        if kw:
            existing_kw = db.query(Keyword).filter(Keyword.keyword == kw).first()
            if existing_kw:
                existing_kw.hot_score += 1
                existing_kw.last_used_at = datetime.now(CST)
            else:
                db.add(Keyword(keyword=kw, hot_score=1, last_used_at=datetime.now(CST)))
    db.commit()

    return templates.TemplateResponse(request, "admin/generate.html", {
        "message": f"✅ 文章生成成功！《{article.title}》[{'已发布' if auto_publish else '草稿'}]",
        "hot_topics": fetch_all_hot(),
        "keywords": db.query(Keyword).filter(Keyword.is_active == True).all(),
    })


@app.post("/admin/batch-generate")
def admin_batch_generate(
    request: Request,
    topics: str = Form(...),
    style: str = Form("焦虑"),
    auto_publish: bool = Form(False),
    db: Session = Depends(get_db),
):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    topic_list = [t.strip() for t in topics.split("\n") if t.strip()]
    success = 0

    for topic in topic_list:
        result = generate_article(topic, style)
        article = Article(
            title=result["title"],
            content=result["content"],
            summary=result["summary"],
            keywords=result["keywords"],
            category="热点",
            status="published" if auto_publish else "draft",
            is_ai_generated=True,
            published_at=datetime.now(CST) if auto_publish else None,
        )
        db.add(article)
        db.commit()

        for kw in result["keywords"].split(","):
            kw = kw.strip()
            if kw:
                existing_kw = db.query(Keyword).filter(Keyword.keyword == kw).first()
                if existing_kw:
                    existing_kw.hot_score += 1
                else:
                    db.add(Keyword(keyword=kw, hot_score=1))
        db.commit()
        success += 1

    return templates.TemplateResponse(request, "admin/generate.html", {
        "message": f"✅ 批量生成完成！成功 {success}/{len(topic_list)} 篇",
        "hot_topics": fetch_all_hot(),
        "keywords": db.query(Keyword).filter(Keyword.is_active == True).all(),
    })


@app.get("/admin/keywords", response_class=HTMLResponse)
def admin_keywords(request: Request, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    keywords = db.query(Keyword).order_by(Keyword.hot_score.desc()).all()
    hot_topics = fetch_all_hot()
    return templates.TemplateResponse(request, "admin/keywords.html", {
        "keywords": keywords,
        "hot_topics": hot_topics,
    })


@app.post("/admin/keywords/add")
def admin_add_keyword(request: Request, keyword: str = Form(...), category: str = Form("通用"), db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    existing = db.query(Keyword).filter(Keyword.keyword == keyword).first()
    if existing:
        existing.is_active = True
        existing.hot_score += 10
    else:
        db.add(Keyword(keyword=keyword, category=category, hot_score=10, is_active=True))
    db.commit()
    return RedirectResponse(url="/admin/keywords", status_code=302)


@app.post("/admin/keywords/delete/{kid}")
def admin_delete_keyword(kid: int, request: Request, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")
    kw = db.query(Keyword).filter(Keyword.id == kid).first()
    if kw:
        kw.is_active = False
        db.commit()
    return RedirectResponse(url="/admin/keywords", status_code=302)


@app.get("/admin/keywords/refresh")
def admin_refresh_keywords(request: Request, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")

    hot_items = fetch_all_hot()
    for item in hot_items[:20]:
        existing = db.query(Keyword).filter(Keyword.keyword == item["keyword"]).first()
        if not existing:
            db.add(Keyword(
                keyword=item["keyword"],
                category="热点",
                hot_score=item.get("score", 50),
                is_active=True,
            ))
        else:
            existing.hot_score = max(existing.hot_score, item.get("score", 50))
    db.commit()
    return RedirectResponse(url="/admin/keywords", status_code=302)


@app.post("/admin/article/{aid}/publish")
def admin_publish_article(aid: int, request: Request, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")
    article = db.query(Article).filter(Article.id == aid).first()
    if article:
        article.status = "published"
        article.published_at = datetime.now(CST)
        db.commit()
    return RedirectResponse(url="/admin/articles", status_code=302)


@app.post("/admin/article/{aid}/delete")
def admin_delete_article(aid: int, request: Request, db: Session = Depends(get_db)):
    if not check_admin(request):
        return RedirectResponse(url="/admin")
    article = db.query(Article).filter(Article.id == aid).first()
    if article:
        db.delete(article)
        db.commit()
    return RedirectResponse(url="/admin/articles", status_code=302)


@app.post("/admin/article/{aid}/edit")
def admin_edit_article(
    aid: int, request: Request,
    title: str = Form(...), content: str = Form(...),
    summary: str = Form(""), keywords: str = Form(""),
    category: str = Form("热点"),
    db: Session = Depends(get_db),
):
    if not check_admin(request):
        return RedirectResponse(url="/admin")
    article = db.query(Article).filter(Article.id == aid).first()
    if article:
        article.title = title
        article.content = content
        article.summary = summary
        article.keywords = keywords
        article.category = category
        article.updated_at = datetime.now(CST)
        db.commit()
    return RedirectResponse(url="/admin/articles", status_code=302)


# ==================== 启动 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
