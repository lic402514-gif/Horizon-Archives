"""API Key management — set/check keys without exposing them."""
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
import json, os

from app.auth import require_permission
from app.models import User

router = APIRouter(prefix="/api/settings", tags=["settings"])

KEY_FILE = Path("data/api_keys.json")

API_KEYS = {
    "deepseek": "DeepSeek",
    "tavily": "Tavily",
    "google_books": "Google Books",
}


def _read_keys():
    if KEY_FILE.exists():
        return json.loads(KEY_FILE.read_text())
    return {}


def _write_keys(data):
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(json.dumps(data))


@router.get("/keys/status")
def key_status(_u: User = Depends(require_permission("system.config"))):
    """Check which keys are configured (never return actual values)."""
    keys = _read_keys()
    env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "google_books": "GOOGLE_BOOKS_API_KEY",
    }
    return {
        name: bool(keys.get(name) or os.getenv(env_name))
        for name, env_name in env_map.items()
    }


@router.post("/keys/{name}")
def set_key(name: str, body: dict,
            _u: User = Depends(require_permission("system.config"))):
    """Set an API key. Body: {"key": "xxx"}"""
    if name not in API_KEYS:
        raise HTTPException(400, f"Unknown key: {name}")
    new_key = (body.get("key") or "").strip()
    if not new_key:
        raise HTTPException(400, "Key cannot be empty")
    keys = _read_keys()
    keys[name] = new_key
    _write_keys(keys)
    env_name = {"deepseek": "DEEPSEEK_API_KEY", "tavily": "TAVILY_API_KEY",
                "google_books": "GOOGLE_BOOKS_API_KEY"}[name]
    os.environ[env_name] = new_key
    return {"status": "saved"}


@router.delete("/keys/{name}")
def delete_key(name: str,
               _u: User = Depends(require_permission("system.config"))):
    """Remove a stored key."""
    if name not in API_KEYS:
        raise HTTPException(400, f"Unknown key: {name}")
    keys = _read_keys()
    keys.pop(name, None)
    _write_keys(keys)
    env_name = {"deepseek": "DEEPSEEK_API_KEY", "tavily": "TAVILY_API_KEY",
                "google_books": "GOOGLE_BOOKS_API_KEY"}[name]
    os.environ.pop(env_name, None)
    return {"status": "deleted"}
