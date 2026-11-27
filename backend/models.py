"""models.py — SQLAlchemy ORM models"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True)
    email         = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String)
    plan          = Column(String, default="free")
    reviews_count = Column(Integer, default=0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

class Review(Base):
    __tablename__ = "reviews"
    id            = Column(String, primary_key=True)
    user_id       = Column(String, nullable=False)
    language      = Column(String, nullable=False)
    code          = Column(Text, nullable=False)
    status        = Column(String, default="pending")   # pending|running|completed|failed
    score         = Column(Integer, nullable=True)
    summary       = Column(Text, nullable=True)
    findings_json = Column(Text, default="[]")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    completed_at  = Column(DateTime(timezone=True), nullable=True)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id         = Column(String, primary_key=True)
    user_id    = Column(String, nullable=False)
    name       = Column(String, nullable=False)
    key_hash   = Column(String, unique=True, nullable=False)
    prefix     = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
