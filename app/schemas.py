"""
Pydantic request/response schemas for the FastAPI application.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Auth ────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ── Users ───────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    role: str = "user"
    status: str = "ACTIVE"
    created_at: datetime | None = None
    roles: list = []
    avatar_url: str | None = None
    avatar_asset_id: int | None = None
    qq: str | None = None
    phone: str | None = None
    wechat: str | None = None
    invite_code_used: str | None = None
    has_easter_egg: bool = False
    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_user(cls, user):
        """Convert ORM User to UserOut."""
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            roles=[{"id": r.id, "name": r.name, "perm_count": len(r.permissions)} for r in (user.roles or [])],
            avatar_url=user.avatar.url if user.avatar else None,
            avatar_asset_id=user.avatar_asset_id,
            qq=user.qq,
            phone=user.phone,
            wechat=user.wechat,
            invite_code_used=user.invite_code_used,
            has_easter_egg=user.has_easter_egg,
        )


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    role: str = "user"
    status: str = "ACTIVE"


class UserUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    email: Optional[EmailStr] = None


# ── Authors ─────────────────────────────────────────────────────────────────
class AuthorOut(BaseModel):
    id: int
    name: str
    bio: Optional[str] = None
    model_config = {"from_attributes": True}


class AuthorCreate(BaseModel):
    name: str
    bio: Optional[str] = None


# ── Publishers ──────────────────────────────────────────────────────────────
class PublisherOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    model_config = {"from_attributes": True}


class PublisherCreate(BaseModel):
    name: str
    address: Optional[str] = None


# ── Categories ──────────────────────────────────────────────────────────────
class CategoryOut(BaseModel):
    code: str
    name: str
    parent_code: Optional[str] = None
    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    code: str
    name: str
    parent_code: Optional[str] = None


# ── Tags ────────────────────────────────────────────────────────────────────
class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str


# ── Files ───────────────────────────────────────────────────────────────────
class FileOut(BaseModel):
    id: int
    book_id: int
    format: str
    oss_key: str
    size: Optional[int] = None
    sha256: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Books ───────────────────────────────────────────────────────────────────
class BookOut(BaseModel):
    id: int
    title: str
    author: Optional[AuthorOut] = None
    publisher: Optional[PublisherOut] = None
    isbn: Optional[str] = None
    edition: Optional[str] = None
    pub_year: Optional[int] = None
    category: Optional[CategoryOut] = None
    summary: Optional[str] = None
    cover_url: Optional[str] = None
    status: str
    tags: list[TagOut] = []
    files: list[FileOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class BookCreate(BaseModel):
    title: str
    author_id: Optional[int] = None
    publisher_id: Optional[int] = None
    isbn: Optional[str] = None
    edition: Optional[str] = None
    pub_year: Optional[int] = None
    category_code: Optional[str] = None
    summary: Optional[str] = None
    tag_ids: list[int] = []


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author_id: Optional[int] = None
    publisher_id: Optional[int] = None
    isbn: Optional[str] = None
    edition: Optional[str] = None
    pub_year: Optional[int] = None
    category_code: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    tag_ids: Optional[list[int]] = None


# ── OSS upload ──────────────────────────────────────────────────────────────
class UploadRequest(BaseModel):
    book_id: int
    format: str           # pdf, epub, mobi...
    filename: str         # original filename


class UploadResponse(BaseModel):
    upload_url: str       # pre-signed PUT URL
    oss_key: str          # OSS object key
    expires_in: int = 60


class FileRecordRequest(BaseModel):
    """Sent by frontend after upload completes to record the file in DB."""
    book_id: int
    format: str
    oss_key: str
    size: Optional[int] = None
    sha256: Optional[str] = None


# ── Book Comments ──────────────────────────────────────────────────────────

class BookCommentOut(BaseModel):
    id: int
    book_id: int
    user_id: int
    username: str = ""
    avatar_url: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class BookCommentCreate(BaseModel):
    content: str


# ── Article Comments ───────────────────────────────────────────────────────

class ArticleCommentOut(BaseModel):
    id: int
    article_id: int
    user_id: int
    username: str = ""
    avatar_url: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class ArticleCommentCreate(BaseModel):
    content: str


# ── Bookshelves ────────────────────────────────────────────────────────────

class BookshelfOut(BaseModel):
    id: int
    user_id: int
    name: str
    is_public: bool
    created_at: Optional[datetime] = None
    book_count: int = 0
    model_config = {"from_attributes": True}


class BookshelfCreate(BaseModel):
    name: str
    is_public: bool = True


class BookshelfUpdate(BaseModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None


class BookshelfItemAdd(BaseModel):
    book_id: int


class BookshelfDetailOut(BaseModel):
    id: int
    user_id: int
    name: str
    is_public: bool
    created_at: Optional[datetime] = None
    items: list[BookOut] = []
    model_config = {"from_attributes": True}


# ── Reading History ────────────────────────────────────────────────────────

class ReadingHistoryOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    action_type: str
    created_at: Optional[datetime] = None
    book: Optional[BookOut] = None
    model_config = {"from_attributes": True}


# ── Notifications ──────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    content: Optional[str] = None
    is_read: bool
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Book View ──────────────────────────────────────────────────────────────

class BookViewOut(BaseModel):
    id: int
    book_id: int
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Popular / New Arrivals ─────────────────────────────────────────────────

class PopularBookOut(BaseModel):
    book_id: int
    title: str
    author_name: str = ""
    category_code: Optional[str] = None
    cover_url: Optional[str] = None
    count: int


class NewArrivalOut(BaseModel):
    id: int
    title: str
    author_name: str = ""
    category_code: Optional[str] = None
    cover_url: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Integration ────────────────────────────────────────────────────────────

class PushBookRequest(BaseModel):
    title: str
    subtitle: Optional[str] = None
    authors: list[str] = []
    translators: list[str] = []
    publisher: Optional[str] = None
    pub_year: Optional[str] = None
    edition: Optional[str] = None
    isbn: Optional[str] = None
    clc: Optional[str] = None
    summary: Optional[str] = None
    language: Optional[str] = None
    pages: Optional[int] = None
    doc_type: Optional[str] = None
    series: Optional[str] = None
    cover_base64: Optional[str] = None
    file_base64: Optional[str] = None
    file_format: Optional[str] = "pdf"


class IsbnCheckResponse(BaseModel):
    exists: bool
    book: Optional[BookOut] = None
