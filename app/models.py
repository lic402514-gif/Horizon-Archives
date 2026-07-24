"""
SQLAlchemy models for Personal Library.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean, UniqueConstraint, Float
from sqlalchemy.orm import relationship, Session
from app.database import Base

# ── Association tables ───────────────────────────────────────────────────────

book_tags = Table(
    "book_tags", Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


# ── Authors ──────────────────────────────────────────────────────────────────

class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    bio = Column(Text, nullable=True)
    books = relationship("Book", back_populates="author")


# ── Publishers ───────────────────────────────────────────────────────────────

class Publisher(Base):
    __tablename__ = "publishers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    address = Column(String(100), nullable=True)
    books = relationship("Book", back_populates="publisher")


# ── Tags ─────────────────────────────────────────────────────────────────────

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    books = relationship("Book", secondary=book_tags, back_populates="tags")


# ── Categories (CLC) ─────────────────────────────────────────────────────────

class Category(Base):
    __tablename__ = "categories"
    code = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    parent_code = Column(String(10), ForeignKey("categories.code"), nullable=True)
    parent = relationship("Category", remote_side=[code], backref="children")


# ── Books ────────────────────────────────────────────────────────────────────

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=True)
    publisher_id = Column(Integer, ForeignKey("publishers.id"), nullable=True)
    isbn = Column(String(20), nullable=True)
    edition = Column(String(20), nullable=True)
    pub_year = Column(Integer, nullable=True)
    category_code = Column(String(10), ForeignKey("categories.code"), nullable=True)
    summary = Column(Text, nullable=True)
    cover_url = Column(String(500), nullable=True)
    status = Column(String(20), default="published")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    author = relationship("Author", back_populates="books")
    publisher = relationship("Publisher", back_populates="books")
    category = relationship("Category")
    tags = relationship("Tag", secondary=book_tags, back_populates="books")
    files = relationship("File", back_populates="book")
    book_assets_rel = relationship("BookAsset", back_populates="book")


# ── Files (legacy) ───────────────────────────────────────────────────────────

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(10), nullable=False)
    oss_key = Column(String(256), nullable=False)
    size = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    book = relationship("Book", back_populates="files")


# ── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(30), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(100), nullable=True)
    role = Column(String(10), default="user")
    status = Column(String(10), default="ACTIVE")
    qq = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    wechat = Column(String(50), nullable=True)
    invite_code_used = Column(String(20), nullable=True)
    avatar_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    token_version = Column(Integer, default=1)
    public_fields = Column(Text, nullable=True)  # JSON array of public field names
    invite_code_used = Column(String(20), nullable=True)
    has_easter_egg = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    roles = relationship("Role", secondary=user_roles, backref="users")
    avatar = relationship("Asset", foreign_keys=[avatar_asset_id])

    def has_permission(self, code: str) -> bool:
        for role in self.roles:
            for perm in role.permissions:
                if perm.code == code: return True
        return False

    def get_permissions(self) -> set[str]:
        return {perm.code for role in self.roles for perm in role.permissions}


# ── Download Logs ────────────────────────────────────────────────────────────

class DownloadLog(Base):
    __tablename__ = "download_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── RBAC ─────────────────────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=True)
    permissions = relationship("Permission", secondary=role_permissions, backref="roles")


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)


class OperationLog(Base):
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(50), nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    result = Column(String(20), default="success")
    is_public = Column(Boolean, default=True)  # whether visible in public activity log
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Asset Management ─────────────────────────────────────────────────────────

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    extension = Column(String(20), nullable=True)
    mime_type = Column(String(100), nullable=True)
    size = Column(Integer, nullable=True)
    md5 = Column(String(32), nullable=True)
    sha256 = Column(String(64), nullable=True)
    provider = Column(String(20), default="local")
    bucket = Column(String(100), nullable=True)
    object_key = Column(String(500), nullable=False)
    asset_type = Column(String(30), default="other")
    remark = Column(Text, nullable=True)
    upload_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    upload_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    update_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default="active")
    url = Column(String(500), nullable=True)


class BookAsset(Base):
    __tablename__ = "book_assets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(20), nullable=False)
    book = relationship("Book", back_populates="book_assets_rel")
    asset = relationship("Asset", backref="book_refs")


# ── Article CMS ──────────────────────────────────────────────────────────────

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(200), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    author_name = Column(String(100), nullable=True)
    status = Column(String(20), default="draft")  # draft | review | published | archived
    summary = Column(Text, nullable=True)
    cover_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    content_md = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)          # e.g. "哲学/现象学"
    tags = Column(String(300), nullable=True)              # comma-separated: "马克思,黑格尔"
    seo_title = Column(String(200), nullable=True)
    seo_description = Column(String(500), nullable=True)
    seo_keywords = Column(String(300), nullable=True)
    canonical_url = Column(String(500), nullable=True)
    reading_time = Column(Integer, nullable=True)          # minutes
    word_count = Column(Integer, nullable=True)
    version = Column(Integer, default=1)                   # current version number
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    cover = relationship("Asset", foreign_keys=[cover_asset_id])


class ArticleVersion(Base):
    __tablename__ = "article_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    content_md = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    summary_changes = Column(String(200), nullable=True)   # "修改了第三段" etc.
    editor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ArticleAsset(Base):
    __tablename__ = "article_assets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(30), nullable=False)
    article = relationship("Article", backref="article_assets_rel")
    asset = relationship("Asset", backref="article_refs")


# ── Invite Codes ────────────────────────────────────────────────────────────

class InviteCode(Base):
    __tablename__ = "invite_codes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="unused")
    note = Column(String(100), nullable=True)
    max_uses = Column(Integer, default=1)
    use_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Page Views (deduplicated) ─────────────────────────────────────────────────

class PageView(Base):
    __tablename__ = "page_views"
    id = Column(Integer, primary_key=True, autoincrement=True)
    page_path = Column(String(500), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    session_key = Column(String(64), nullable=True)
    view_count = Column(Integer, default=1)
    first_viewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_viewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


# ── Issue Governance ────────────────────────────────────────────────────

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    content = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="draft")  # draft/discussion/voting/counting/finished/archived
    vote_type = Column(String(30), default="simple_majority")  # simple_majority/absolute_majority/approval
    discussion_start = Column(DateTime, nullable=True)
    discussion_end = Column(DateTime, nullable=True)
    vote_start = Column(DateTime, nullable=True)
    vote_end = Column(DateTime, nullable=True)
    result_publish_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[creator_id])
    options = relationship("IssueOption", back_populates="issue", cascade="all, delete-orphan")
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="issue", cascade="all, delete-orphan")


class IssueOption(Base):
    __tablename__ = "issue_options"
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    sort = Column(Integer, default=0)
    vote_count = Column(Integer, default=0)

    issue = relationship("Issue", back_populates="options")


class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("issue_options.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    issue = relationship("Issue", back_populates="votes")
    option = relationship("IssueOption")
    user = relationship("User")

    __table_args__ = (UniqueConstraint("issue_id", "user_id", "option_id", name="uq_vote_user_option"),)


class IssueComment(Base):
    __tablename__ = "issue_comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("issue_comments.id"), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(20), default="approved")  # pending/approved/rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    issue = relationship("Issue", back_populates="comments")
    user = relationship("User")
    parent = relationship("IssueComment", remote_side=[id], backref="replies")


class IssueResult(Base):
    __tablename__ = "issue_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("issue_options.id"), nullable=True)
    vote_count = Column(Integer, default=0)
    percentage = Column(Float, nullable=True)
    rank = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    issue = relationship("Issue")
    option = relationship("IssueOption")


# ── Election System ────────────────────────────────────────────────────

class Election(Base):
    __tablename__ = "elections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    position = Column(String(255), nullable=True)
    seats = Column(Integer, default=1)
    status = Column(String(20), default="draft")
    vote_type = Column(String(30), default="simple_majority")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nomination_start = Column(DateTime, nullable=True)
    nomination_end = Column(DateTime, nullable=True)
    voting_start = Column(DateTime, nullable=True)
    voting_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[creator_id])
    candidates = relationship("ElectionCandidate", back_populates="election", cascade="all, delete-orphan")
    votes = relationship("ElectionVote", back_populates="election", cascade="all, delete-orphan")
    results = relationship("ElectionResult", back_populates="election", cascade="all, delete-orphan")


class ElectionCandidate(Base):
    __tablename__ = "election_candidates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    biography = Column(Text, nullable=True)
    manifesto = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending/approved/rejected
    vote_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    election = relationship("Election", back_populates="candidates")
    user = relationship("User")


class ElectionVote(Base):
    __tablename__ = "election_votes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("election_candidates.id"), nullable=False)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rank = Column(Integer, default=1)  # for STV future use
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    election = relationship("Election", back_populates="votes")
    candidate = relationship("ElectionCandidate")
    voter = relationship("User")

    __table_args__ = (UniqueConstraint("election_id", "voter_id", "candidate_id", name="uq_election_vote"),)


class ElectionResult(Base):
    __tablename__ = "election_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("election_candidates.id"), nullable=True)
    vote_count = Column(Integer, default=0)
    percentage = Column(Float, nullable=True)
    rank = Column(Integer, default=0)
    elected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    election = relationship("Election", back_populates="results")
    candidate = relationship("ElectionCandidate")


# ── Book Comments ──────────────────────────────────────────────────────────

class BookComment(Base):
    __tablename__ = "book_comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    book = relationship("Book", backref="comments")
    user = relationship("User", backref="book_comments")


# ── Article Comments ───────────────────────────────────────────────────────

class ArticleComment(Base):
    __tablename__ = "article_comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    article = relationship("Article", backref="comments")
    user = relationship("User", backref="article_comments")


# ── Bookshelves ────────────────────────────────────────────────────────────

class Bookshelf(Base):
    __tablename__ = "bookshelves"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="bookshelves")
    items = relationship("BookshelfItem", back_populates="bookshelf", cascade="all, delete-orphan")


class BookshelfItem(Base):
    __tablename__ = "bookshelf_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bookshelf_id = Column(Integer, ForeignKey("bookshelves.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    bookshelf = relationship("Bookshelf", back_populates="items")
    book = relationship("Book")


# ── Reading History ────────────────────────────────────────────────────────

class ReadingHistory(Base):
    __tablename__ = "reading_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(20), nullable=False)  # "view" or "download"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="reading_history")
    book = relationship("Book")


# ── Notifications ──────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="notifications")


# ── Book Views (per-book visit tracking) ───────────────────────────────────

class BookView(Base):
    __tablename__ = "book_views"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    book = relationship("Book")


# ── Book Merge Log ─────────────────────────────────────────────────────────

class BookMergeLog(Base):
    __tablename__ = "book_merge_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_book_id = Column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    target_book_id = Column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    merged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    merged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Messages ──────────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")


# ── Quotes ──────────────────────────────────────────────────────────────────

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    author = Column(String(200), nullable=True)
    asset_id = Column(Integer, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String(20), default="active")
