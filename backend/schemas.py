"""schemas.py — Pydantic request/response schemas"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime

class UserCreate(BaseModel):
    email: str
    password: str

class LoginIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    plan: str
    model_config = {"from_attributes": True}

class TokenOut(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class ReviewCreate(BaseModel):
    code: str
    language: str = "python"

class ReviewOut(BaseModel):
    id: str
    status: str
    language: str
    score: Optional[int] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class ReviewDetailOut(ReviewOut):
    findings: List[Any] = []

class ApiKeyCreate(BaseModel):
    name: str
