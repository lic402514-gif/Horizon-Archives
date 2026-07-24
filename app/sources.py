"""
Multi-source book metadata auto-fill.
Priority: Google Books → Tavily Search → DeepSeek Memory
"""
import json, re, os
from pathlib import Path as _Path
import httpx


def _load_api_key(name: str) -> str:
    key = os.getenv(name)
    if key:
        return key
    kf = _Path("data/api_keys.json")
    if kf.exists():
        return json.loads(kf.read_text()).get(name.lower().replace("_api_key", ""), "")
    return ""


def _parse_year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    m = re.match(r'(\d{4})', date_str)
    return int(m.group(1)) if m else None


# ── Source 1: Google Books ─────────────────────────────────────────────────

def from_google_books(isbn: str) -> dict | None:
    api_key = _load_api_key("GOOGLE_BOOKS_API_KEY")
    params = {"q": f"isbn:{isbn}"}
    if api_key:
        params["key"] = api_key
    try:
        r = httpx.get("https://www.googleapis.com/books/v1/volumes",
                       params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("totalItems", 0) == 0:
            return None
        vi = data["items"][0]["volumeInfo"]
        return {
            "title": vi.get("title", ""),
            "author": vi.get("authors", []),
            "publisher": vi.get("publisher"),
            "pub_year": _parse_year(vi.get("publishedDate")),
            "edition": None,
            "pages": vi.get("pageCount"),
            "summary": (vi.get("description") or "")[:800],
            "category_code": "",
            "source": "Google Books",
        }
    except Exception:
        return None


# ── Source 2: Tavily Search → DeepSeek Extract ─────────────────────────────

def from_tavily_search(isbn: str) -> dict | None:
    tavily_key = _load_api_key("TAVILY_API_KEY")
    deepseek_key = _load_api_key("DEEPSEEK_API_KEY")
    if not tavily_key or not deepseek_key:
        return None

    try:
        r = httpx.post("https://api.tavily.com/search",
            json={"api_key": tavily_key, "query": f"{isbn} 书籍 出版年份 页数 简介",
                  "max_results": 5, "include_answer": True}, timeout=15)
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
    except Exception:
        return None

    if not results:
        return None

    context = "\n".join(
        [f"- {item['title']}: {item.get('content', '')[:500]}" for item in results]
    )

    prompt = f"""根据以下搜索结果，提取ISBN {isbn}的图书元数据：
{context}

返回严格JSON（只输出JSON）：
{{"title":"书名","author":["作者"],"publisher":"出版社","pub_year":年份,"edition":"版次","pages":页数,"summary":"简介","category_code":"中图法分类号"}}
找不到则 {{"error":"not found"}}。"""

    try:
        resp = httpx.post("https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {deepseek_key}",
                     "Content-Type": "application/json"},
            json={"model": "deepseek-chat",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.1, "max_tokens": 800},
            timeout=30)
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            return None
        result = json.loads(match.group(0))
        if "error" in result:
            return None
        result["source"] = "Tavily + DeepSeek"
        return result
    except Exception:
        return None


# ── Source 3: DeepSeek Memory (last resort) ────────────────────────────────

def from_deepseek_memory(isbn: str) -> dict | None:
    api_key = _load_api_key("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    prompt = f"""根据ISBN {isbn}，返回该书的元数据JSON。如果你知道这本书，请根据训练数据填写。只返回JSON：
{{"title":"书名","author":["作者"],"publisher":"出版社","pub_year":出版年份,"edition":"版次","pages":页数,"summary":"简介","category_code":"中图法分类号"}}
如果不确定，返回 {{"error":"not found"}}。不要输出任何其他内容。"""
    try:
        resp = httpx.post("https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "deepseek-chat",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.1, "max_tokens": 600},
            timeout=20)
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            return None
        result = json.loads(match.group(0))
        if "error" in result:
            return None
        result["source"] = "DeepSeek Memory"
        return result
    except Exception:
        return None


# ── Entry point ────────────────────────────────────────────────────────────

def auto_fill(isbn: str) -> dict:
    sources = [from_google_books, from_tavily_search, from_deepseek_memory]
    for fn in sources:
        result = fn(isbn)
        if result and result.get("title"):
            return result
    raise ValueError(f"Not found: {isbn}")
