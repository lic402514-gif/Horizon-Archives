"""
Book Metadata Assistant — AI-powered, beginner-friendly.
Upload a file, AI extracts metadata, review & publish in one flow.
"""
import os, json, re
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pathlib import Path

from app.database import get_db, SessionLocal
from app.models import Book, Author, Publisher, Category, Tag, Asset, BookAsset, File as FileModel
from app.auth import require_permission, require_user, STORAGE_DIR
from app.models import User

router = APIRouter(prefix="/api/metadata", tags=["metadata"])

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_API_BASE = os.getenv("AI_API_BASE", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")


async def _call_ai(system_prompt: str, user_prompt: str) -> dict:
    if not AI_API_KEY:
        raise HTTPException(400, "AI 未配置，请在 .env 中设置 AI_API_KEY")
    import httpx

    body = json.dumps({
        "model": AI_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.2,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    })
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{AI_API_BASE}/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY}"},
                content=body,
            )
            resp.raise_for_status()
            return json.loads(json.loads(resp.text)["choices"][0]["message"]["content"])
    except httpx.TimeoutException:
        raise HTTPException(500, "AI API 连接超时。请在 .env 中设置可用的 API 地址")
    except Exception as e:
        raise HTTPException(500, f"AI 调用失败: {e}")


SYSTEM_PROMPT = """你是中国图书馆分类法(CLC)编目专家。你的首要任务是根据书名/文件名准确判断该书的CLC分类号。

CLC 大类参考：
A 马克思主义、列宁主义、毛泽东思想、邓小平理论
B 哲学、宗教（B0哲学理论 B1世界哲学 B2中国哲学 B3亚洲哲学 B4非洲哲学 B5欧洲哲学 B6大洋洲哲学 B7美洲哲学 B80思维科学 B81逻辑学 B82伦理学 B83美学 B84心理学 B9宗教）
C 社会科学总论（C0理论与方法 C1现状概况 C2机构团体 C3研究法 C4教育普及 C5丛书文集 C6参考工具书 C8统计学 C91社会学 C92人口学 C93管理学 C95民族学 C96人才学 C97劳动科学）
D 政治、法律（D0政治学 D1国际共产主义运动 D2中国共产党 D4工人农民青年妇女运动 D5世界政治 D6中国政治 D8外交国际关系 D9法律）
E 军事
F 经济（F0经济学 F1世界经济 F2经济计划管理 F3农业经济 F4工业经济 F49信息产业经济 F5交通运输经济 F59旅游经济 F6邮电经济 F7贸易经济 F8财政金融）
G 文化、科学、教育、体育（G0文化理论 G1文化产业 G2信息与知识传播 G3科学研究 G4教育 G8体育）
H 语言、文字（H0语言学 H1汉语 H2中国少数民族语言 H3常用外国语 H4汉藏语系 H5阿尔泰语系 H61南亚语系 H62南印语系 H63南岛语系 H64东北亚语系 H65高加索语系 H66乌拉尔语系 H67闪含语系 H7印欧语系 H81非洲语言 H83美洲语言 H84大洋洲语言 H9国际辅助语）
I 文学（I0文学理论 I1世界文学 I2中国文学 I3亚洲文学 I4非洲文学 I5欧洲文学 I6大洋洲文学 I7美洲文学）
J 艺术（J0艺术理论 J1艺术概况 J2绘画 J29书法篆刻 J3雕塑 J4摄影 J5工艺美术 J6音乐 J7舞蹈 J8戏剧曲艺 J9电影电视）
K 历史、地理（K0史学理论 K1世界史 K2中国史 K3亚洲史 K4非洲史 K5欧洲史 K6大洋洲史 K7美洲史 K81传记 K85考古学 K89风俗民俗 K9地理）
N 自然科学总论
O 数理科学和化学（O1数学 O3力学 O4物理学 O6化学 O7晶体学）
P 天文学、地球科学（P1天文学 P2测绘学 P3地球物理学 P4大气科学 P5地质学 P7海洋学 P9自然地理学）
Q 生物科学（Q1普通生物学 Q2细胞生物学 Q3遗传学 Q4生理学 Q5生物化学 Q6生物物理学 Q7分子生物学 Q81生物工程学 Q91古生物学 Q93微生物学 Q94植物学 Q95动物学 Q96昆虫学 Q98人类学）
R 医药、卫生（R1预防医学/卫生学 R2中国医学 R3基础医学 R4临床医学 R5内科学 R6外科学 R71妇产科学 R72儿科学 R73肿瘤学 R74神经病学/精神病学 R75皮肤病学/性病学 R76耳鼻咽喉科学 R77眼科学 R78口腔科学 R8特种医学 R9药学）
S 农业科学
T 工业技术（TB一般工业技术 TD矿业工程 TE石油天然气 TF冶金 TG金属学 TH机械仪表 TJ武器工业 TK能源动力 TL原子能 TM电工技术 TN电子通信 TP自动化/计算机 TQ化学工业 TS轻工业/手工业 TU建筑科学 TV水利工程）
U 交通运输
V 航空、航天
X 环境科学、安全科学
Z 综合性图书（Z1丛书 Z2百科全书类书 Z3辞典 Z4论文集全集选集杂著 Z5年鉴年刊 Z6期刊连续性出版物 Z8图书目录文摘索引）

分类规则：
- B类哲学：中国哲学→B2，德国哲学→B516，法国哲学→B565，英美哲学→B561，美学→B83，伦理学→B82，心理学→B84，宗教→B9
- I类文学：中国小说→I247（当代）/I246（现代）/I242（古代），外国小说按国家分
- K类历史：中国通史→K20，各代史→K21-K27，世界史→K1，传记→K81，地理→K9
- A类马恩列斯毛邓著作
- D类政治法律著作
- F类经济著作
- C类社会学管理学著作

请从文件名/书名分析，返回JSON：
{
  "title": "书名",
  "author": "作者",
  "publisher": "出版社",
  "isbn": "ISBN（无则为空）",
  "pub_year": 出版年份(数字),
  "category_code": "CLC分类号（核心任务，务必准确！如B561.291）",
  "category_name": "分类名称",
  "summary": "内容简介100-200字",
  "tags": ["标签1","标签2"],
  "confidence": "high/medium/low"
}

规则：中文优先、分类号要精确到细分、简介要概括学术内容"""


# ── Config ──────────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

def _read_env_vars() -> dict:
    """Read AI_* vars from .env file."""
    result = {"AI_API_KEY": "", "AI_API_BASE": "https://api.openai.com/v1", "AI_MODEL": "gpt-4o-mini"}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip()
                if k in result:
                    result[k] = v
    return result

def _save_env_key(key: str, value: str):
    """Save or update a key=value in the .env file."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.is_file() else []
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    # Update module-level variable
    if key == "AI_API_KEY":
        global AI_API_KEY
        AI_API_KEY = value
    elif key == "AI_API_BASE":
        global AI_API_BASE
        AI_API_BASE = value
    elif key == "AI_MODEL":
        global AI_MODEL
        AI_MODEL = value

@router.get("/config")
def metadata_config(_u: User = Depends(require_user)):
    return {
        "ai_configured": bool(AI_API_KEY),
        "model": AI_MODEL,
        "api_base": AI_API_BASE,
        "has_key": bool(AI_API_KEY),
    }

@router.post("/save-key")
def save_api_key(body: dict, _u: User = Depends(require_permission("book.create"))):
    """Save AI API key and optional base/model to .env."""
    for key in ["AI_API_KEY", "AI_API_BASE", "AI_MODEL"]:
        if key in body and body[key]:
            _save_env_key(key, body[key])
    return {"ok": True, "ai_configured": bool(AI_API_KEY)}


# ── CLC keyword matching (no AI needed) ─────────────────────────────────────
CLC_KEYWORDS = [
    # A — 马恩列斯毛邓
    ("马克思", "A81"), ("恩格斯", "A81"), ("列宁", "A82"), ("斯大林", "A83"),
    ("毛泽东", "A4"), ("邓小平", "A49"), ("共产党宣言", "A12"), ("资本论", "A81"),
    ("德意志意识形态", "A81"), ("自然辩证法", "A81"), ("反杜林论", "A81"),
    ("唯物主义", "B0"), ("唯心主义", "B0"),
    # B — 哲学
    ("哲学", "B0"), ("形而上学", "B0"), ("存在主义", "B086"), ("现象学", "B089"),
    ("解释学", "B089"), ("结构主义", "B089"), ("解构主义", "B089"),
    ("中国哲学", "B2"), ("儒家", "B222"), ("论语", "B222"), ("孟子", "B222"),
    ("道家", "B223"), ("老子", "B223"), ("庄子", "B223"), ("墨子", "B224"),
    ("韩非子", "B226"), ("荀子", "B222"),
    ("西方哲学", "B5"), ("古希腊", "B502"), ("柏拉图", "B502"), ("亚里士多德", "B502"),
    ("康德", "B516.31"), ("黑格尔", "B516.35"), ("尼采", "B516.47"),
    ("海德格尔", "B516.54"), ("叔本华", "B516.41"), ("胡塞尔", "B516.52"),
    ("笛卡尔", "B565.21"), ("福柯", "B565.59"), ("德里达", "B565.59"),
    ("德勒兹", "B565.59"), ("阿尔都塞", "B565.59"), ("萨特", "B565.53"),
    ("卢梭", "B565.26"), ("休谟", "B561.291"), ("洛克", "B561.24"),
    ("培根", "B561.21"), ("罗素", "B561.54"), ("维特根斯坦", "B561.59"),
    ("杜威", "B712.51"), ("詹姆士", "B712.44"),
    ("逻辑学", "B81"), ("伦理学", "B82"), ("美学", "B83"), ("心理学", "B84"),
    ("精神分析", "B84"), ("弗洛伊德", "B84"), ("荣格", "B84"), ("拉康", "B84"),
    ("宗教", "B9"), ("佛教", "B94"), ("道教", "B95"), ("基督教", "B97"),
    ("伊斯兰教", "B96"),
    # C — 社会科学
    ("社会学", "C91"), ("人口学", "C92"), ("管理学", "C93"), ("民族学", "C95"),
    ("统计学", "C8"), ("社会科学", "C"),
    # D — 政治法律
    ("政治", "D0"), ("法律", "D9"), ("宪法", "D921"), ("民法", "D923"),
    ("刑法", "D924"), ("国际法", "D99"), ("中国共产党", "D2"),
    ("国际关系", "D8"), ("外交", "D8"),
    # F — 经济
    ("经济", "F0"), ("金融", "F83"), ("财政", "F81"), ("贸易", "F7"),
    ("产业", "F26"), ("农业经济", "F3"), ("工业经济", "F4"),
    # G — 文化教育
    ("教育", "G4"), ("文化", "G0"), ("新闻", "G21"), ("图书馆", "G25"),
    ("体育", "G8"),
    # H — 语言
    ("语言学", "H0"), ("汉语", "H1"), ("英语", "H31"), ("日语", "H36"),
    # I — 文学
    ("文学", "I"), ("小说", "I24"), ("诗歌", "I22"), ("散文", "I26"),
    ("中国文学", "I2"), ("鲁迅", "I210"), ("呐喊", "I210"), ("围城", "I246"),
    ("外国文学", "I1"), ("日本文学", "I313"), ("英国文学", "I561"),
    ("法国文学", "I565"), ("德国文学", "I516"), ("俄国文学", "I512"),
    ("美国文学", "I712"),
    # J — 艺术
    ("艺术", "J0"), ("绘画", "J2"), ("书法", "J29"), ("音乐", "J6"),
    ("电影", "J9"), ("摄影", "J4"), ("设计", "J5"),
    # K — 历史地理
    ("历史", "K"), ("中国史", "K2"), ("世界史", "K1"), ("地理", "K9"),
    ("传记", "K81"), ("考古", "K85"), ("风俗", "K89"),
    # N/O/P/Q/R/S/T/U/V/X/Z — 自然科学
    ("数学", "O1"), ("物理", "O4"), ("化学", "O6"), ("生物", "Q"),
    ("医学", "R"), ("计算机", "TP3"), ("人工智能", "TP18"), ("编程", "TP31"),
    ("建筑", "TU"), ("环境", "X"), ("生态", "X17"),
]

def _match_clc(text: str) -> list[dict]:
    """Match CLC codes by keyword. Returns top matches."""
    scores = {}
    t = text.lower()
    for kw, code in CLC_KEYWORDS:
        if kw.lower() in t:
            # Longer keyword = more specific = higher score
            scores[code] = scores.get(code, 0) + len(kw) * 10
    # Sort by score descending, deduplicate
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    seen = set()
    result = []
    for code, score in ranked:
        if code not in seen:
            seen.add(code)
            result.append({"code": code, "score": score})
    return result[:5]


@router.post("/clc-match")
def clc_match(body: dict):
    """Match CLC codes by keywords from a book title — no AI needed."""
    text = body.get("query", "").strip()
    if not text:
        raise HTTPException(400, "请输入书名")
    return {"matches": _match_clc(text)}


# ── Extract from filename ───────────────────────────────────────────────────
@router.post("/extract")
def extract_metadata(body: dict, _u: User = Depends(require_permission("book.create"))):
    """AI extracts metadata from a book title/filename."""
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(400, "请输入书名")
    # Also return keyword-matched CLC as fallback
    clc_matches = _match_clc(query)
    result = {"title": query, "author": "", "publisher": "", "isbn": "",
              "pub_year": None, "category_code": "", "summary": "", "tags": [],
              "confidence": "low", "clc_matches": clc_matches}
    try:
        ai_result = await _call_ai(SYSTEM_PROMPT, f"分析这本书：{query}")
        result.update(ai_result)
        result["confidence"] = ai_result.get("confidence", "medium")
    except HTTPException:
        # AI not available, use keyword match for CLC
        if clc_matches:
            result["category_code"] = clc_matches[0]["code"]
    return result


def _extract_pdf_text(file_bytes: bytes) -> tuple[str, bool]:
    """Extract text from PDF bytes. Returns (text, is_scanned)."""
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts = []
        total_chars = 0
        for page_num in range(min(len(doc), 8)):  # first 8 pages
            page = doc[page_num]
            text = page.get_text("text")
            text_parts.append(text)
            total_chars += len(text.strip())
        doc.close()
        full_text = "\n".join(text_parts).strip()
        is_scanned = total_chars < 50  # less than 50 chars = scanned image PDF
        return full_text, is_scanned
    except Exception:
        return "", True


# ── Extract + Upload in one call ────────────────────────────────────────────
@router.post("/extract-upload")
async def extract_and_upload(
    file: UploadFile = File(...),
    hint: str = Form(""),
    _u: User = Depends(require_permission("book.create")),
):
    """Upload a file, extract text from PDF, AI extracts metadata."""
    fn = file.filename or "unknown"
    content = await file.read()
    ext = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''

    # Clean filename for AI
    clean_name = re.sub(r'\(z-lib[^)]*\)|\(z-library[^)]*\)|\.pdf$|\.epub$|\.mobi$|\.djvu$|\.azw3$|\.txt$',
                        '', fn, flags=re.IGNORECASE)
    clean_name = re.sub(r'[_\-\s]+', ' ', clean_name).strip()
    if not clean_name or len(clean_name) < 2:
        clean_name = fn.rsplit('.', 1)[0]

    # Try to extract text from PDF
    pdf_text = ""
    is_scanned = False
    if ext == 'pdf':
        pdf_text, is_scanned = _extract_pdf_text(content)

    # Build AI prompt with all available info
    query = f"文件名: {clean_name}"
    if pdf_text:
        # Limit text to avoid token overflow
        text_preview = pdf_text[:3000]
        query += f"\n\nPDF 内文前几页提取:\n{text_preview}"
        if len(pdf_text) > 3000:
            query += "\n...(内容已截断)"
    elif is_scanned:
        query += "\n\n注意：这是扫描版PDF，无法提取文字。请仅根据文件名判断。"
    else:
        # For EPUB/TXT etc, try to read raw text
        try:
            raw = content.decode('utf-8', errors='ignore')[:2000]
            if raw and len(raw.strip()) > 50:
                query += f"\n\n文件内文片段:\n{raw}"
        except Exception:
            pass

    if hint:
        query += f"\n补充说明: {hint}"

    clc_matches = _match_clc(clean_name)
    metadata = {"title": clean_name, "author": "", "publisher": "", "isbn": "",
                "pub_year": None, "category_code": "", "summary": "", "tags": [],
                "confidence": "low", "clc_matches": clc_matches}

    # Try AI first
    try:
        ai_result = await _call_ai(SYSTEM_PROMPT, query)
        metadata.update(ai_result)
    except HTTPException:
        # AI unavailable — use keyword match for CLC as best guess
        if clc_matches:
            metadata["category_code"] = clc_matches[0]["code"]
            metadata["notes"] = "基于关键词匹配，建议核实"

    # Save file to temp location (truncate long names for Windows path limit)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_fn = fn if len(fn) < 120 else fn[:80] + "..." + fn[-40:]
    ext = safe_fn.rsplit('.', 1)[-1].lower() if '.' in safe_fn else ''
    asset_path = Path(STORAGE_DIR) / "uploads" / f"{_u.id}" / f"{ts}_{safe_fn}"
    try:
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(500, f"文件保存失败: {str(e)}")

    return {
        **metadata,
        "_file": {
            "filename": safe_fn,
            "size": len(content),
            "ext": ext,
            "mime": file.content_type or "application/octet-stream",
            "tmp_path": str(asset_path),
        }
    }


# ── Duplicate check ─────────────────────────────────────────────────────────
@router.post("/check-duplicate")
def check_duplicate(body: dict, db: Session = Depends(get_db)):
    """Check if a book with same title or ISBN already exists."""
    title = body.get("title", "").strip()
    isbn = body.get("isbn", "").strip()
    matches = []
    if title:
        q = db.query(Book).filter(Book.title == title)
        if isbn:
            q = q.filter(Book.isbn == isbn)
        matches = q.all()
    elif isbn:
        matches = db.query(Book).filter(Book.isbn == isbn).all()
    # Also check fuzzy title match
    fuzzy = []
    if title and not matches:
        fuzzy = db.query(Book).filter(Book.title.contains(title[:10])).limit(5).all()
    return {
        "is_duplicate": len(matches) > 0,
        "matches": [{"id": b.id, "title": b.title, "isbn": b.isbn,
                      "author": b.author.name if b.author else None} for b in matches],
        "similar": [{"id": b.id, "title": b.title, "isbn": b.isbn} for b in fuzzy],
    }


# ── Create book + finalize file ─────────────────────────────────────────────
@router.post("/create-with-file")
async def create_book_with_file(
    title: str = Form(...),
    author: str = Form(""),
    publisher: str = Form(""),
    isbn: str = Form(""),
    pub_year: str = Form(""),
    category_code: str = Form(""),
    summary: str = Form(""),
    tags: str = Form(""),
    tmp_path: str = Form(""),
    filename: str = Form(""),
    file_size: str = Form(""),
    file_ext: str = Form(""),
    file_mime: str = Form(""),
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    """Create a book record and register the uploaded file in one step."""
    if not title.strip():
        raise HTTPException(400, "书名不能为空")

    # Author
    author_obj = None
    if author.strip():
        author_obj = db.query(Author).filter(Author.name == author.strip()).first()
        if not author_obj:
            author_obj = Author(name=author.strip())
            db.add(author_obj); db.flush()

    # Publisher
    pub_obj = None
    if publisher.strip():
        pub_obj = db.query(Publisher).filter(Publisher.name == publisher.strip()).first()
        if not pub_obj:
            pub_obj = Publisher(name=publisher.strip())
            db.add(pub_obj); db.flush()

    py = None
    try: py = int(pub_year)
    except: pass

    book = Book(
        title=title.strip(),
        author_id=author_obj.id if author_obj else None,
        publisher_id=pub_obj.id if pub_obj else None,
        isbn=isbn.strip() or None,
        pub_year=py,
        category_code=category_code.strip() or None,
        summary=summary.strip() or None,
        status="published",
    )
    db.add(book); db.flush()

    # Tags
    for t in [t.strip() for t in tags.split(",") if t.strip()]:
        tag = db.query(Tag).filter(Tag.name == t).first()
        if not tag:
            tag = Tag(name=t)
            db.add(tag); db.flush()
        from app.models import book_tags
        db.execute(book_tags.insert().values(book_id=book.id, tag_id=tag.id))

    # Upload file to OSS and register asset
    asset = None
    if tmp_path and filename:
        tp = Path(tmp_path)
        # Restrict to uploads temp directory only
        uploads_dir = (Path.cwd() / "data" / "uploads").resolve()
        tp_resolved = tp.resolve()
        if ".." in str(tp) or not str(tp_resolved).startswith(str(uploads_dir)):
            raise HTTPException(400, "Invalid file path")
        if tp.exists():
            ext = file_ext or filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            size = int(file_size) if file_size else tp.stat().st_size
            oss_key = f"books/{book.id}/{filename}"

            # Upload to OSS first, fall back to local
            provider = "local"
            try:
                import oss2
                from app.auth import OSS_ENDPOINT, OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME
                auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
                bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
                bucket.put_object_from_file(oss_key, str(tp))
                provider = "oss"
                try: tp.unlink()
                except: pass
            except Exception:
                # OSS failed — save locally
                dest = Path(STORAGE_DIR) / oss_key
                dest.parent.mkdir(parents=True, exist_ok=True)
                tp.rename(dest)

            asset = Asset(
                filename=filename, extension=ext, mime_type=file_mime,
                size=size, object_key=oss_key, asset_type="ebook",
                provider=provider, upload_by=_u.id, status="active",
            )
            db.add(asset); db.flush()

            # BookAsset link
            ba = BookAsset(book_id=book.id, asset_id=asset.id, relation_type="ebook")
            db.add(ba)

            # File record for downloads
            f = FileModel(book_id=book.id, format=ext.upper(),
                          oss_key=oss_key, size=size)
            db.add(f)

    db.commit()
    db.refresh(book)

    return {
        "id": book.id,
        "title": book.title,
        "author": author.strip() or None,
        "has_file": asset is not None,
        "url": f"/book/{book.id}.html",
        "message": "图书创建成功！",
    }


# ── Category search ─────────────────────────────────────────────────────────
@router.get("/categories/search")
def search_categories(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    cats = db.query(Category).filter(
        Category.name.contains(q) | Category.code.contains(q.upper())
    ).limit(15).all()
    return [{"code": c.code, "name": c.name} for c in cats]
