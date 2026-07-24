"""
Static Site Generator — reads published books from DB and
renders Jinja2 templates into a dist/ directory.
v2.0: Category Navigation Builder with breadcrumbs.
"""
import os, shutil, warnings
from pathlib import Path
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader
from xml.etree.ElementTree import Element, SubElement, tostring
from collections import defaultdict

from app.database import SessionLocal
from app.models import Book, Author, Category, Publisher, Tag, File, BookAsset, Asset, Article, Issue, IssueComment, IssueResult, Election, ElectionResult, User
from sqlalchemy import text

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "static_site" / "templates"
DIST_DIR = ROOT / "dist"
SITE_URL = os.getenv("SITE_URL", "https://library.example.com")
SITE_NAME = "个人图书馆资源小站"

jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
jinja_env.globals["site_url"] = SITE_URL


def slugify(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in text.lower().replace(" ", "-")).strip("-")


# ── Category Tree ───────────────────────────────────────────────────────────
class CategoryNode:
    __slots__ = ("code", "name", "parent", "children", "books")

    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.parent = None
        self.children: list[CategoryNode] = []
        self.books: list[Book] = []


class CategoryTree:
    """Read-only category tree built once from DB categories."""

    def __init__(self, categories: list[Category]):
        # Build all nodes
        self.nodes: dict[str, CategoryNode] = {}
        for cat in categories:
            self.nodes[cat.code] = CategoryNode(cat.code, cat.name)
        # Link parent/child
        for cat in categories:
            node = self.nodes[cat.code]
            if cat.parent_code and cat.parent_code in self.nodes:
                parent = self.nodes[cat.parent_code]
                node.parent = parent
                parent.children.append(node)
        self._all_codes = set(self.nodes.keys())

    def get(self, code: str) -> CategoryNode | None:
        return self.nodes.get(code)

    def get_ancestors(self, code: str) -> list[CategoryNode]:
        """Return chain from root to this node (inclusive)."""
        node = self.nodes.get(code)
        if not node:
            return []
        chain = []
        cur = node
        while cur:
            chain.append(cur)
            cur = cur.parent
        chain.reverse()
        return chain

    def all_codes(self) -> set[str]:
        return self._all_codes

    def breadcrumb(self, code: str) -> list[dict]:
        """Breadcrumb list for templates: [{name, url}, ...]."""
        chain = self.get_ancestors(code)
        return [{"name": n.name, "url": f"/category/{n.code}.html"} for n in chain]


# ── Render helpers ──────────────────────────────────────────────────────────
def render_page(tmpl: str, out: Path, **ctx):
    t = jinja_env.get_template(tmpl)
    ctx["now"] = datetime.now()
    # Compute base_path based on depth from dist/
    rel = out.relative_to(DIST_DIR)
    depth = len(rel.parts) - 1  # 0 for index.html, 1 for book/1.html
    ctx["base_path"] = ".." * depth if depth > 0 else "."
    ctx.setdefault("title", SITE_NAME)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t.render(**ctx), encoding="utf-8")


def _build_sitemap(books, cats, authors, publishers, tags):
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for b in books:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{SITE_URL}/book/{b.id}.html"
    for c in cats:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{SITE_URL}/category/{c.code}.html"
    for a in authors:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{SITE_URL}/author/{slugify(a.name)}.html"
    for p in publishers:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{SITE_URL}/publisher/{slugify(p.name)}.html"
    for t in tags:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{SITE_URL}/tag/{slugify(t.name)}.html"
    (DIST_DIR / "sitemap.xml").write_text(tostring(urlset, encoding="unicode"), encoding="utf-8")


def _build_robots():
    (DIST_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")


def _build_rss(books):
    rss = Element("rss", version="2.0")
    ch = SubElement(rss, "channel")
    SubElement(ch, "title").text = "地平线档案馆（Horizon Archive）"
    SubElement(ch, "link").text = SITE_URL
    for b in books[:20]:
        it = SubElement(ch, "item")
        SubElement(it, "title").text = b.title
        SubElement(it, "link").text = f"{SITE_URL}/book/{b.id}.html"
    (DIST_DIR / "rss.xml").write_text(tostring(rss, encoding="unicode"), encoding="utf-8")


# ── Main build ──────────────────────────────────────────────────────────────
def build_all():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        # Copy static assets
        static_dir = ROOT / "static"
        if static_dir.exists():
            shutil.copytree(static_dir, DIST_DIR / "static")

        # ── Step 1: Read all data ──────────────────────────────────────────
        print("读取 Books ...")
        published = db.query(Book).filter(Book.status == "published").all()
        print(f"  → {len(published)}")

        print("读取 Categories ...")
        categories = db.query(Category).all()
        print(f"  → {len(categories)}")
        # Make categories available to all templates (for sidebar navigation)
        jinja_env.globals["all_categories"] = categories

        authors = db.query(Author).all()
        publishers = db.query(Publisher).all()
        tags = db.query(Tag).all()

        # ── Step 2: Build CategoryTree ─────────────────────────────────────
        print("建立 Category Tree ...")
        tree = CategoryTree(categories)
        print("  → 完成")

        # ── Step 3: Build category index (book → all parent categories) ────
        print("建立分类索引 ...")
        category_books: dict[str, list[Book]] = {c.code: [] for c in categories}
        unknown_cats: set[str] = set()

        for book in published:
            code = (book.category_code or "").strip()
            if not code:
                continue
            # Walk the code prefix upward to find the nearest known category
            # B561.291 → try B561, B56, B5, B — stop at first match
            found = None
            test = code
            all_codes = tree.all_codes()
            while test:
                if test in all_codes:
                    found = test
                    break
                # Strip last segment: B561.291 → B561
                dot = test.rfind('.'); dash = test.rfind('-')
                if max(dot, dash) > 0:
                    test = test[:max(dot, dash)]
                    continue
                # No dot/dash: try stripping one trailing digit at a time
                # B561 → B56 → B5 → B
                if test[-1].isdigit():
                    test = test[:-1]
                    continue
                # TP → T
                if len(test) > 1:
                    test = test[:-1]
                    continue
                test = None
            if found:
                ancestors = tree.get_ancestors(found)
                for anc in ancestors:
                    category_books.setdefault(anc.code, []).append(book)
            else:
                unknown_cats.add(code)

        if unknown_cats:
            for c in sorted(unknown_cats):
                print(f"  WARNING: Unknown Category: {c}")
        print(f"  → 完成 ({len(category_books)} categories, {len(unknown_cats)} unknown)")

        # ── Step 4: Book detail pages ──────────────────────────────────────
        print("生成 Book 页面 ...")
        for book in published:
            book_cats = tree.get_ancestors(book.category_code) if book.category_code else []
            render_page("book.html", DIST_DIR / "book" / f"{book.id}.html",
                        book=book, book_breadcrumb=tree.breadcrumb(book.category_code or ""),
                        book_cats=book_cats,
                        title=f"{book.title} - 地平线档案馆（Horizon Archive）", base_path="..")
        print(f"  → {len(published)}")

        # ── Step 5: Category pages (ALL, even empty) ───────────────────────
        print("生成 Category 页面 ...")
        for cat in categories:
            books = category_books.get(cat.code, [])
            node = tree.get(cat.code)
            render_page("category.html", DIST_DIR / "category" / f"{cat.code}.html",
                        category=cat, books=books, breadcrumb=tree.breadcrumb(cat.code),
                        parent=node.parent if node else None,
                        children=sorted(node.children, key=lambda n: n.code) if node else [],
                        title=f"{cat.name} ({cat.code}) - 地平线档案馆（Horizon Archive）", base_path="..")
        print(f"  → {len(categories)}")

        # ── Author pages ───────────────────────────────────────────────────
        for author in authors:
            author_books = [b for b in published if b.author_id == author.id]
            if author_books:
                render_page("author.html", DIST_DIR / "author" / f"{slugify(author.name)}.html",
                            author=author, books=author_books,
                            title=f"{author.name} - 地平线档案馆（Horizon Archive）", base_path="..")
        print(f"  [OK] author pages")

        # ── Publisher pages ────────────────────────────────────────────────
        for pub in publishers:
            pub_books = [b for b in published if b.publisher_id == pub.id]
            if pub_books:
                render_page("publisher.html", DIST_DIR / "publisher" / f"{slugify(pub.name)}.html",
                            publisher=pub, books=pub_books,
                            title=f"{pub.name} - 地平线档案馆（Horizon Archive）", base_path="..")
        print(f"  [OK] publisher pages")

        # ── Tag pages ──────────────────────────────────────────────────────
        for tag in tags:
            tag_books = [b for b in published if tag in b.tags]
            if tag_books:
                render_page("tag.html", DIST_DIR / "tag" / f"{slugify(tag.name)}.html",
                            tag=tag, books=tag_books,
                            title=f"标签: {tag.name} - 地平线档案馆（Horizon Archive）", base_path="..")
        print(f"  [OK] tag pages")

        # ── Article pages ──────────────────────────────────────────────────
        articles = db.query(Article).filter(Article.status == "published").all()
        articles_dir = DIST_DIR / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)
        if articles:
            for a in articles:
                render_page("article.html", articles_dir / f"{a.slug}.html",
                           article=a, title=f"{a.title} — 个人图书馆资源小站")
        # Always generate articles index
        render_page("articles.html", articles_dir / "index.html",
                    articles=articles, title="文章 — 个人图书馆资源小站")

        # ── About page ─────────────────────────────────────────────────────
        render_page("about.html", DIST_DIR / "about.html",
                    title="关于 - 地平线档案馆（Horizon Archive）", active_page="about", base_path=".")

        # ── Index page ─────────────────────────────────────────────────────
        render_page("index.html", DIST_DIR / "index.html", books=published,
                    categories=[c for c in categories if not (c.parent_code and c.parent_code.strip())],
                    articles=articles[:10],
                    quotes=db.execute(text("SELECT q.content,q.author,q.asset_id,a.object_key FROM quotes q LEFT JOIN assets a ON a.id=q.asset_id WHERE q.status='active' ORDER BY q.sort_order")).mappings().all(),
                    issues=db.query(Issue).filter(Issue.status!="draft").order_by(Issue.created_at.desc()).limit(10).all(),
                    elections=db.query(Election).filter(Election.status!="draft").order_by(Election.created_at.desc()).limit(10).all(),
                    title="地平线档案馆（Horizon Archive）", active_page="home", base_path=".")

        # ── Sitemap / Robots ───────────────────────────────────────────────
        _build_sitemap(published, categories, authors, publishers, tags)
        _build_robots()

        print(f"\n[SSG] Done! Site built to {DIST_DIR}")

    finally:
        # ── Step 9: Issue pages ───────────────────────────────────────────
        print("生成 Issue 页面 ...")
        issues_dir = DIST_DIR / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        published = db.query(Issue).filter(Issue.status != "draft").all()
        for issue in published:
            comments = db.query(IssueComment).filter(
                IssueComment.issue_id == issue.id, IssueComment.status == "approved"
            ).order_by(IssueComment.created_at).all()
            results = db.query(IssueResult).filter(IssueResult.issue_id == issue.id).order_by(IssueResult.rank).all()
            render_page("issue.html", issues_dir / f"{issue.slug}.html",
                        issue=issue, comments=comments, results=results,
                        title=f"{issue.title} - 议题投票", base_path="..")
        print(f"  → {len(published)}")

        # Issue index page
        print("生成 Issue 索引页 ...")
        all_issues = db.query(Issue).filter(Issue.status != "draft").order_by(Issue.created_at.desc()).all()
        render_page("issues-index.html", issues_dir / "index.html",
                    issues=all_issues, title="议题投票 - 地平线档案馆（Horizon Archive）", base_path="..")
        print(f"  → {len(all_issues)} items")

        # ── Election pages ──────────────────────────────────────────────
        print("生成 Election 页面 ...")
        elections_dir = DIST_DIR / "elections"
        elections_dir.mkdir(parents=True, exist_ok=True)
        elections = db.query(Election).filter(Election.status != "draft").all()
        for el in elections:
            results = db.query(ElectionResult).filter(ElectionResult.election_id == el.id).order_by(ElectionResult.rank).all()
            render_page("election.html", elections_dir / f"{el.slug}.html",
                        election=el, results=results,
                        title=f"{el.title} - 选举投票", base_path="..")
        print(f"  → {len(elections)} items")

        # ── Team page ─────────────────────────────────────────────────
        print("生成 Team 页面 ...")
        import json
        admins = db.query(User).filter(User.role == "admin").all()
        for a in admins:
            a.public_fields_list = json.loads(a.public_fields or '["username","email","role","qq","wechat"]')
            if a.avatar_asset_id:
                av = db.query(Asset).filter(Asset.id == a.avatar_asset_id).first()
                a.avatar_url = f"/api/image/{av.id}" if av else None
            else:
                a.avatar_url = None
        render_page("team.html", DIST_DIR / "team.html",
                    admins=admins, title="管理团队 - 地平线档案馆（Horizon Archive）", base_path=".")
        print(f"  → {len(admins)} admins")

        # Election index page — always generate, show "暂无" if empty
        print("生成 Election 索引页 ...")
        all_elections = db.query(Election).filter(Election.status != "draft").order_by(Election.created_at.desc()).all()
        render_page("elections-index.html", elections_dir / "index.html",
                    elections=all_elections, title="选举 - 地平线档案馆（Horizon Archive）", base_path="..")
        print(f"  → {len(elections)} items")

        db.close()


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    build_all()
