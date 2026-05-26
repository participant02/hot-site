import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker

os.makedirs("data", exist_ok=True)

engine = create_engine("sqlite:///./data/hotsite.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(String(500), default="")
    keywords = Column(String(500), default="")
    category = Column(String(50), default="热点")
    status = Column(String(20), default="draft")  # draft / published
    source = Column(String(50), default="ai_generated")
    view_count = Column(Integer, default=0)
    is_ai_generated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))), onupdate=lambda: datetime.now(timezone(timedelta(hours=8))))
    published_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "keywords": self.keywords,
            "category": self.category,
            "status": self.status,
            "source": self.source,
            "view_count": self.view_count,
            "is_ai_generated": self.is_ai_generated,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "published_at": self.published_at.isoformat() if self.published_at else "",
        }


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True)
    keyword = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), default="通用")
    hot_score = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))
    last_used_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
